import math
import classracedata, races
from graphs.models import Result

class PlotSet(object):
    def __init__(self, classrace, user_evid, friends_evid):
        self.results = Result.objects.get(classrace=classrace.id,
                person_eventor_id=user_evid)
        self.raceinfo = races.Race(classrace)
        racedata = classracedata.ClassRaceData(classrace)
        if not racedata.hassplits:
            self.showgraphs = False
            return 
        else:
            self.showgraphs = True
        self.plots = {}

        self.friends_evids = friends_evid
    
        self.plots['splits'] = MultiplePointsPerPersonPlot('splittider',
        'Splittider', racedata.data, user_evid, friends_evid, 'splits', None, 
        'tid (min)', 'kontroll')
        self.plots['bomsplits'] = MultiplePointsPerPersonPlot('bommar',
        'Bommar', racedata.data, user_evid, friends_evid, 'mistakes', None, 'tid (min)', 
        'kontroll')
        self.plots['legbehind'] = MultiplePointsPerPersonPlot('tidskillnader',
        'Tidsskillnader', racedata.data, user_evid, friends_evid, 'legdiffs', None, 
        'tid (min)', 'kontroll')
        self.plots['spread'] = SingePointsPerPersonPlot('spread',
        'Spridning tidsskillnader', racedata.data, user_evid, friends_evid, 'spread', 
        'result', 'std.avvik. tidskillnad(%)', 'placering', 'nottime')
        self.plots['bomtotal'] = SingePointsPerPersonPlot('bomtotal', 'Total'
        'bomtid', racedata.data, user_evid, friends_evid, 'totalmistakes', 'result',
        'tid (min)','placering')
        self.plots['totaltime'] = SingePointsPerPersonPlot('tidefter', 'Tid'
        ' efter vinnare', racedata.data, user_evid, friends_evid, 'diff', 'result', 
        'tid (min)', 'placering',
                )

class BasePlot(object):
    def __init__(self, name, title, racedata, user_evid, friends_evid, y, x=None, ylab=None, xlab=None,
                y_units=None):
        self.name = name
        self.title = title
        self.points = []
        self.xlab = xlab
        self.ylab = ylab
        self.y_units = y_units
        self.user_evid = user_evid
        self.friends_evid = friends_evid
    
    def get_pointstyle(self, pid):
        if str(pid)==str(self.user_evid):
            pointclass = 'userpoint'
            radius = '5px'
        elif pid not in [None, ''] and str(pid) in str(self.friends_evid):
            pointclass = 'friendpoint'
            radius = '3px'
        else:
            pointclass = 'greypoint'
            radius = '1.5px'
        return {'pclass': pointclass, 'radius': radius}
    
    def render_html(self):
        html = [self.base_html()]
        html.append( self.set_ytickmarks() )
        html.append(self.render_data() )
        html.append(self.render_points() )
        html.append(self.render_plot() )
        html.append(self.close_html() )
        return '\n'.join(html)
    
    def base_html(self):
        return """
        <div class="graph" id="%s"><h4>%s</h4></div>
<script>
var width = 500;
var height = 300;
var padding = 50;
var plotname = "%s";
var svg = d3.select("#%s").append("svg:svg").attr("width", width).attr("height",
height);
var xlab = "%s";
var ylab = "%s";
""" % (self.name, self.title, self.name,self.name, self.xlab,
self.ylab)
    
    def render_data(self):
        return """
        data[plotname] = [ %s ];
    var ymax = %s
    var xmax = d3.max(data[plotname], function(datum) {return datum.x;});
    var x = d3.scale.linear().domain([0, xmax]).range([padding, width-padding]);
    var y = d3.scale.linear().domain([0, ymax]).range([padding, height-padding]);
        """ % (',\n'.join(self.points), self.ymax)
    
    def render_points(self):
        return """
// points
svg.selectAll("circle").data(data[plotname]).enter().append("svg:circle")
.attr("cx", function(d) { return x(d.x); })
.attr("cy", function(d) { return height - y(d.y);})
.class(function(d) {return d.dataclass;})
.attr("r", function(d) {return d.rad})
.attr("id", function(d) { return d.eid+"#"+ "%s"; })
.on("mouseover", highlight_point)
.on("mouseout", dehighlight_point)

    """ % self.name
    
    def render_plot(self):
        return """
             
// axes
var axisGroup = svg.append("g");

axisGroup.append("line").attr("x1", padding).attr("x2",
width-padding).attr("y1", height-padding).attr("y2",
height-padding).attr("stroke", "black");
axisGroup.append("line").attr("x1", padding).attr("x2", padding).attr("y1",
padding).attr("y2",
height-padding).attr("stroke", "black");

// tickmarks, 10 for x, 5 for y
var xincrement = Math.ceil(xmax / 10);

// x ticks
axisGroup.selectAll(".xTicks").data(d3.range(0, xmax,
xincrement)).enter().append("line").attr("y1", height-padding).attr("y2",
height-padding+5).attr("x1", function(datum){return x(datum);}).attr("x2",
function(datum) {return x(datum);}).attr("stroke", "black");

axisGroup.selectAll(".xTickNos").data(d3.range(0, xmax,
xincrement)).enter().append("text").attr("y", height-padding+15).attr("x", function(datum){return x(datum);})
.text(function(datum) {return datum;}).attr("fill", "black").attr("class",
"xTickNos").attr("text-anchor", "middle");

// y ticks
axisGroup.selectAll(".yTicks")
    .data(ticks).enter()
    .append("line")
    .attr("x1", padding)
    .attr("x2", padding-5)
    .attr("y1", function(d) {return height-y(d.tick);})
    .attr("y2", function(d) {return height-y(d.tick);})
    .attr("stroke", "black");

axisGroup.selectAll(".yTickNos")
    .data(ticks).enter()
    .append("text")
    .attr("x", padding-7)
    .attr("y", function(d){return height-y(d.tick);})
    .text(function(d) {return d.mark;})
    .attr("fill", "black")
    .attr("class", "xTickNos")
    .attr("text-anchor", "end")
    .attr("dy", 3);

// axis labels
// x axis
axisGroup.append("text")
    .attr("x", (padding + width-padding)/2)
    .attr("y", height-padding/2)
    .text(xlab).attr("fill", "black")
    .attr("text-anchor", "middle");
// y axis
rotation = "rotate(-90, 10" + ", "+ height/2 + ")";
axisGroup.append("text")
    .attr("x", 10)
    .attr("y", height/2)
    .text(ylab).attr("fill", "black")
    .attr("text-anchor", "middle")
    .attr("transform", rotation)
    ;

"""

    def close_html(self):
        return """
        </script>
        """

    def set_ytickmarks(self):
        """Method to determine how tickmarks should be distributed"""

        def tickformatter(ticks, y_units):
            ticksout = {
                'time' : [{'tick': x, 'mark': '%d:%02d' % (x/60, x%60)} for x in ticks],
                'nottime' : [{'tick': x, 'mark': x } for x in ticks]
                }
            return ticksout[y_units]
                
        if self.y_units == 'time': # time tickmarks with minutes
            ymax_minutes = int(self.ymax)/60
            if ymax_minutes > 3: # >3 minutes: show whole minutes on ticks
                rest = ymax_minutes % 5
                ymax_minutes += (5-rest)
                self.ymax = int(ymax_minutes * 60)
            else: # show multiples of 10 seconds
                rest = int(self.ymax) % 10
                self.ymax = int(self.ymax) + (10-rest)
        else:
            rest = self.ymax % 5
            self.ymax = int(self.ymax + (5 - rest))

        yinc = self.ymax/5 # 5 tickmarks
        ticks = range(0, self.ymax, yinc)
        ticks += [ticks[-1]+yinc]
        ticks = tickformatter(ticks, self.y_units)
        ticks = """ticks = {0};""".format(ticks)
        ticks = ticks.replace("\'tick\'", 'tick').replace('\'mark\'',
                        'mark').replace('\'', '\"')
        return ticks

class SingePointsPerPersonPlot(BasePlot):
    def __init__(self, name, title, racedata, user_evid, friends_evid, y, x=None, ylab=None, xlab=None, y_units='time'):
        super(SingePointsPerPersonPlot, self).__init__( name, title, racedata,
                    user_evid, friends_evid, y, x, ylab, xlab, y_units)
        for pid in racedata:
            pdata = self.get_pointstyle(pid)
            self.points.append('{name: "%s", x: %s, y: %s, eid:'
            '"%s", dataclass:"%s", rad:"%s"}' \
                % (racedata[pid]['name'].decode('utf-8'), racedata[pid][x], racedata[pid][y],
                str(pid), pdata['pclass'], pdata['radius'] ))
         
        self.ymax = math.ceil(max([racedata[x][y] for x in racedata]))


class MultiplePointsPerPersonPlot(BasePlot):
    def __init__(self, name, title, racedata, user_evid, friends_evid, y, x=None, ylab=None, xlab=None,
            y_units='time'):
        super(MultiplePointsPerPersonPlot, self).__init__( name, title,
                            racedata, user_evid, friends_evid, y, x, ylab, xlab, y_units)
        points = {}
        for pid in racedata:
            for n,spl in enumerate(racedata[pid][y]):
                pdata = self.get_pointstyle(pid)
                if not n in points:
                    points[n] = []
                points[n].append('{name: "%s", x: %s, y: %s, eid:'
                '"%s", dataclass: "%s", rad: "%s"}' % (racedata[pid]['name'], 
                    n+1, spl, str(pid), pdata['pclass'], pdata['radius']))
        
        xpoints = sorted(points.keys())
        self.points = [x for n in xpoints for x in points[n]]
        ymaxlist = [z for x in racedata for z in racedata[x][y]]
        self.ymax = math.ceil(max(ymaxlist))

    def render_points(self):
        return ('// points \n'
                'svg.selectAll("circle").data(data[plotname]).enter().append("svg:circle")'
                '.attr("cx", function(d, index) { return (x(d.x) + 5 * (index % 3 -1));})'
                '.attr("cy", function(d) { return height - y(d.y);})'
                '.attr("r", function(d) {return d.rad})'
                '.attr("class", function(d) {return d.dataclass;})'
                '.attr("text", function(d) {return d.name;})'
                '.on("mouseover", highlight_point)'
                '.on("mouseout", dehighlight_point);'
                    )
                    
