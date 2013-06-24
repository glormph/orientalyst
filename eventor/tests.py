#!python
# -*- coding: utf-8 -*-

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import os, copy, json
from lxml import etree
import mocks
import dbupdate as iu
from django.test import TestCase
from graphs.models import Person, Si, Event, Classrace, Result, Split, PersonRun

class PasswordResetNewUserTest(TestCase):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']
    def setUp(self):
        self.competitors = [
            mocks.BaseMock( SInrs = ['123'],
                            firstname = 'Pelle',
                            lastname = 'Plupp',
                            email = 'ladu@local.not',
                            eventorID = 45678979,
                            ),
            mocks.BaseMock( SInrs = ['1234'],
                            lastname = 'Rutger',
                            firstname = 'Jönåker',
                            email = 'rutgerj@hot.not',
                            eventorID = 45667867,
                            ),
            mocks.BaseMock( SInrs = ['12'],
                            firstname = 'Surbritt',
                            lastname = 'Jonsson',
                            email = 'suris@local',
                            eventorID = 45687907,
                            )]

    def test_members_returned(self):
        iu.password_reset_for_new_users(self.competitors)
        from django.core.mail import outbox
        assert outbox[0].to == [self.competitors[0].email]

    def test_mail_address_wrong(self):
        iu.password_reset_for_new_users([self.competitors[-1]])
        from django.core.mail import outbox
        assert outbox == []

class PersonUpdateOldMembersTest(TestCase):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']

    def setUp(self):
        with open('eventor/fixtures/test_competitors.json') as fp:
            personfixtures = json.load(fp)
        self.eventordata = iu.eventorobjects.EventorData()
        self.eventordata.competitors = []
        for fix in personfixtures:
            comp = iu.eventorobjects.ClubMember()
            for attr in fix['attributes']:
                setattr(comp, attr, fix['attributes'][attr])
            self.eventordata.competitors.append(comp)
        # only use the first 4 competitors of the fixture
        self.eventordata.competitors = self.eventordata.competitors[0:4]
        
    def test_members_returned(self):
        oldmem_in_db = Person.objects.all()

        oldmem,newmem = iu.update_db_persons(self.eventordata)
        assert newmem == []
        for mem in oldmem:
            assert mem in self.eventordata.competitors
        assert len(oldmem_in_db) == len(Person.objects.all())

class PersonUpdateNewMembersTest(TestCase):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']
    def setUp(self):
        self.eventordata = iu.eventorobjects.EventorData()
        self.eventordata.competitors = [
            mocks.BaseMock( SInrs = ['123'],
                            firstname = 'Pelle',
                            lastname = 'Plupp',
                            email = 'boekeltjuh@hotmail.com',
                            eventorID = 45678979,
                            ),
            mocks.BaseMock( SInrs = ['1234'],
                            lastname = 'Rutger',
                            firstname = 'Jönåker',
                            email = 'boekeltjuh@hotmail.com',
                            eventorID = 45667867,
                            ),
            mocks.BaseMock( SInrs = ['12'],
                            firstname = 'Surbritt',
                            lastname = 'Jonsson',
                            email = 'suris@localhost',
                            eventorID = 45687907,
                            )]

    def test_members_returned(self):
        oldmem,newmem = iu.update_db_persons(self.eventordata)
        assert oldmem == []
        for mem in newmem:
            assert mem in self.eventordata.competitors
        
    def test_members_created(self):
        oldmem,newmem = iu.update_db_persons(self.eventordata)
        newpersons = Person.objects.filter(eventor_id__in=[x.eventorID for x in \
        self.eventordata.competitors])
        assert len(newpersons) == len(self.eventordata.competitors)
        allsis = Si.objects.all()
        for person in newpersons:
            comp = [x for x in self.eventordata.competitors \
                        if x.eventorID == person.eventor_id][0]
            siobj = [x.si for x in allsis if x.person == person]
            assert siobj == [int(x) for x in comp.SInrs]

class PersonUpdateMixOldNewMembers(PersonUpdateOldMembersTest):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']
    def setUp(self):
        super(PersonUpdateMixOldNewMembers, self).setUp()
        
        self.eventordata.competitors.extend([
            mocks.BaseMock( SInrs = ['123'],
                            firstname = 'Pelle',
                            lastname = 'Plupp',
                            email = 'perplupp@localhost',
                            eventorID = 45678979,
                            ),
            mocks.BaseMock( SInrs = ['1234'],
                            lastname = 'Rutger',
                            firstname = 'Jönåker',
                            email = 'rj@localhost',
                            eventorID = 45667867,
                            ),
            mocks.BaseMock( SInrs = ['12'],
                            firstname = 'Surbritt',
                            lastname = 'Jonsson',
                            email = 'suris@localhost.here',
                            eventorID = 45687907,
                            )])
    
    def test_members_returned(self):
        oldmem,newmem = iu.update_db_persons(self.eventordata)
        assert len(oldmem) == 4
        assert len(newmem) == 3 
        for mem in oldmem:
            assert mem in self.eventordata.competitors
        for mem in newmem:
            assert mem in self.eventordata.competitors


class EventUpdate(TestCase):
    fixtures = ['graphs_events_testdata.json']

    def setUp(self):
        self.events_in_db = {}
        with open('eventor/fixtures/graphs_events_testdata.json') as fp:
            ev_fix = json.load(fp)
        for ev in ev_fix:
            self.events_in_db[ev['fields']['eventor_id']] = \
                mocks.BaseMock( name = ev['fields']['name'],
                                startdate = ev['fields']['startdate'],
                                eventorID = ev['fields']['eventor_id']
                                )

    def test_nochange_in_events(self):
        result = iu.update_events(self.events_in_db)
        assert len(result) == len(self.events_in_db)
        # FIXME check if they have not been updated

    def test_change_in_events(self):
        # only use one event
        event_changing = copy.deepcopy(self.events_in_db[ [x for x in \
                                            self.events_in_db][0]])
        event_changing.name = 'Sergels torg sprint KM'
        event_dict = {event_changing.eventorID : event_changing}
        result = iu.update_events(event_dict)
        assert result[0].name == event_changing.name
        ev_updated = Event.objects.filter(eventor_id=event_changing.eventorID)
        assert len(ev_updated) == 1
        assert ev_updated[0].eventor_id == event_changing.eventorID == \
            self.events_in_db[[x for x in self.events_in_db][0]].eventorID
    
    def test_new_events(self):
        newevents = {}
        newevents[1] = mocks.BaseMock(  name = 'Nya Karolinska Sprint',
                                        startdate = '2010-01-03',
                                        eventorID = 1)

        before = Event.objects.all()
        len(before) # executes lazy query, otherwise it will include new event.
        result = iu.update_events(newevents)
        assert len(Event.objects.all()) - len(before) == 1
        newquery = Event.objects.filter(eventor_id=1)
        assert len(newquery) == 1
        assert newquery[0].name == newevents[1].name


class UpdateClassraces(TestCase):
    fixtures = ['graphs_events_testdata.json',
             'graphs_classrace_testdata.json']
    
    def setUp(self):
        cr_db = Classrace.objects.get(pk=1)
        self.oldcr = mocks.BaseMock(
           date=cr_db.startdate,
           classname=cr_db.classname,
           racetype=cr_db.racetype,
           lightcondition=cr_db.lightcondition,
           name=cr_db.name,
           event = mocks.BaseMock(
                eventfkey = cr_db.event)
        )
        self.firstevent = Event.objects.get(pk=1)
        
        
    def test_old_classrace(self):
        allcrs_before = [x for x in Classrace.objects.all()]
        iu.update_classraces([self.firstevent], [self.oldcr])
        allcrs_after = [x for x in Classrace.objects.all()]
        assert allcrs_before == allcrs_after

    def test_update_old_classrace(self):
        updatedcr = copy.deepcopy(self.oldcr)
        updatedcr.lightcondition = 'updated light'
        allcrs_before = [x for x in Classrace.objects.all()]
        iu.update_classraces([self.firstevent], [updatedcr])
        allcrs_after = [x for x in Classrace.objects.all()]
        assert len(allcrs_before) == len(allcrs_after)
        assert allcrs_before != allcrs_after 

    def test_new_classrace_of_empty_event(self):
        secondevent = Event.objects.get(pk=2)
        newcr = copy.deepcopy(self.oldcr)
        newcr.classname = 'new classname'
        newcr.racetype = 'short'
        newcr.event.eventkey = secondevent
        newcr.name = 'new name'
        
        allcrs_before = [x for x in Classrace.objects.all()]
        iu.update_classraces([secondevent], [newcr])
        allcrs_after = [x for x in Classrace.objects.all()]
        assert len(allcrs_before) == len(allcrs_after) - 1


class UpdateResults(TestCase):
    fixtures = ['graphs_classrace_testdata.json', 'graphs_events_testdata.json',  'graphs_result_testdata.json']

    def setUp(self):
        self.results_before = [x for x in Result.objects.all()]
        crfkey = Classrace.objects.get(pk=1) 
        self.oldcr = mocks.BaseMock(classrace_fkey=crfkey, results = {
            '23': {   'firstname': 'Per',
                    'lastname': 'Permans',
                    'position': 2,
                    'status': 'OK',
                    'time': '130',
                    'diff': '0'}})
        
        self.newcr = mocks.BaseMock(classrace_fkey=crfkey, results = {
            '45': {   'firstname': 'Jonny',
                    'lastname': 'Jonnison',
                    'position': 5,
                    'status': 'OK',
                    'time': '200',
                    'diff': '50'}})

    def test_oldresults(self):
        iu.update_results([self.oldcr])
        results_after = [x for x in Result.objects.all()]
        assert self.results_before == results_after

    def test_newresults(self):
        iu.update_results([self.newcr])
        results_after = [x for x in Result.objects.all()]
        assert len(self.results_before) == len(results_after) - 1
     
    def test_badresults(self):
        pass
        # FIXME what are bad results?
        # what exceptions need handling?

    def test_mixed_oldnew_results(self):
        iu.update_results([self.oldcr, self.newcr])
        results_after = [x for x in Result.objects.all()]
        assert len(self.results_before) == len(results_after) - 1

class UpdateSplit(TestCase):
    fixtures = ['graphs_classrace_testdata.json',
    'graphs_events_testdata.json',  'graphs_result_testdata.json',
    'graphs_split_testdata.json']

    def setUp(self):
        self.splits_before = [x for x in Split.objects.all()]

    def test_newsplit(self):
        spobj = Split.objects.get(pk=1)
        resobj = spobj.result
        highest_splitn = max([x.split_n for x in \
                        Split.objects.filter(result=resobj)])

        cr = mocks.BaseMock(results={resobj.person_eventor_id : 
                                      {'resultobj': resobj,
                                       'splits': [{'split_n': highest_splitn+1 ,
                                            'time': spobj.splittime}]
                                      }
                                    })

        iu.update_splits([cr])
        assert len(self.splits_before) == len([x for x in Split.objects.all()]) - 1

    def test_oldsplit(self):
        spobj = Split.objects.get(pk=1)
        resobj = spobj.result
        cr = mocks.BaseMock(results={resobj.person_eventor_id : 
                                      {'resultobj': resobj,
                                       'splits': [{'split_n': spobj.split_n,
                                            'time': spobj.splittime}]
                                      }
                                    })

        iu.update_splits([cr])
        assert self.splits_before == [x for x in Split.objects.all()]


class UpdatePersonRun(TestCase):
    fixtures = ['graphs_person_testdata.json', 'graphs_classrace_testdata.json',
    'graphs_events_testdata.json', 'graphs_personrun_testdata.json',
    'graphs_si_testdata.json', 'auth_user_testdata.json']
    
    def setUp(self):
        self.oldentries = [x for x in PersonRun.objects.all()]
        crfkey = self.oldentries[0].classrace
        self.aclassrace = mocks.BaseMock(classrace_fkey=crfkey)

    def test_oldpersonrun(self):
        person = self.oldentries[0].person
        competitor = mocks.BaseMock(classraces = { 1 : { 'H21':
                self.aclassrace } },
                person_fkey = person)
        edata = mocks.BaseMock(
            competitors = [competitor],
            classraces = [self.aclassrace])

        iu.update_personrun(edata)
        assert self.oldentries == [x for x in PersonRun.objects.all()]

    def test_newpersonrun(self):
        # get person not existing in fixtures
        i = 1
        while i in [x.person.id for x in self.oldentries]:
            i += 1
        person = Person.objects.get(pk=i)
        competitor = mocks.BaseMock(classraces = { 1 : { 'H21':
                self.aclassrace } },
                person_fkey = person)
        edata = mocks.BaseMock(
            competitors = [competitor],
            classraces = [self.aclassrace])
        iu.update_personrun(edata)
        assert len(self.oldentries) == len([x for x in \
                PersonRun.objects.all()]) -1
