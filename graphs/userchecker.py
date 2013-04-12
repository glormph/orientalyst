from graphs.models import PersonRun, Person #, Classrace, Result, Split, Person

class User(object):
    def __init__(self, user):
        self.fullname = '{0} {1}'.format(
            user.first_name.encode('utf-8'),
            user.last_name.encode('utf-8'))
        self.user = user
        self.alias = user.username
        self.person = Person.objects.get(user=self.user.id)

    def is_loggedin(self):
        return self.user.is_authenticated()

    def has_race(self, raceid):
        races = PersonRun.objects.all().filter(classrace_id=raceid,
        person_id=self.get_competitorID() )
        if len(races) > 0 and int(raceid) in [x.classrace_id for x in races]:
            return True

    def is_uk(self):
        pass

    def get_eventorID(self):
        return self.person.eventor_id

    def get_competitorID(self):
        return self.person.id

