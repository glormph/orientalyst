class MockDjangoObject():
    def __init__(self):
        self.saved = False

    def save(self):
        self.saved = True
        return True


class BaseMock():
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

class MockEventorData():
    def getCompetitors(self):
        global gccalled
        gccalled = 1
    
    def getResults(self, p, days=None):
        self.events = ['event1', 'event2']
        self.classraces = ['cr1', 'cr2']
        if days:
            self.days = days
        global grcalled
        grcalled = True

    def finalize(self):
        global fincalled
        fincalled = True
