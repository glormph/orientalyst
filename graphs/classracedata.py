from models import PersonRun, Classrace, Result, Split 

class ClassRaceData(object):
    def __init__(self, cr):
        self.results = Result.objects.filter(classrace=cr.id).order_by('position')
        self.data = {}
        for result in self.results:
            eid = result.person_eventor_id
            self.data[ eid ] = {}	
            self.data[eid]['name'] = '{0} {1}'.format( \
                result.firstname.encode('utf-8'),
                result.lastname.encode('utf-8'))
            self.data[eid]['result'] = result.position
            ttime = result.time.split(':')
            self.data[eid]['totaltime'] = int(ttime[0]) * 60 + int(ttime[1])
            splits = [x.splittime for x in Split.objects.filter(result = 
            result.id).order_by('split_n')]
            
            # sometimes no split times in the xml, but splits are included
            try:
                splits = [int(x.split(':')[0])*60 + int(x.split(':')[1]) for x in splits]
            except ValueError:
                self.data[eid]['splits'] = []
            else:
                self.data[eid]['splits'] = splits
        
        # when no splits are found, set flag
        if not False in [self.data[x]['splits']==[] for x in self.data]:
            self.hassplits = False
            return # FIXME sometimes no splits have been uploaded. The whole
                   # thing becomes useless
        else:
            self.hassplits = True
            newdata = {}
            for eid in self.data:
                if self.data[eid]['splits'] != []:
                    newdata[eid] = self.data[eid]
            self.data = newdata

        self.getLegTimes()
        self.fastest_splits = self.getFastest('splits')
        self.fastest_legs = self.getFastest('legs')
        for eid in self.data:
            self.data[eid]['legdiffs'] = self.getDiffs('legs', \
                    self.data[eid]['legs'], self.fastest_legs)
            self.data[eid]['splitdiffs'] = self.getDiffs('splits', \
                    self.data[eid]['splits'], self.fastest_splits)
            self.data[eid]['mistakes'] = \
                    self.calculateMistakes( self.data[eid]['legdiffs'] )
            self.data[eid]['totalmistakes'] = sum(self.data[eid]['mistakes'])
            self.data[eid]['spread'] = self.calculateSpread( \
                    self.data[eid]['legdiffs'])

    def getDiffs(self, leg_or_split, times, fastest):
        diffs = []
        for n,time in enumerate(times):
            diffs.append(time - fastest[n]['time'])
        return diffs       

    def getLegTimes(self):
        for eid in self.data:
            prev_split = 0
            self.data[eid]['legs'] = []
            for split in self.data[eid]['splits']:
                self.data[eid]['legs'].append( split - prev_split) #FIXME what if no success?
                prev_split = split
        
    def getFastest(self, legsplit):
        fastest = {}
        for eid in self.data:
            for n,time in enumerate(self.data[eid][legsplit]):
                if not n in fastest:
                    fastest[n] = {'time': time, 'eid': eid}
                elif time < fastest[n]['time']:
                    fastest[n]['time'] = time
                    fastest[n]['eid'] = eid
        return fastest

    def calculateMistakes(self, legs):
        mistakes = []
        relative_diffs = []
        for n,leg in enumerate(legs):
            relative_diffs.append(leg / float(self.fastest_legs[n]['time']))
        avg_reldiff = sum(relative_diffs)/len(relative_diffs)
        for n,reldif in enumerate(relative_diffs):
            rel_mistake = reldif - avg_reldiff - 0.2
            if rel_mistake > 0: # mistake found
                mistakes.append( rel_mistake * self.fastest_legs[n]['time'])
            else:
                mistakes.append(0)
        return mistakes

    def calculateSpread(self, diffs):
        relative_diffs = []
        for n,dif in enumerate(diffs):
            relative_diffs.append(float(dif) / self.fastest_legs[n]['time'])
        # now calculating sd, I think
        avg = sum(relative_diffs) / len(relative_diffs)
        return pow(sum([(val - avg)**2 for val in relative_diffs]) / \
                len(relative_diffs), 0.5)

    def getPositionPerSplit(self):
        pass
