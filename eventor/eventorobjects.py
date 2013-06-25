import os, string, random, logging, datetime, urllib2
import eventor, constants
from lxml import etree

log = logging.getLogger(__name__)

# how to do relays? --> teamresult instead of personresult
# how many competitorstatus are there? OK, didnotstart, ...

# i think the problem is in that classraces are created and then dumped

# error handling of not found elements

class ClubMember(object):
    def __init__(self, xml=None):
        self.SInrs = []
        self.lastname = '' 
        self.firstname = ''
        self.email = None
        self.eventorID = None
        self.classraces = {}
        if xml:
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
                self.SInrs.append(ccard.find('CCardId').text)

class Event(object):
    def __init__(self, eventxml, eventid):
        self.classraces = {}
        self.eventorID = eventid
        self.name = eventxml.find('Name').text
        self.startdate = eventxml.find('StartDate').find('Date').text
        self.finishdate = eventxml.find('FinishDate').find('Date').text


class ClassRace(object):
    def __init__(self, event, classname, eventraceid, name, date, racetype='',
    distance='', lightcondition=''):
        self.event = event
        self.classname = classname
        self.eventraceid = eventraceid
        self.name = name # e.g. 'Etapp 1'
        self.date = date
        self.racetype = racetype
        self.distance = distance
        self.lightcondition = lightcondition
        self.results = {}
        self.checkpoints = {}
     
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
#        print self.results[personid]['firstname'], self.results[personid]['familyname']
        try:
            self.results[personid]['position'] = result.find('ResultPosition').text
        except:
            self.results[personid]['position'] = None
        try: # strange, if there isn't time, there is no last split either?
            self.results[personid]['time'] = result.find('Time').text
        except:
            #print self.results[personid]['firstname'], self.results[personid]['familyname'], self.event.eventorID, self.eventraceid
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
        self.classraces = {}
           
    def get_people(self):
        memberxml = self.download_memberxml()
        self.competitors = self.parse_members(memberxml)

    def update_results(self, days=7):
        for person in self.competitors:
            self.getResults(person, days)
    
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
    
    def download_memberxml(self):
        return eventor.eventorAPICall(constants.API_KEY,
            'persons/organisations/636?includeContactDetails=true' )

    def parse_members(self, clubmembersxml):
        competitors = []
        for person in clubmembersxml[0:10]: 
            # one call per competitor, slow
            clubmember = ClubMember(person)
            try:
                competitorxml = eventor.eventorAPICall(constants.API_KEY,
            'competitor/{0}'.format(clubmember.eventorID) )
            except urllib2.HTTPError:
                pass # not a competitor, only a member, skip.
            else:
                clubmember.parse_competitiondetails(competitorxml) 
            competitors.append(clubmember)
        return competitors
        
    def getResults(self, person, days=None):
        # APIcall to get results for a person
        url = 'results/person?personId={0}&top=1000&includeSplitTimes=true'.format(person.eventorID)
        if days:
            # Specify whether to get all results or the ones from a certain date
            now = datetime.datetime.now()
            fromdate = now - datetime.timedelta(days)
            url = '{0}&fromDate={1}-{2}-{3}'.format(url, str(fromdate.year),
                    str(fromdate.month).zfill(2), str(fromdate.day).zfill(2) )
        try:
            results = eventor.eventorAPICall(constants.API_KEY, url)
        except urllib2.HTTPError, e:
            # FIXME figure out when error occurs
            print 'Error occurred in communication with eventor server'
            print e
            return None
        else:
            return results

    def parseResults(self, person, results):
        print 'Parsing results'
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
                    self.attachRaceToObject(self.classraces[raceid][classname], clubmember)
                
            else:
                eventraceid = eventclassinfo.find('.//EventRaceId').text
                if eventraceid not in self.classraces:
                    self.classraces[eventraceid] = {}
                if classname not in self.classraces[eventraceid]:
                    # create new classrace
                    self.classraces[eventraceid][classname] = ClassRace(event, \
                            classname, eventraceid, event.name, event.startdate)
                    # add splittimes
                    for personresult in personresults:
                        self.classraces[eventraceid][classname].splitsFromSingleResults(personresult)
                    # attach to event
                    self.attachRaceToObject(self.classraces[eventraceid][classname], event)
                # and attach to clubmember
                self.attachRaceToObject(self.classraces[eventraceid][classname], clubmember)
    
    def attachRaceToObject(self, classrace, obj):
        """Attaches classrace to an object: event, person, etc """
        if classrace.eventraceid not in obj.classraces:
            obj.classraces[classrace.eventraceid] = {}
        obj.classraces[classrace.eventraceid][classrace.classname] = classrace
        return
       
        self.events[eventid] = event # replace updated event
        
    def parseRaceResults(self, personresults, raceids, competitorid, event, classname):
        # gather which classraces should be parsed
        ids_toparse = self.checkCompetitorStartInRace(personresults, competitorid)
        started = ids_toparse[:]
        for raceid in ids_toparse[::-1]:
            if raceid in self.classraces and classname in self.classraces[raceid]:
                ids_toparse.pop(ids_toparse.index(raceid) )
                #print ids_toparse, len(ids_toparse)
        
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
                    # necessary because personresults are iteraded through.
                    if eventraceid not in self.classraces:
                        self.classraces[eventraceid] = {}
                    if classname not in self.classraces[eventraceid]:
                        racetype = eventrace.attrib['raceDistance']
                        print racetype, type(racetype)
                        light = eventrace.attrib['raceLightCondition']
                        name = eventrace.find('Name').text
                        date = eventrace.find('RaceDate').find('Date').text
                        # make new classrace, attach to event
                        self.classraces[eventraceid][classname] = ClassRace(event, classname, \
                                eventraceid, name, date, racetype, lightcondition=light)
                        self.attachRaceToObject(self.classraces[eventraceid][classname], \
                                event)
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
