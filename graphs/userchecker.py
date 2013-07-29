from graphs.models import PersonRun, Person, Si

class User(object):
    def __init__(self, user):
        self.user = user
        if user.is_authenticated():
            self.fullname = '{0} {1}'.format(
                user.first_name.encode('utf-8'),
                user.last_name.encode('utf-8'))
            self.alias = user.username
            self.person = Person.objects.get(user=self.user.id)
            self.sis = Si.objects.filter(person=self.person)

    def is_loggedin(self):
        return self.user.is_authenticated()

    def has_race(self, raceid):
        races = PersonRun.objects.all().filter(classrace_id=raceid,
        person_id=self.get_competitorID() )
        if len(races) > 0 and int(raceid) in [x.classrace_id for x in races]:
            return True

    def is_uk(self):
        pass
    
    def get_sportident(self):
        return [x.si for x in self.sis]

    def get_eventorID(self):
        return self.person.eventor_id

    def get_competitorID(self):
        return self.person.id


class AnonymousUser(object):
    def __init__(self):
        pass

    def get_user_from_urllogin(self, random_id):
        # FIXME timestamp different when firsttime (1 week)
        user = False
        try:
            urllogin = UrlLogin.objects.get(randomid=random_id)
        except UrlLogin.DoesNotExist:
            return False
        
        self.firsttime = urllogin.firsttime
        diff = datetime.datetime.now() - urllogin.timestamp
        if self.firsttime:
            if diff.days < 7:
                user = User(urllogin.user)
        else:
            if diff.days == 0 and diff.seconds < 900: # 15 min max
                user = User(urllogin.user)
        
        return user
