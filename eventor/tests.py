#!python
# -*- coding: utf-8 -*-

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from lxml import etree
import mocks
import init_update as iu
from django.test import TestCase
from graphs.models import Person, Si

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
        
