from graphs.models import PersonRun
from graphs.models import Result


class RaceList(object):
    def __init__(self, user):
        self.user = user
        if self.user.is_loggedin():
            self.racelist = \
                PersonRun.objects.all().filter(
                    person=self.user.get_competitorID())
        else:
            self.racelist = None

    def get_latest_races(self, amount):
        """Returns last x races of a competitor"""
        if self.racelist is not None:
            racelist = self.racelist.order_by(
                '-classrace__eventrace__startdate')
            racelist = [Race(x.classrace) for x in racelist]
        else:
            return None
        return racelist[:amount]

    def get_all_races_by_year(self):
        self.allraces = {}
        races = self.racelist.order_by('-classrace__eventrace__startdate')
        for r in races:
            if not r.classrace.eventrace.startdate.year in self.allraces:
                self.allraces[r.classrace.eventrace.startdate.year] = []

            self.allraces[r.classrace.eventrace.startdate.year].append(
                Race(r.classrace))

        # return year
        return sorted(self.allraces.keys())[::-1]


class Race(object):
    def __init__(self, classrace):
        if classrace.eventrace.event.name == classrace.eventrace.name:
            self.name = classrace.eventrace.name
        else:
            self.name = '{0} - {1}'.format(
                classrace.eventrace.event.name.encode('utf-8'),
                classrace.eventrace.name.encode('utf-8'))
        self.classname = classrace.classname
        self.date = classrace.eventrace.startdate
        self.cr_id = classrace.id


class RaceData(object):
    def __init__(self, classrace, user_evid):
        try:
            self.results = Result.objects.get(classrace=classrace.id,
                                              person_eventor_id=user_evid)
        except Result.DoesNotExist:
            self.user_has_result = False
        else:
            self.user_has_result = True

        self.info = Race(classrace)
