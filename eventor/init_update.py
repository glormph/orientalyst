# vim: set fileencoding=utf-8 :
import sys, os, string, random
import eventorobjects, postgres
from olstats import settings
from django.core.management import setup_environ
setup_environ(settings)
from django.contrib.auth.models import User

def initialize():
    db = postgres.DatabaseSession('olstats', 'jorrit')
    data = eventorobjects.EventorData()
    data.initialize()
    init_persons_db(db, data)
    update_db_results(db, data)
    db.close()

def update():
    data = eventorobjects.EventorData()
    data.get_persons()
    db = postgres.DatabaseSession()
    new_members, old_members = update_db_persons(db, data)
    
    for person in new_members:
        data.getResults(person)
    for person in old_members:
        data.getResults(person, days=7) 
    
    update_db_results(db, data)
    db.close()


def createTables(db):
    pass
    # IS DONE IN DJANGO with SYNCDB

def init_persons_db(db, data):
    print 'Writing to persons DB'
    for person in data.competitors:
        # if necessary, create a user account
        userid = create_user_account(person)
        db.runwrite('insert', 'graphs_person', schema=None, eventor_id=person.eventorID,
                firstname=person.firstname, lastname=person.lastname,
                user_id=userid)
        person.sqlid = db.fetchone('graphs_person', ['id'],
        eventor_id=person.eventorID)[0]
        db.runwrite('insert', 'graphs_si', person_id=person.sqlid, si=person.SInr) 
        person.si_sqlid = db.fetchone('graphs_si', ['id'], id=person.sqlid)[0]


def create_user_account(person):
    # check if user account exists:
    try:
        existing_user = User.objects.get(email=person.email)
    except User.DoesNotExist:
        pass
    else:
        return existing_user.id

    print 'Creating user account'
    # empty mail people get an account too. Wont be mailing them though.
    if not person.email:
        print 'No email found!'
        print person.firstname, person.lastname
        person.email = '{0}_{1}@localhost'.format(person.firstname,
        person.lastname)
    
    # username, generate one
    username = person.firstname
    samefirstname = User.objects.all().filter(first_name=username)
    nr = len(samefirstname)
    if nr > 0:
        username += str(nr)
    username = username.lower()
    
    # generate random password
    chars = string.ascii_letters + string.digits
    random.seed = (os.urandom(1024))
    password = ''.join(random.choice(chars) for i in range(12))

    # now create user and save
    user = User.objects.create_user(username, person.email, password)
    user.first_name = person.firstname
    user.last_name = person.lastname
    user.save()
    return user.id

def update_db_results(db, data):
    print 'Updating results'
    # update events and get sqlid for them
    for event in data.events.values():
        db.runwrite('upsert', 'graphs_event', pk_fields=['eventor_id'], name=event.name, startdate=event.startdate,
                eventor_id=event.eventorID)
        event.sqlid = db.fetchone('graphs_event', ['id'], eventor_id=event.eventorID)[0]
    # update classraces and get their sqlids
    for raceid in data.classraces:
        for classrace in data.classraces[raceid].values():
            db.runwrite('upsert', 'graphs_classrace', pk_fields=['name', 'event_id',
            'classname'], event_id=classrace.event.sqlid,
            startdate=classrace.date, classname=classrace.classname,
            racetype=classrace.racetype,lightcondition=classrace.lightcondition,
            name=classrace.name)
            classrace.sqlid = db.fetchone('graphs_classrace', ['id'],
            name=classrace.name, event_id=classrace.event.sqlid,
            classname=classrace.classname)[0]
            
            for personid in classrace.results:
                db.runwrite('upsert', 'graphs_result', pk_fields=['classrace_id',
                'person_eventor_id'], classrace_id=classrace.sqlid,
                person_eventor_id=personid,
                firstname=classrace.results[personid]['firstname'],
                lastname=classrace.results[personid]['lastname'],
                position=classrace.results[personid]['position'],
                time=classrace.results[personid]['time'],
                status=classrace.results[personid]['status'],
                diff=classrace.results[personid]['diff']
                )
                resultssqlid = db.fetchone('graphs_result', ['id'],
                classrace_id=classrace.sqlid, person_eventor_id=personid)[0]
                
                for splitcc in classrace.results[personid]['splits']:
                    db.runwrite('upsert', 'graphs_split', pk_fields=['result_id',
                    'split_n'], result_id=resultssqlid,
                    split_n=splitcc,
                    splittime=classrace.results[personid]['splits'][splitcc])

    # write to who-runs-what table
    for person in data.competitors:
        for eventraceid in person.classraces:
            for classname in person.classraces[eventraceid]:
                db.runwrite('upsert', 'graphs_personrun', ['person_id', 'si_id',
                'classrace_id'], person_id=person.sqlid, si_id=person.si_sqlid,
                classrace_id=person.classraces[eventraceid][classname].sqlid)


def update_db_persons(db, data):
    new_members = []
    old_members = []
    for person in data.competitors:
        # update/insert person db and check if new members exist
        up = db.runwrite('upsert', 'graphs_person', ['eventor_id', 'firstname', 'lastname'], \
             [person.eventorID, person.firstname, person.familyname])
        if up:
            new_members.append(person)
        else:
            old_members.append(person)
        
        # also update SI table 
        person.sqlid = db.fetchone('graphs_person', ['id'],
        eventor_id=person.eventorID)[0]
        db.runwrite(upsert, 'graphs_si', ['person_id', 'si'], [person.sqlid, person.SInr])
    
    return new_members, old_members

if __name__ == '__main__':
    initialize()
