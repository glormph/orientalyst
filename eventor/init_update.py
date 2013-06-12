# vim: set fileencoding=utf-8 :
import sys, os, string, random
import eventorobjects, postgres
from olstats import settings
from django.core.management import setup_environ
setup_environ(settings)
from django.contrib.auth.models import User
from graphs.models import Person, Event, Classrace, PersonRun, Result, Si,Split 

def update():
    data = eventorobjects.EventorData()
    data.competitors = data.getCompetitors()
    old_members, new_members = update_db_persons(data)
    for person in new_members[:1]:
        resultxml = data.getResults(person)
        data.parseResults(person, resultxml)
    for person in old_members[:1]:
        resultxml = data.getResults(person, days=7) 
        data.parseResults(person, resultxml)
    
    data.finalize() # modifies classraces into a list instead of convolutd dict
    
    events = update_events(data.events)
    update_classraces(events, data.classraces)
    update_results(data.classraces)
    update_splits()
    update_personruns()


def create_user_account(person):
    # check if user account exists:
    try:
        existing_user = User.objects.get(email=person.email)
    except User.DoesNotExist:
        pass
    else:
        return existing_user

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
    return user

def get_lookup_by_type(d, k):
    if type(d) == dict:
        out = d[k]
    else:
        out = getattr(d, k)
    return out

def update_db_entry(obj, data, objkeys, datakeys):
    changed = False
    for ok,dk in zip(objkeys, datakeys):
        if getattr(obj, ok) != get_lookup_by_type(data, dk):
            setattr(obj, ok, get_lookup_by_type(data, dk))
            changed = True
    if changed:
        obj.save()

def generate_db_entry(model, data, objkeys, datakeys):
    obj = model()
    for ok,dk in zip(objkeys, datakeys):
        setattr(obj, ok, get_lookup_by_type(data, dk))
    return obj


def update_events(events):
    # split in old/new events
    old_events = Event.objects.filter(eventor_id__in=[int(x) for x in \
                    events]) # events is a dict with eventorIDs as keys
    old_events_ids = [x.eventor_id for x in old_events]
    new_eventdata = {x: events[x] for x in events if x not in \
                old_events_ids }
     
    # update old events if necessary
    for event in old_events:
        evd = events[ event.eventor_id ]
        update_db_entry(event, evd, 
                        ['name', 'startdate', 'eventor_id'],
                        ['name', 'startdate', 'eventorID'])
    # the rest: insert and give foreign key
    all_events = []
    new_events = []
    for edata in new_eventdata.values():
        event = generate_db_entry(Event, edata, 
                    ['name', 'startdate', 'eventor_id'],
                    ['name', 'startdate', 'eventorID'])
        event.save()
        all_events.append(event)
        edata.eventfkey = event
    all_events.extend(list(old_events))
    return all_events

def update_classraces(events, classraces):
    # get classraces in db
    cr_indb = Classrace.objects.filter(event__in=[x for x in
                events])
    
    # first create a dict containing pks for lookup and a tuple of the object and a
    # dict with relevant fields for classrace comparison
    cr_indb_dict = { x.pk: ( x, {'name': x.name, 'event': x.event, 
                    'classname': x.classname, 'racetype': x.racetype} ) for x in cr_indb }
    
    # filter downloaded classraces with/without db entry
    # since they have no eventorID, we use instead a combination of
    # event, name, classname and racetype
    # PROBLEM: this means these cannot be updated since they are used as
    # lookup! This may present a problem when updating eg classrace name
    # FIXME think about which identifiers to use. date?
    
    for cr in classraces:
        cr.eventfkey = cr.event.eventfkey
        cr_idfields = {'name': cr.name, 'event': cr.eventfkey,
            'classname' : cr.classname, 'racetype': cr.racetype}
        is_newcr = True
        for pk in cr_indb_dict:
            if cr_idfields == cr_indb_dict[pk][1]:
                is_newcr = False
                # update old classrace
                cr.classrace_fkey = cr_indb_dict[pk][0]
                update_db_entry(cr.classrace_fkey, cr,
                        ['event', 'startdate', 'classname', 'racetype',
                                            'lightcondition', 'name'],
                        ['eventfkey', 'date', 'classname', 'racetype', 'lightcondition',
                                            'name'])
                break
        if is_newcr:
            classrace = generate_db_entry(Classrace, cr,
                ['event', 'startdate', 'classname', 'racetype',
                                        'lightcondition', 'name'],
                ['eventfkey', 'date', 'classname', 'racetype',
                                        'lightcondition', 'name'])
            classrace.save()
            cr.classrace_fkey = classrace

def update_results(classraces):
    # get old results from db and make lookup dict
    oldresults = Result.objects.filter(classrace__in=[x.classrace_fkey for x \
                                                    in classraces])
    oldreslookup, newresults = {}, []
    for x in oldresults:
        if x.classrace not in oldreslookup:
            oldreslookup[x.classrace] = {}
        oldreslookup[x.classrace][x.person_eventor_id] = x
    # now filter old results
    for cr in classraces:
        for personid in cr.results:
            cr.results[personid]['eventorID'] = personid
            cr.results[personid]['cr'] = cr.classrace_fkey
            try:
                oldresult = oldreslookup[cr.classrace_fkey][personid]
            except KeyError:
                newresults.append(generate_db_entry(Result,
                                    cr.results[personid], 
                    ['classrace', 'person_eventor_id', 'firstname', 'lastname',
                                        'position', 'time', 'status', 'diff'],
                    ['cr', 'eventorID', 'firstname', 'lastname', 'position', 'time',
                                                            'status', 'diff']))
            else:
                cr.results[personid]['resultobj'] = oldresult
                update_db_entry(oldresult, cr.results[personid],
                    ['classrace', 'person_eventor_id', 'firstname', 'lastname',
                                        'position', 'time', 'status', 'diff'],
                    ['cr', 'eventorID', 'firstname', 'lastname',
                                        'position', 'time', 'status', 'diff'])
    # new results: bulk_create, then get result obj and attach to result datas
    if newresults:
        Result.objects.bulk_create(newresults) 
        newres_cr = Result.objects.filter(classrace__in=[x.classrace \
                    for x in newresults])
        newres_lookup = {}
        for res in newres_cr:
            if res.classrace not in newres_lookup:
                newres_lookup[ res.classrace ] = {}
            newres_lookup[ res.classrace ][ res.person_eventor_id ] = res
        for cr in classraces:
            for personid in cr.results:
                if not 'resultobj' in cr.results[personid]:
                    try:
                        cr.results[personid]['resultobj'] = \
                                newres_lookup[cr.classrace_fkey][personid]
                    except KeyError:
                        raise
                        # FIXME what if not in dict? Lookup problem?


def update_splits(classraces): #FIXME
    # old splits: update
    splitsindb = Split.objects.filter(result__in=\
      [x.results[y]['resultobj'] for x in classraces for y in x.results])
    splitslookup, newsplits = {}, []
    for sp in splitsindb:
        if sp.result not in splitslookup:
            splitslookup[sp.result] = {}
        splitslookup[sp.result][sp.split_n] = sp
    for cr in classraces:
        for pid in cr.results:
            for sp in cr.results[pid]['splits']:
                sp['resultobj'] = cr.results[pid]['resultobj']
                try:
                    spobj = \
                        splitslookup[cr.results[pid]['resultobj']][sp['split_n']]
                except KeyError:
                    newsplits.append( generate_db_entry(Split, sp,
                    ['result', 'split_n', 'splittime'],
                    ['resultobj', 'split_n', 'time']))
                else:
                    update_db_entry(spobj, sp,
                        ['result', 'split_n', 'splittime'],
                        ['resultobj', 'split_n', 'time'])
                
    # new splits: bulk create
    Split.objects.bulk_create(newsplits)


def update_personrun(eventordata):
    # write to who-runs-what table
    eventordata.person_runs = []
    for p in eventordata.competitors:
        for erid in p.classraces:
            for cn in p.classraces[erid]:
                eventordata.person_run.append({
                    'person': p,
                    'classrace': p.classraces[erid][cn].classrace_fkey,
                    'si' : p.si_fkey
                    })
    
    oldprs = PersonRun.objects.filter(classrace__in = eventordata.classraces)
    oldprlookup = {}
    newprs = []
    for pr in oldprs:
        if not pr.classrace in oldprs:
            oldprs[pr.classrace] = {}
        oldprs[pr.classrace][pr.person] = pr
    for prun in eventordata.person_runs:
        try:
            probj = oldprlookup[ prun['classrace'] ][ prun['person'] ]
        except KeyError:
            newprs.append(PersonRun(  person=person.person_fkey,
                    si = person.si_fkey,
                    classrace =
                    person.classraces[er_id][cname].classrace_fkey))
        else:
            update_db_entry(probj, prun,
                    ['si', 'person', 'classrace'],
                    ['si', 'person', 'classrace'])
    
    PersonRun.objects.bulk_create(newprs)
    # done

def update_db_persons(data):
    """Feed downloaded eventor data, db will be updated with persons."""
    new_members, new_persons = [], []

    old_persons = Person.objects.all().filter(eventor_id__in=[x.eventorID \
                for x in data.competitors])
    
    old_members_eventor = [str(x.eventor_id) for x in old_persons]
    old_members = [x for x in data.competitors if x.eventorID in
                        old_members_eventor]
    for competitor in data.competitors:
        if competitor.eventorID not in old_members_eventor:
            useraccount = create_user_account(competitor)
            person = Person(eventor_id=competitor.eventorID,
                    firstname=competitor.firstname, lastname=competitor.lastname,
                    user=useraccount)
            person.save() # no need for bulk insert, usually few persons
            new_persons.append( person )
            new_members.append( competitor )

    for person in old_members:
        pass
        # FIXME upsert in case of name/email change?
    for person, member in zip(new_persons, new_members):
        si = Si(si=member.SInr, person=person)
        si.save()
    
    return old_members, new_members


if __name__ == '__main__':
    initialize()
