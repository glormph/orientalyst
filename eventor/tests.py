#!python
# -*- coding: utf-8 -*-

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import copy, json
from lxml import etree
import mocks
import init_update as iu
from django.test import TestCase
from graphs.models import Person, Si, Event

class PersonUpdateOldMembersTest(TestCase):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']
    def setUp(self):
        with open('eventor/fixtures/test_competitors.xml') as fp:
            cpxml = etree.fromstring(fp.read())
        self.eventordata = iu.eventorobjects.EventorData()
        self.eventordata.competitors = self.eventordata.parseCompetitors(cpxml)
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
            mocks.BaseMock( SInr = '123',
                            firstname = 'Pelle',
                            lastname = 'Plupp',
                            email = 'perplupp@localhost',
                            eventorID = 45678979,
                            ),
            mocks.BaseMock( SInr = '1234',
                            lastname = 'Rutger',
                            firstname = 'Jönåker',
                            email = 'rj@localhost',
                            eventorID = 45667867,
                            ),
            mocks.BaseMock( SInr = '12',
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
            siobj = [x for x in allsis if x.person == person][0]
            assert siobj.si == int(comp.SInr)

class PersonUpdateMixOldNewMembers(TestCase):
    fixtures = ['auth_user_testdata.json', 'graphs_person_testdata.json']
    def setUp(self):
        with open('eventor/fixtures/test_competitors.xml') as fp:
            cpxml = etree.fromstring(fp.read())
        self.eventordata = iu.eventorobjects.EventorData()
        self.eventordata.competitors = self.eventordata.parseCompetitors(cpxml)
        self.eventordata.competitors = self.eventordata.competitors[0:4]
        self.eventordata.competitors.extend([
            mocks.BaseMock( SInr = '123',
                            firstname = 'Pelle',
                            lastname = 'Plupp',
                            email = 'perplupp@localhost',
                            eventorID = 45678979,
                            ),
            mocks.BaseMock( SInr = '1234',
                            lastname = 'Rutger',
                            firstname = 'Jönåker',
                            email = 'rj@localhost',
                            eventorID = 45667867,
                            ),
            mocks.BaseMock( SInr = '12',
                            firstname = 'Surbritt',
                            lastname = 'Jonsson',
                            email = 'suris@localhost',
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

