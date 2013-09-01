import string, random

class BaseData(object):
    def attach_django_object(self, obj):
        self.db_obj = obj
    
    def get_django_object(self):
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
    def __init__(self, event, eventraceid, name, startdate, lightcondition=''):
        self.eventorID = eventraceid
        self.name = name # e.g. 'Etapp 1'
        self.startdate = startdate
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
