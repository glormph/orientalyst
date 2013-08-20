import string, random, logging, datetime
import connections, constants
from urllib2 import HTTPError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# console handler
#fh = logging.FileHandler(os.path.join(consts.LOG_DIR, 'vainamoinen.log') )
loghandler = logging.StreamHandler()
#fh.setLevel(logging.DEBUG)
#fh_errors = logging.FileHandler(os.path.join(consts.LOG_DIR, 'errors.log') )
#fh_errors.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - PID:%(process)d - %(name)s - '
'%(levelname)s - %(message)s')
#fh.setFormatter(formatter)
#fh_errors.setFormatter(formatter)
#log.addHandler(fh)
#log.addHandler(fh_errors)
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)


# how to do relays? --> teamresult instead of personresult
# how many competitorstatus are there? OK, didnotstart, ...
# currently person-based. Every person results are parsed. Should make it so
# that we only download once per event

# error handling of not found elements
class BaseData(object):
    def attach_django_object(self, obj):
        self.db_obj = obj
    
    def get_django_object(self, obj):
        return self.db_obj

    def get_fkey(self, name):
        fkey_object = self.fkeys[name]
        return fkey_object.db_obj


class ClubMember(BaseData):
    def __init__(self, xml=None):
        self.SInrs = []
        self.lastname = '' 
        self.firstname = ''
        self.email = None
        self.eventorID = None
        self.classraces = {}
        if xml is not None:
            self.parsePersonXML(xml)

    def parsePersonXML(self, person):
        self.lastname = person.find('.//Family').text.encode('utf-8')
        self.firstname = person.find('.//Given').text.encode('utf-8')
        self.eventorID = person.find('.//PersonId').text
        try:
            self.email = person.find('.//Tele').attrib['mailAddress']
        except (KeyError, AttributeError):
            self.email = None

    def parse_competitiondetails(self, xml):
        ccards = xml.findall('.//CCard')
        for ccard in ccards:
            if ccard.find('PunchingUnitType').attrib['value'] == 'SI':
                sinr = ccard.find('CCardId').text
                if sinr not in self.SInrs:
                    self.SInrs.append(sinr)

class Event(BaseData):
    def __init__(self, eventxml, eventid):
        self.classraces = {}
        self.eventorID = eventid
        self.name = eventxml.find('Name').text
        self.startdate = eventxml.find('StartDate').find('Date').text
        self.finishdate = eventxml.find('FinishDate').find('Date').text


class EventRace(BaseData):
    def __init__(self, event, eventraceid, name, date, lightcondition=''):
        self.eventorID = eventraceid
        self.name = name # e.g. 'Etapp 1'
        self.date = date
        self.lightcondition = lightcondition
        self.fkeys = {'event': event}


class ClassRace(BaseData):
    def __init__(self, eventrace, classname, distance='', racetype=''):
        self.eventrace = eventrace
        self.classname = classname
        self.racetype = racetype
        self.distance = distance
        self.results = {}
        self.checkpoints = {}
        self.fkeys = {'eventrace': eventrace}

    def splitsFromSingleResults(self, personresult):
        person = personresult.find('Person')
        try:
            personid = person.find('PersonId').text
        except AttributeError:
            personid = ''
            for i in range(8):
                personid += random.choice(string.hexdigits)
        self.setPerson( person, personid)
        result = personresult.find('Result')
        self.addResults(result, personid)

    def splitsFromRaceResult(self, raceresult, personid, person):
        self.setPerson(person, personid)
        result = raceresult.find('Result')
        self.addResults(result, personid)
    
    def addResults(self, result, personid):
        try:
            self.results[personid]['position'] = result.find('ResultPosition').text
        except:
            self.results[personid]['position'] = None
        try: # strange, if there isn't time, there is no last split either?
            self.results[personid]['time'] = result.find('Time').text
        except:
            self.results[personid]['time'] = ''

        self.results[personid]['status'] = result.find('CompetitorStatus').attrib['value']
        self.results[personid]['splits'] = {}

        try: # not everyone includes timediff
            self.results[personid]['diff'] = result.find('TimeDiff').text 
        except AttributeError:
            self.results[personid]['diff'] = ''
            
        for split in result.findall('SplitTime'):
            self.checkpoints[split.attrib['sequence'] ] = split.find('ControlCode').text
            try: # need error catching for missing splittimes (grey text in winsplits online)
                self.results[personid]['splits'][split.attrib['sequence']] = split.find('Time').text
            except AttributeError:
                self.results[personid]['splits'][split.attrib['sequence']] = ''
        
    def setPerson(self, person, personid):
        lastname = person.find('.//Family').text
        firstname = person.find('.//Given').text
        self.results[personid] = {}
        self.results[personid]['firstname'] = firstname
        self.results[personid]['lastname'] = lastname


class PersonRun(BaseData):
    def __init__(self, clubmember, classrace):
        self.fkeys = {'classrace': classrace, 'person': clubmember}


class EventorData(object):
    def __init__(self):
        self.events = {}
        self.eventraces = {}
        self.classraces = {}
        self.personruns = []
        self.connection = connections.EventorConnection()
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
            xml = self.connection.download_events(member.eventorID, todate=todate)
            self.process_member_result_xml(xml, member)
    
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
        """Gets results for races, downloading from eventor for each event,
        then processing."""
        for event in self.events:
            resultxml = self.connection.download_results(event)
            if resultxml is None:
                continue
            # results are added to existing races in self.xml_parse and below
            # no need for further processing or even putting output in variable
            self.xml_parse(resultxml)

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
        for clubmember in clubmembers[0:10]:
            try:
                logger.info('Getting competition details for clubmember with'
                'ID {0}, {1}, {2}.'.format(clubmember.eventorID,
                clubmember.firstname.encode('utf-8'),
                clubmember.lastname.encode('utf-8')))
                compxml = self.connection.download_competition_data(clubmember.eventorID)
            except HTTPError, e:
                if e.code == 404: # no data in eventor on certain competitor
                    continue
            else:
                clubmember.parse_competitiondetails(compxml) 
                competitors.append(clubmember)
        return competitors
   
    def process_member_result_xml(self, xml, clubmember):
        logger.info('Processing member race xml for member ID {0}, containing '
         '{1} events.'.format(clubmember.eventorID, len(xml)))
        racedata = {'events': [], 'eventraces': [], 'classraces': []}
        # parse xml and create data models
        for resultlist in xml:
            parsed = self.xml_parse(resultlist, clubmember)
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

    def xml_parse(self, xml, clubmember=None):
        # map result to Event
        logger.debug('Parsing eventor XML')
        eventxml = xml.find('Event')
        eventid = eventxml.find('EventId').text
        if eventid in self.events:
            event = self.events[eventid]
        else:
            event = Event(eventxml, eventid)
        logger.debug('Created an event, id {0}'.format(eventid))
        
        if clubmember is None:
            to_parse_eventresults = self.check_races_with_club_starts(event)
        # loop through event results by class
        racedata = {'events': [event], 'eventraces': [], 'classraces':[]}
        classresults = xml.findall('ClassResult')
        logger.debug('Found {0} classresults'.format(len(classresults)))
        for classresult in classresults:
            # prepare parsing
            eventclassinfo = classresult.find('EventClass')
            classname = eventclassinfo.find('Name').text
            if clubmember is None:
                races_to_parse, personresults = self.prepare_event_results(classresult,
                                        to_parse_eventresults, classname)
                add_results = True
            else:
                races_to_parse, personresults = self.prepare_member_results(classresult,
                                        clubmember, classname)
                add_results = False
            if races_to_parse is None:
                continue

            # process results and fill racedata
            parsed = self.parse_multi_or_singleday_races(personresults, event,
                                eventclassinfo, classname, races_to_parse, add_results)
            for k in parsed:
                racedata[k].extend(parsed[k])
        logger.debug('All xml parsed')
        return racedata

    
    def prepare_member_results(self, classresult, clubmember, classname):
        logger.debug('Preparing member results')
        personresults = classresult.findall('PersonResult')
        # dont parse team result yet
        if personresults == []: 
            logger.debug('Found team result, not parsing')
            return None, None
        # check race status (finished), and if race has not already been parsed. 
        races_to_parse = self.check_competitor_status(personresults, classname,
                                        classresult, clubmember.eventorID)
        # check if there are races to parse for this class
        if classname not in races_to_parse or \
                    races_to_parse[classname] == []:
            logger.debug('No races to parse for this class.')
            return None, None
        else:
            return races_to_parse, personresults

    def prepare_event_results(self, classresult, races_to_parse, classname):
        # if there are no races to parse for this class, check next classresult.
        if classname not in races_to_parse or \
                    races_to_parse[classname] == []:
            return None, None

        personresults = classresult.findall('PersonResult')
        if personresults == []: # teamresult - what to do?
            return None, None
        else:
            return races_to_parse, personresults

    def parse_multi_or_singleday_races(self, personresults, event,
                eventclassinfo, classname, races_to_parse, add_results):
        if personresults[0].find('RaceResult') is not None:
            logger.debug('Found multiday classresults')
            return self.parse_multiday_raceresults(personresults, event,
                        classname, races_to_parse, add_results=add_results)
        else:
            logger.debug('Found singleday classresults')
            return self.parse_singleday_raceresults(personresults, event,
                        eventclassinfo, classname, add_results=add_results)
    
    def parse_singleday_raceresults(self, personresults, event, eventclassinfo,
                                    classname, add_results):
        eventraceid = eventclassinfo.find('.//EventRaceId').text
        # no need to check if eventraceid in races_to_parse, since single day
        # event only has one eventraceid
        if eventraceid in self.eventraces:
            logger.debug('Eventrace with ID {0} already exists, using '
            'it.'.format(eventraceid))
            er = self.eventraces[eventraceid]
        else:
            logger.debug('Creating new Eventrace with ID '
            '{0}'.format(eventraceid))
            er = EventRace(event,
                eventraceid, event.name, event.startdate)
        if eventraceid not in self.classraces:
            self.classraces[eventraceid] = {}
        if classname in self.classraces[eventraceid]:
            logger.debug('Classrace for eventrace {0}, class {1} already '
            'exists'.format(eventraceid, classname.encode('utf-8')))
            cr = self.classraces[eventraceid][classname]
            # add results only for event results, for which already exist
            # a cr in self.classrace by definition
            if add_results is True:
                for personresult in personresults:
                    cr.splitsFromSingleResults(personresult)
        else:
            logger.debug('Creating new classrace for eventrace {0}, class '
            '{1}'.format(eventraceid, classname.encode('utf-8')))
            cr = ClassRace(er, classname)
        
        return {'eventraces': [er], 'classraces': [cr]}

    def parse_multiday_raceresults(self, personresults, event, classname, races_to_parse,
                                    add_results):
        """Called in case of multiday event, where multiple races are run"""
        # TODO would like to have this call single_raceresults, but that would
        # possibly be less effective parsing.
        eventraces = {}
        classraces = {}
        logger.debug('Parsing multiday event, got {0} '
        'personresults'.format(len(personresults)))
        for personresult in personresults:
            person = personresult.find('Person')
            try: # not all competitors are registered in eventor
                personid = person.find('PersonId').text
            except AttributeError:
                personid = ''
            # iterate through raceresults
            raceresults = personresult.findall('RaceResult')
            logger.debug('Got {0} races for this event'.format(len(raceresults)))
            for raceresult in raceresults:
                eventrace = raceresult.find('EventRace')
                eventraceid = eventrace.find('EventRaceId').text
                # check if race should be parsed (starting clubmembers, not yet parsed for other member)
                if eventraceid not in races_to_parse[classname]:
                    logger.debug('Not parsing team results')
                    continue
                    
                # If eventrace/classrace not yet exist, make new ones 
                if eventraceid not in eventraces:
                    logger.debug('Creating new Eventrace with ID '
                    '{0}'.format(eventraceid))
                    light = eventrace.attrib['raceLightCondition']
                    name = eventrace.find('Name').text
                    date = eventrace.find('RaceDate').find('Date').text
                    er = EventRace(event, eventraceid, name, date, light)
                    eventraces[eventraceid] = er
                    classraces[eventraceid] = {}
                else:
                    logger.debug('Eventrace with ID {0} already exists, '
                    'using'.format(eventraceid))
                    er = eventraces[eventraceid]
                # same for classrace, and attach results if eventresults
                if classname not in classraces[eventraceid]:
                    logger.debug('Creating new Classrace with eventrace id '
                    '{0}, class {1}'.format(eventraceid, classname.encode('utf-8')))
                    racetype = eventrace.attrib['raceDistance']
                    cr = ClassRace(er, classname, racetype=racetype)
                    classraces[eventraceid][classname] = cr
                else:
                    logger.debug('Classrace with eventrace id {0}, class {1} already exists, '
                    'using'.format(eventraceid, classname.encode('utf-8')))
                    cr = classraces[eventraceid][classname]
                    if add_results is True:
                        cr.splitsFromRaceResult(raceresult, personid, person)
            
            return {'eventraces': eventraces.values(), 'classraces':
                            [y for x in classraces.values() for y in x.values()]}

    def check_races_with_club_starts(self, event):
        """Returns races of a certain event in which at least one clubmember
        started. Evaluated by checking which classraces already exist. Returns
        a dict with eventraceid lists as values, classnames as keys."""
        raceresults_to_parse = {}
        event_to_parse = self.events[event.eventorID]
        for cr in self.classraces:
            er = cr.fkeys['eventrace']
            if event_to_parse == er.fkeys['event']:
                if er.eventorID not in raceresults_to_parse:
                    raceresults_to_parse[cr.classname] = []
                raceresults_to_parse[cr.classname].append(er.eventorID)
        
        return raceresults_to_parse 
    
    def check_competitor_status(self, personresults, classname, classresult, competitorid,
                                    eventraceid=None):
        """Check in which classraces a clubmember started and finished ok."""
        logger.debug('Checking competitor status for person id {0} '
        ', have received {1} personresult elements'.format(competitorid, len(personresults)))
        status_ok = {}
        # this should not be necessary, but just to be safe
        for personresult in personresults:
            person = personresult.find('Person')
            try: # not all competitors are registered in eventor
                personid = person.find('PersonId').text
                logger.debug('Found person id {0} in results'.format(personid))
            except AttributeError:
                personid = None

            # Check if the requested clubmember did start, if not: next raceresult.
            if personresult.find('RaceResult') is not None:
                for raceresult in personresult.findall('RaceResult'):
                    if personid == competitorid and \
                            raceresult.find('Result').find('CompetitorStatus').attrib['value'] != \
                            'DidNotStart':
                        eventraceid = raceresult.find('EventRace').find('EventRaceId').text
                        status_ok[classname] = eventraceid
            else:
                if personid == competitorid and \
                        personresult.find('Result').find('CompetitorStatus').attrib['value'] != \
                        'DidNotStart':
                    eventraceid = classresult.find('EventClass').find('.//EventRaceId').text
                    status_ok[classname] = eventraceid
        return status_ok
