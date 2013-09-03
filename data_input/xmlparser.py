import logging
from data_input.inputmodels import Event, EventRace, ClassRace
logger = logging.getLogger('data_input')

class EventorXMLParser(object):
    def __init__(self):
        pass
    
    def xml_parse(self, xml, already_parsed, clubmember=None, to_parse_eventresults=None):
        """Parses Eventor XML, returns a dict with events, eventraces,
        classraces found in that XML"""
        self.eventraces = already_parsed['eventraces']
        self.classraces = already_parsed['classraces']

        # map result to Event
        logger.debug('Parsing eventor XML')
        eventxml = xml.find('Event')
        eventid = eventxml.find('EventId').text
        if eventid in already_parsed['events']:
            event = already_parsed['events'][eventid]
            logger.debug('Using previously created event, id {0}'.format(eventid))
        else:
            event = Event(eventxml, eventid)
            logger.debug('Created an event, id {0}'.format(eventid))
        
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
                    logger.debug('Not parsing eventrace '
                    '{0}'.format(eventraceid))
                    continue
                    
                # If eventrace/classrace not yet exist, make new ones 
                # FIXME theoretically possible for 1 member to run two races
                # with same eventraceid
                if eventraceid not in self.eventraces and eventraceid not in \
                            eventraces:
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
                    try:
                        er = self.eventraces[eventraceid]
                    except KeyError:
                        # when a member raced two classes of same eventrace
                        er = eventraces[eventraceid]
                    finally:
                        if eventraceid not in classraces:
                            classraces[eventraceid] = {}
                # same for classrace, and attach results if eventresults
                newclassrace = False
                try:
                    if classname not in self.classraces[eventraceid]:
                        newclassrace = True
                    else:
                        cr = self.classraces[eventraceid][classname]
                except KeyError:
                    if classname not in classraces[eventraceid]:
                        newclassrace = True
                    else:
                        cr = classraces[eventraceid][classname]

                if newclassrace is True: 
                    logger.debug('Creating new Classrace with eventrace id '
                    '{0}, class {1}'.format(eventraceid, classname.encode('utf-8')))
                    racetype = eventrace.attrib['raceDistance']
                    cr = ClassRace(er, classname, racetype=racetype)
                    classraces[eventraceid][classname] = cr
                else:
                    logger.debug('Classrace with eventrace id {0}, class {1} already exists, '
                    'using'.format(eventraceid, classname.encode('utf-8')))
                    if add_results is True:
                        cr.splitsFromRaceResult(raceresult, personid, person)
                    classraces[eventraceid][classname] = cr

        return {'eventraces': eventraces.values(), 'classraces':
                            [y for x in classraces.values() for y in x.values()]}

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
