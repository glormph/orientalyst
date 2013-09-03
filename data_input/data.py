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
    
    def create_clubmembers(self, memberobjs):
        competitors = []
        for member in memberobjs:
            cm = ClubMember(eventor_id=member.eventor_id)
            cm.attach_django_object(member)
            competitors.append(cm)
        return competitors

    def get_newmember_races(self, members):
        """Interface method to process all races from new members except from
        the last x days"""
        now = datetime.datetime.now()
        for member in members:
            logger.info('Getting races participated in by new member ID '
                                            '{0}'.format(member.eventorID))
            try:
                xml = self.connection.download_events(member.eventorID,
                                                        todate=now)
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
        logger.info('Getting results for {0} processed events'.format( \
                            len(results_to_download)))
        for cr in results_to_download:
            eventid = cr.fkeys['eventrace'].fkeys['event'].eventorID
            personid = results_to_download[cr].eventorID
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
                # FIXME club start checking may be unneccessary, since we
                # download results of one member and have checked which races
                # he/she has ran
                results_toparse = self.check_races_with_club_starts(self.events[eventid])
                already_parsed = self.populate_with_parsed_models([], [], None)
                for resultlist in resultxml:
                    self.parser.xml_parse(resultlist, already_parsed,
                               to_parse_eventresults=results_toparse)

    def get_classraces_as_list(self):
        """Format some data for easy access by db module"""
        classraces = []
        for erid in self.classraces:
            classraces.extend(self.classraces[erid].values())
        return classraces

    def reformat_split_results(self, classraces):
        for cr in classraces:
            for pid in cr.results:
                cr.results[pid]['splits'] = [{'split_n': x,
                                             'time': cr.results[pid]['splits'][x]}\
                                            for x in cr.results[pid]['splits']]
        return classraces

    def filter_competitor(self, memberxml, eventorid):
        # filters mmebers on an eventorid
        if eventorid is None:
            clubmembers = [ClubMember() for x in memberxml]
            for cm,xml in zip(clubmembers, memberxml):
                cm.parse_personXML(xml)
            logger.info('Creating {0} clubmember '
                                    'objects'.format(len(clubmembers)))
            return clubmembers
        else:
            for member in memberxml:
                cm = ClubMember()
                cm.parse_personXML(member)
                if cm.eventorID == eventorid:
                    logger.info('Only processing member with eventorid '
                    '{0}'.format(eventorid))
                    return [cm]
            # loop falls through, error:
            return False

    def add_competition_data(self, clubmembers):
        competitors = []
        for clubmember in clubmembers[:10]:
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
        amount_ev, amount_evr, amount_cr, amount_pr  = \
                            self.get_amounts_processed_races()
        racedata = {'events': [], 'eventraces': [], 'classraces': []}
        
        # parse xml and create data models
        already_parsed = self.populate_with_parsed_models([], [], None)
        for resultlist in xml:
            parsed = self.parser.xml_parse(resultlist, already_parsed, clubmember)
            already_parsed = self.populate_with_parsed_models({
                    'events':parsed['events'], 
                    'eventraces': parsed['eventraces']},
                    parsed['classraces'], clubmember)

        amount_ev_after, amount_evr_after, amount_cr_after, amount_pr_after  = \
                            self.get_amounts_processed_races()
        logger.info('Created {0} new events, {1} eventraces, {2} classraces '
        'and {3} personruns'.format(
            amount_ev_after - amount_ev,
            amount_evr_after - amount_evr,
            amount_cr_after - amount_cr,
            amount_pr_after - amount_pr))
    
    def get_amounts_processed_races(self):
        # A bit unneccessary, but I want to be able to check the logs how many
        # things are made right now when testing
        nr_of_personruns = len(self.personruns)
        nr_of_events = len(self.events.values())
        nr_of_eventraces = len(self.eventraces.values())
        nr_of_classraces = len([y for x in self.classraces.values() for y in
                                x.values()])
        return (nr_of_events, nr_of_eventraces, nr_of_classraces,
                    nr_of_personruns)

    def populate_with_parsed_models(self, events_eventraces, classraces, clubmember):
        # populate self.events and self.eventraces which are single depth dicts
        for k in events_eventraces:
            racedict = getattr(self, k)
            for x in events_eventraces[k]:
                racedict[x.eventorID] = x
            setattr(self, k, racedict)
        
        # populate self.classraces which is a 2-depth dict. Also make
        # personruns here.
        for cr in classraces:
            if cr.fkeys['eventrace'].eventorID not in self.classraces:
                self.classraces[cr.fkeys['eventrace'].eventorID] = {}
            self.classraces[cr.fkeys['eventrace'].eventorID][cr.classname] = cr
            self.personruns.append(PersonRun(clubmember, cr))
        
        return {'events': self.events, 'eventraces': self.eventraces,
                        'classraces': self.classraces}

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
        logger.info('Filtering classraces to download results of')
        allclassraces = self.get_classraces_as_list()
        personruns_to_download = {}
        for pr in self.personruns:
            cr = pr.fkeys['classrace']
            if cr not in allclassraces:
                continue
            try:
                p = personruns_to_download[cr]
            except KeyError:
                personruns_to_download[pr.fkeys['classrace']] = \
                                                    pr.fkeys['person']
        return personruns_to_download

