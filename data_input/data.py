import os, string, random, logging, urllib2
import connections, constants
from lxml import etree
from urllib2 import HTTPError
log = logging.getLogger(__name__)

# how to do relays? --> teamresult instead of personresult
# how many competitorstatus are there? OK, didnotstart, ...
# currently person-based. Every person results are parsed. Should make it so
# that we only download once per event

# error handling of not found elements
class BaseData(object):
    def __init__(self):
        self.db_obj = None

    def attach_django_object(self, obj):
        self.db_obj = obj

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
        self.eventraceid = eventraceid
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

class EventorData(object):
    def __init__(self):
        self.events = {}
        self.eventraces = {}
        self.classraces = {}
        self.connection = connections.EventorConnection()
           
    def get_competitors(self, personid=None):
        memberxml = \
            self.connection.download_all_members(constants.ORGANISATION_ID)
        clubmembers = self.filter_competitor(memberxml, personid)
        # FIXME handle clubmembers==False error
        self.competitors = self.add_competition_data(clubmembers)
    
    def get_newmember_races(self, members):
        pass
        # set todate to 7 d before now, leave out fromdate
        # call get_events
        # parse events, eventraces, classraces
        # define personruns
    
    def get_recent_races(self, members):
        pass
        # set fromdate to 7d before
        # call get_events
        # parse events, eventraces, classraces
        # define personruns

    def get_results_by_race(self, races):
        # loop through events
        # if event is in 'races', keep it, otherwise dump
        # of filtered list, get all results
        # parse results of the races that we need
        # attach results to races
        pass

    def get_events(self, members, fromdate=None, todate=None):
        for member in members:
            resultxml = self.connection.download_results(member, days=period,
                                            events=events)
            if resultxml is not None:
                self.parse_results(member, resultxml)

    def get_results(self, members, events=None, period=None):
        for member in members:
            resultxml = self.connection.download_results(member, days=period,
                                            events=events)
            if resultxml is not None:
                self.parse_results(member, resultxml)
    
    def filter_competitor(self, memberxml, eventorid):
        if eventorid==None:
            return [ClubMember(x) for x in memberxml]
        else:
            for member in memberxml:
                cm = ClubMember(member)
                if cm.eventorID == eventorid:
                    return [member]
            # loop falls through, error:
            return False

    def finalize(self):
        """Format some data for easy access by db module"""
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

    def add_competition_data(self, clubmembers):
        competitors = []
        for clubmember in clubmembers:
            try:
                compxml = self.connection.download_competition_data(clubmember.eventorID)
            except HTTPError, e:
                if e.code == 404: # no data in eventor on certain competitor
                    continue
            else:
                clubmember.parse_competitiondetails(compxml) 
                competitors.append(clubmember)
        return competitors
    
    def parse_newmember_classraces(self, results, members):
        # loop through event results
        # create events, eventraces and classraces
        # return classraces
        pass

    def parse_results(self, person, results):
        if results.tag == 'ResultListList':
            for resultlist in results:
                self.parseResultList(resultlist, person)
        elif results.tag == 'ResultList':
            self.parseResultList(results, person)
    
    def parseResultList(self, xml, clubmember):
        # map result to Event
        eventxml = xml.find('Event')
        eventid = eventxml.find('EventId').text
        if eventid not in self.events:
            event = Event(eventxml, eventid)
            self.events[eventid] = event
        else:
            # select already existing event
            event = self.events[eventid]
        # parse class results
        classresults = xml.findall('ClassResult')
        for classresult in classresults:
            # first get classname, raceids
            eventclassinfo = classresult.find('EventClass')
            classname = eventclassinfo.find('Name').text
            personresults = classresult.findall('PersonResult')
            if personresults == []: # teamresult - what to do?
                continue
            elif personresults[0].find('RaceResult') is not None:
                eventraceids = eventclassinfo.find('.//EventRaceId').text
                # Make classraces (or not if already made) and attach to persons.
                attach_ids = self.parseRaceResults(personresults, eventraceids, \
                            clubmember.eventorID, event, classname) # multiday -> multiple classraces!!
                for raceid in attach_ids:
                    self.attachRaceToObject(self.classraces[raceid][classname],
                                        raceid, clubmember)
                
            else:
                eventraceid = eventclassinfo.find('.//EventRaceId').text
                if eventraceid not in self.eventraces:
                    self.classraces[eventraceid] = {}
                    self.eventraces[eventraceid] = EventRace(event,
                        eventraceid, event.name, event.startdate, lightcondition)
                if classname not in self.classraces[eventraceid]:
                    # create new classrace
                    cr = ClassRace(self.eventraces[eventraceid], classname)
                    # add splittimes
                    for personresult in personresults:
                        cr.splitsFromSingleResults(personresult)
                    # attach to eventrace
                    self.attachRaceToObject(cr, eventraceid, eventrace)
                    self.classraces[eventraceid][classname] = cr 
                # and attach to clubmember
                self.attachRaceToObject(self.classraces[eventraceid][classname],
                                    eventraceid, clubmember)
    
    def attachRaceToObject(self, classrace, eventraceid, obj):
        """Attaches classrace to an object: event, person, etc """
        # Is attaching necessary?
        if eventraceid not in obj.classraces:
            obj.classraces[eventraceid] = {}
        obj.classraces[eventraceid][classrace.classname] = classrace
        return
        
    def parseRaceResults(self, personresults, raceids, competitorid, event, classname):
        # gather which classraces should be parsed
        ids_toparse = self.checkCompetitorStartInRace(personresults, competitorid)
        started = ids_toparse[:]
        for raceid in ids_toparse[::-1]:
            if raceid in self.eventraces and classname in self.classraces[raceid]:
                ids_toparse.pop(ids_toparse.index(raceid) )
        
        if not ids_toparse:
            return started # no need to do anything, attach races in started to person
        else:
            for personresult in personresults:
                person = personresult.find('Person')
                try: # not all competitors are registered in eventor
                    personid = person.find('PersonId').text
                except AttributeError:
                    personid = ''
                # iterate through raceresults
                for raceresult in personresult.findall('RaceResult'):
                    eventrace = raceresult.find('EventRace')
                    eventraceid = eventrace.find('EventRaceId').text
                    # check if race should be parsed (starting clubmembers, not yet parsed for other member)
                    if eventraceid not in ids_toparse:
                        continue
                        
                    # check if there is no existing classrace made -> make new one. 
                    # necessary because personresults are iterated through.
                    if eventraceid not in self.eventraces:
                        light = eventrace.attrib['raceLightCondition']
                        name = eventrace.find('Name').text
                        date = eventrace.find('RaceDate').find('Date').text
                        self.eventraces[eventraceid] = EventRace(event,
                                        eventraceid, name, date, light)
                        self.classraces[eventraceid] = {}
                    if classname not in self.classraces[eventraceid]:
                        racetype = eventrace.attrib['raceDistance']
                        # make new classrace, attach to event
                        self.classraces[eventraceid][classname] = \
                                 ClassRace(self.eventraces[eventraceid], classname, racetype=racetype)
                        self.attachRaceToObject(self.classraces[eventraceid][classname],
                                    eventraceid, eventrace)
                    # add splits
                    self.classraces[eventraceid][classname].splitsFromRaceResult(raceresult, personid, person)
            return started # returned list with raceids to attach to person 
        
        
    def checkCompetitorStartInRace(self, personresults, competitorid):
        """Check in which classraces a clubmember started."""
        eventraceids = []
        for personresult in personresults:
            person = personresult.find('Person')
            try: # not all competitors are registered in eventor
                personid = person.find('PersonId').text
            except AttributeError:
                personid = None
            # iterate through raceresults
            for raceresult in personresult.findall('RaceResult'):
                # Check if the requested clubmember did start, if not: next raceresult.
                if personid == competitorid and \
                        raceresult.find('Result').find('CompetitorStatus').attrib['value'] != \
                        'DidNotStart':
                    eventrace = raceresult.find('EventRace')
                    eventraceids.append(eventrace.find('EventRaceId').text )
        
        return eventraceids
