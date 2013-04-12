from graphs.models import PersonRun

class RaceList(object):
    def __init__(self, user):
        self.user = user
        self.racelist = \
                PersonRun.objects.all().filter(person=self.user.get_competitorID())
    
    def get_latest_races(self, amount):
        """Returns last x races of a competitor"""
        racelist = self.racelist.order_by('-classrace__startdate')
        racelist = [Race( x.classrace ) for x in racelist]
        return racelist[:amount]
    
    def get_all_races_by_year(self):
        self.allraces = {}
        races = self.racelist.order_by('-classrace__startdate')
        for r in races:
            if not r.classrace.startdate.year in self.allraces:
                self.allraces[ r.classrace.startdate.year ] = []

            self.allraces[ r.classrace.startdate.year ].append( Race(r.classrace) )
        
        # return year
        return sorted(self.allraces.keys())
        


class Race(object):
    def __init__(self, classrace):
        if classrace.event.name == classrace.name:
            self.name = classrace.name
        else:
            self.name = '{0} - {1}'.format(classrace.event.name.encode('utf-8'),
                    classrace.name.encode('utf-8'))
        self.classname = classrace.classname
        self.date = classrace.startdate
        self.cr_id = classrace.id
    
