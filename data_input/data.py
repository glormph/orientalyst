import logging, datetime, time
import connections, constants
from urllib2 import HTTPError
from data_input.inputmodels import PersonRun, ClubMember
from data_input.xmlparser import EventorXMLParser

logger = logging.getLogger('data_input')


# how to do relays? --> teamresult instead of personresult
# how many competitorstatus are there? OK, didnotstart, ...
# currently person-based. Every person results are parsed. Should make it so
# that we only download once per event

# error handling of not found elements


class EventorData(object):
    def __init__(self):
        self.events = {}
        self.eventraces = {}
        self.classraces = {}
        self.personruns = []
        self.connection = connections.EventorConnection()
        self.parser = EventorXMLParser()
        self.update_time_days = 7 # how long a period should be requested
                                  # results from eventor from.

    def get_competitors(self, personid=None):
        """Public method to make data object fetch competitors"""
        logger.info('Downloading member data from eventor')
        memberxml = \
            self.connection.download_all_members(constants.ORGANISATION_ID)
        logger.info('Got {0} members'.format(len(memberxml)))
        clubmembers = self.filter_competitor(memberxml, personid)
        # FIXME handle clubmembers==False error
        self.competitors = self.add_competition_data(clubmembers)
    
    def get_newmember_races(self, members):
        """Interface method to process all races from new members except from
        the last x days"""
        now = datetime.datetime.now()
        todate = now - datetime.timedelta(self.update_time_days+1)
        for member in members:
            logger.info('Getting race data from eventor for new member ID '
            '{0}'.format(member.eventorID))
            try:
                xml = self.connection.download_events(member.eventorID, todate=todate)
            except HTTPError, e:
                if e.code == 500:
                    logger.warning('HTTPError 500 occurred downloading events')
                    continue
                else:
                    raise
            else:
                self.process_member_result_xml(xml, member)
        return self.classraces
    
    def get_recent_races(self, members):
        """Calling method interface to process recent races for club members"""
        now = datetime.datetime.now()
        fromdate = now - datetime.timedelta(self.update_time_days)
        for member in members:
            logger.info('Getting race data from eventor for member ID '
            '{0}'.format(member.eventorID))
            xml = self.connection.download_events(member.eventorID,
                                                    fromdate=fromdate)
            self.process_member_result_xml(xml, member)
    
    def filter_races(self, keepraces):
        """Repopulates self.classraces, self.events, self.eventraces,
        by filtering on the races to keep."""
        logger.info('Filtering races to keep {0} races'.format(len(keepraces)))
        self.classraces, self.events, self.eventraces = {}, {}, {}
        for cr in keepraces:
            eventrace = cr.fkeys['eventrace']
            event = eventrace.fkeys['event']
            if eventrace.eventorID not in self.classraces:
                self.classraces[eventrace.eventorID] = {}
            self.classraces[eventrace.eventorID][cr.classname] = cr
            self.events[event.eventorID] = event
            self.eventraces[eventrace.eventorID] = eventrace

    def get_results_of_races(self):
        """Gets results for races, downloading from eventor for each 
        event/personcombination, then processing."""
        results_to_download = self.get_person_event_combinations()
        logger.info('Getting results for processed events')
        for cr in results_to_download:
            eventid = cr.fkeys['eventrace'].fkeys['event'].eventorID
            personid = results_to_download[cr].eventorID
            if eventid != '3009':
                continue
            logger.debug('Downloading results for person {0}, '
                'event {1}'.format(personid, eventid))
            try:
                resultxml = self.connection.download_results(personid, eventid)
            except HTTPError, e:
                if e.code == 500:
                    logger.warning('HTTPError 500 occurred downloading resultdata')
                    continue
                else:
                    raise
            else:
                # results are added to existing races in by parser
                results_toparse = self.check_races_with_club_starts(self.events[eventid])
                self.parser.set_races_as_classvars(self.events, self.eventraces, self.classraces)
                self.parser.xml_parse(resultxml, to_parse_eventresults=results_toparse)

    def finalize(self):
        """Format some data for easy access by db module"""
        # UNNECCESSARY?
        tmplist = []
        for erid in self.classraces:
            for cr in self.classraces[erid].values():
                tmplist.append(cr)
        self.classraces = tmplist
        
        for cr in self.classraces:
            for pid in cr.results:
                cr.results[pid]['splits'] = [{'split_n': x,
                                             'time': cr.results[pid]['splits'][x]}\
                                            for x in cr.results[pid]['splits']]
    
    def wipe_data(self):
        """Deletes all data in self.classraces, self.eventraces, etc"""
        self.__init__()
    
    def filter_competitor(self, memberxml, eventorid):
        # filters mmebers on an eventorid
        if eventorid is None:
            return [ClubMember(x) for x in memberxml]
        else:
            for member in memberxml:
                cm = ClubMember(member)
                if cm.eventorID == eventorid:
                    logger.info('Only processing member with eventorid '
                    '{0}'.format(eventorid))
                    return [cm]
            # loop falls through, error:
            return False

    def add_competition_data(self, clubmembers):
        competitors = []
        for clubmember in clubmembers:
            try:
                logger.info('Getting competition details for clubmember with'
                'ID {0}, {1}, {2}.'.format(clubmember.eventorID,
                clubmember.firstname,
                clubmember.lastname))
                compxml = self.connection.download_competition_data(clubmember.eventorID)
            except HTTPError, e:
                if e.code == 404: # no data in eventor on certain competitor
                    logger.warning('No competition data for competitor ID '
                    '{0}'.format(clubmember.eventorID))
                    continue
            else:
                clubmember.parse_competitiondetails(compxml) 
                competitors.append(clubmember)
            time.sleep(1)
        return competitors
   
    def process_member_result_xml(self, xml, clubmember):
        logger.info('Processing member race xml for member ID {0}, containing '
         '{1} events.'.format(clubmember.eventorID, len(xml)))
        racedata = {'events': [], 'eventraces': [], 'classraces': []}
        # parse xml and create data models
        self.parser.set_races_as_classvars(self.events, self.eventraces, self.classraces)
        for resultlist in xml:
            parsed = self.parser.xml_parse(resultlist, clubmember)
            racedata['events'].extend(parsed['events'])
            racedata['eventraces'].extend(parsed['eventraces'])
            racedata['classraces'].extend(parsed['classraces'])
        # make personruns
        logger.debug('Creating {0} PersonRun '
        'objects'.format(len(racedata['classraces'])))
        for cr in racedata['classraces']:
            self.personruns.append(PersonRun(clubmember, cr))
        # fill self.classraces, self.eventraces, self.events
        self.fill_model_lists(racedata['events'], self.events)
        self.fill_model_lists(racedata['eventraces'], self.eventraces)
        for cr in racedata['classraces']:
            if cr.fkeys['eventrace'].eventorID not in self.classraces:
                self.classraces[cr.fkeys['eventrace'].eventorID] = {}
            self.classraces[cr.fkeys['eventrace'].eventorID][cr.classname] = cr
        logger.info('Parsed all member result for member with ID '
        '{0}'.format(clubmember.eventorID))

    def fill_model_lists(self, models, classvar):
        for x in models:
            classvar[x.eventorID] = x

    def check_races_with_club_starts(self, event):
        """Returns races of a certain event in which at least one clubmember
        started. Evaluated by checking which classraces already exist. Returns
        a dict with eventraceid lists as values, classnames as keys."""
        races_with_club_start = {}
        for erid in self.classraces:
            er =  self.eventraces[erid]
            if er.fkeys['event'] != event:
                continue
            for cn in self.classraces[erid]:
                if cn not in races_with_club_start:
                    races_with_club_start[cn] = []
                races_with_club_start[cn].append(erid)
        return races_with_club_start

    def get_person_event_combinations(self):
        personruns_to_download = {}
        for pr in self.personruns:
            try:
                p = personruns_to_download[pr.fkeys['classrace']]
            except KeyError:
                personruns_to_download[pr.fkeys['classrace']] = \
                                                    pr.fkeys['person']
        return personruns_to_download

