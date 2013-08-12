# vim: set fileencoding=utf-8 :
import sys, os, string, random
import constants
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from graphs.models import Person, Event, EventRace, Classrace, PersonRun, \
                        Result, Si, Split 

def get_old_members(data):
    old_persons = Person.objects.all().filter(eventor_id__in=[x.eventorID \
                for x in data.competitors])
    eventorid_person_lookup = {str(x.eventor_id): x for x in old_persons}
    old_members = [x for x in data.competitors if x.eventorID in
                        eventorid_person_lookup]
    return old_members, eventorid_person_lookup

def update_db_persons(data):
    """Feed downloaded eventor data, db will be updated with persons."""
    new_members, new_persons = [], []
    old_members, eventorid_person_lookup = get_old_members(data)
    for competitor in data.competitors:
        if competitor not in old_members:
            # first get user account since it needs to exist before updating db
            useraccount = create_user_account(competitor)
            person = Person(eventor_id=competitor.eventorID,
                    firstname=competitor.firstname, lastname=competitor.lastname,
                    user=useraccount)
            person.save() # no need for bulk insert, usually few persons
            competitor.person_fkey = person
            new_persons.append( person )
            new_members.append( competitor )

    for competitor in old_members:
        # add person and sinr django objects to competitors
        competitor.person_fkey = eventorid_person_lookup[competitor.eventorID]
        competitor.si_fkeys = {}
        for sinr in competitor.SInrs:
            siobj = Si.objects.get(si=int(sinr), 
                person_id=eventorid_person_lookup[competitor.eventorID])
            competitor.si_fkeys[int(sinr)] = siobj
        # FIXME upsert in case of name/email change?
    for person, member in zip(new_persons, new_members):
        member.si_fkeys = {}
        for sinr in member.SInrs:
            si = Si(si=int(sinr), person=person)
            si.save()
            member.si_fkeys[int(sinr)] = si
    
    return old_members, new_members

def create_user_account(person):
    # should probably be put in file with other user/account code
    # check if user account exists:
    try:
        existing_user = User.objects.get(email=person.email)
    except User.DoesNotExist:
        pass
    else:
        return existing_user

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

    # empty mail people get an account too. Wont be mailing them though.
    if not person.email:
        person.email = '{0}_{1}@localhost'.format(person.firstname,
                            person.lastname)
        
    # now create user and save
    user = User.objects.create_user(username, person.email, password)
    user.first_name = person.firstname
    user.last_name = person.lastname
    user.save()
    
    return user

def password_reset_for_new_users(persons):
    for person in persons:
        # for testing, email addresses to be ignored
        if person.email.split('@')[1] == 'localhost':
            continue
        form = PasswordResetForm({'email': person.email}) 
        if form.is_valid():
            form.save(from_email=constants.FROM_EMAIL)

def get_lookup_by_type(d, k):
    if type(d) == dict:
        out = d[k]
    else:
        out = getattr(d, k)
    return out

def update_db_entry(obj, data, objattrs, dataattrs, objfkeys=[], datafkeys=[]):
    changed = False
    # check update attributes
    for ok,dk in zip(objattrs, dataattrs):
        if getattr(obj, ok) != get_lookup_by_type(data, dk):
            setattr(obj, ok, get_lookup_by_type(data, dk))
            changed = True

    # check updated fkeys
    for ok,dk in zip(objfkeys, datafkeys):
        fkey = data.get_fkey(dk)
        assert fkey is not None
        if getattr(obj, ok) != fkey:
            setattr(obj, ok, fkey)
            changed = True
    if changed:
        obj.save()

def generate_db_entry(model, data, objattrs, dataattrs, objfkeys=[], datafkeys=[]):
    obj = model()
    # set attributes
    for ok,dk in zip(objattrs, dataattrs):
        setattr(obj, ok, get_lookup_by_type(data, dk))
    # set fkeys
    for ok,dk in zip(objfkeys, datafkeys):
        fkey = data.get_fkey(dk)
        assert fkey is not None
        setattr(obj, ok, fkey)
    return obj


def update_objects_by_eventor_id(data, model, model_attributes,
                data_attributes, model_fkeys=[], data_fkeys=[]):
    old_objs = model.objects.filter(eventor_id__in=[int(x) for x in \
                    data]) # events is a dict with eventorIDs as keys
    old_ids = [x.eventor_id for x in old_objs]
    new_data = {x: data[x] for x in data if x not in \
                old_ids }
    
    # update old objects
    for obj in old_objs:
        data_obj = data[obj.eventor_id]
        update_db_entry(obj, data_obj,  model_attributes,
                        data_attributes, model_fkeys, data_fkeys)

    # insert new objects
    all_objs = []
    for d in new_data.values():
        obj = generate_db_entry(model, d, model_attributes,
                            data_attributes, model_fkeys, data_fkeys)
        obj.save()
        d.attach_django_object(obj)
        all_objs.append(obj)

    all_objs.extend(list(old_objs))
    return all_objs


def update_events(events):
    return update_objects_by_eventor_id(events, Event,
                                ['name', 'startdate', 'eventor_id'],
                                ['name', 'startdate', 'eventorID'])


def update_eventraces(eventraces):
    return update_objects_by_eventor_id(events, EventRace,
                                ['eventor_id', 'startdate',
                                'lightcondition', 'name'],
                                ['eventorID', 'startdate',
                                'lightcondition', 'name'],
                                model_fkeys=['event'], data_fkeys=[0])
    

def update_classraces(eventraces, classraces):
    # get classraces in db
    cr_indb = Classrace.objects.filter(eventrace__in=[x for x in
                eventraces])
    
    # classraces have no eventorid, which is silly. Instead, there is a
    # eventraceid which is an id for all races of a given competition(day). We
    # assume each classname only races once per eventrace.
    
    # first create a dict containing pks for lookup and a tuple of the object and a
    # dict with relevant fields for classrace comparison
    cr_indb_dict = { x.pk: ( x, {'eventrace': x.eventrace, 
                    'classname': x.classname} ) for x in cr_indb }
    # filter downloaded classraces with/without db entry
    for cr in classraces:
        cr.erace_fkey = cr.eventrace.eventracefkey
        cr_idfields = {'eventrace': cr.erace_fkey, 'classname' : cr.classname }
        is_newcr = True
        for pk in cr_indb_dict:
            if cr_idfields == cr_indb_dict[pk][1]:
                is_newcr = False
                # update old classrace
                cr.classrace_fkey = cr_indb_dict[pk][0]
                update_db_entry(cr.classrace_fkey, cr,
                        ['eventrace', 'classname', 'racetype'],
                        ['erace_fkey', 'classname', 'racetype'])
                break
        if is_newcr:
            classrace = generate_db_entry(Classrace, cr,
                ['eventrace', 'classname', 'racetype'],
                ['erace_fkey', 'classname', 'racetype'])
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


def update_personruns(eventordata):
    """Updates who-runs-what table"""

    # first make person_run objects in eventordata
    # this maybe can be done in eventor file
    eventordata.person_runs = []
    for p in eventordata.competitors:
        for erid in p.classraces:
            for cn in p.classraces[erid]:
                eventordata.person_runs.append({
                    'person': p.person_fkey,
                    'classrace': p.classraces[erid][cn].classrace_fkey,
                    })
    
    # get old personruns and create a lookup
    oldprs = PersonRun.objects.filter(classrace__in = \
            [x.classrace_fkey for x in eventordata.classraces])
    oldprlookup = {}
    newprs = []
    for pr in oldprs:
        if not pr.classrace in oldprs:
            oldprlookup[pr.classrace] = {}
        oldprlookup[pr.classrace][pr.person] = pr

    # now update
    for prun in eventordata.person_runs:
        try:
            probj = oldprlookup[ prun['classrace'] ][ prun['person'] ]
        except KeyError:
            newprs.append(PersonRun(  
                person=prun['person'],
                classrace = prun['classrace']))
        else:
            update_db_entry(probj, prun,
                    ['person', 'classrace'],
                    ['person', 'classrace'])
    
    PersonRun.objects.bulk_create(newprs)
    # done


