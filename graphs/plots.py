import classracedata, races
from graphs.models import Result

class PlotSet(object):
    def __init__(self, classrace, eventor_id):
        self.results = Result.objects.get(classrace=classrace.id,
                person_eventor_id=eventor_id)
        self.raceinfo = races.Race(classrace)

        racedata = classracedata.ClassRaceData(classrace)
        if not racedata.hassplits:
            self.showgraphs = False
            return 
        else:
            self.showgraphs = True
        self.plots = {}
        self.show_eids = eventor_id # for testing, sofia anderssons
                                        #eventorID=2664

        self.plots['splits'] = MultiplePointsPerPersonPlot('splits',
                            racedata.data, self.show_eids, 'splits', 'time')
        self.plots['bomsplits'] = MultiplePointsPerPersonPlot('bommar', 
                racedata.data, self.show_eids, 'mistakes', 'time')
        self.plots['behind'] = MultiplePointsPerPersonPlot('tidskillnad', 
                racedata.data, self.show_eids, 'splitdiffs', 'time')
        self.plots['legbehind'] = MultiplePointsPerPersonPlot('tidskillnad_leg', 
                racedata.data, self.show_eids, 'legdiffs', 'time')
        self.plots['spread'] = SingePointsPerPersonPlot('spread', racedata.data,
                self.show_eids, 'spread', 'result')
        self.plots['bomtotal'] = SingePointsPerPersonPlot('bomtotal', racedata.data,
                self.show_eids, 'totalmistakes', 'result')

class BasePlot(object):
    def base_html(self):
        return """
        <div class="graph" id="%s"><div class="graphtitle">%s</div></div>
<script>
var width = 350;
var height = 200;
var padding = 50;
var plotname = "%s";
var svg = d3.select("#%s").append("svg:svg").attr("width", 350).attr("height",
200);
var highlight_eid = "%s";
""" % (self.name, self.name, self.name,self.name, self.highlight)
    
    def render_data(self):
        return """data[plotname] = [ %s
        ];
    var xmax = d3.max(data[plotname], function(datum) {return datum.x;});
    var ymax = d3.max(data[plotname], function(datum) {return datum.y;});
    var x = d3.scale.linear().domain([0, xmax]).range([padding, width-padding]);
    var y = d3.scale.linear().domain([0, ymax]).range([padding, height-padding]);
        """ % ',\n'.join(self.points)
    
    def render_points(self):
        return """
// points
svg.selectAll("circle").data(data[plotname]).enter().append("svg:circle")
.attr("cx", function(d) { return x(d.x); })
.attr("cy", function(d) { return height - y(d.y);})
.attr("class", "smallpoints").attr("r", 2)
.attr("id", function(d) { return d.eid+"#"+ "%s"; })


highlight_point(plotname, "2664");
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
var yincrement = Math.round(ymax *100 / 5)/100;

axisGroup.selectAll(".xTicks").data(d3.range(0, xmax,
xincrement)).enter().append("line").attr("y1", height-padding).attr("y2",
height-padding+5).attr("x1", function(datum){return x(datum);}).attr("x2",
function(datum) {return x(datum);}).attr("stroke", "black");

axisGroup.selectAll(".yTicks").data(d3.range(0, ymax,
yincrement)).enter().append("line").attr("x1", padding).attr("x2",
padding-5).attr("y1", function(datum){return y(datum);}).attr("y2",
function(datum) {return y(datum);}).attr("stroke", "black");

// tick nrs

axisGroup.selectAll(".xTickNos").data(d3.range(0, xmax,
xincrement)).enter().append("text").attr("y", height-padding+15).attr("x", function(datum){return x(datum);})
.text(function(datum) {return datum;}).attr("fill", "black").attr("class",
"xTickNos").attr("text-anchor", "middle");

axisGroup.selectAll(".yTickNos").data(d3.range(0, ymax,
yincrement)).enter().append("text").attr("x", padding-10).attr("y",
function(datum){return height-y(datum);})
.text(function(datum) {return datum;}).attr("fill", "black").attr("class",
"xTickNos").attr("text-anchor", "end").attr("dy", 3);
// axis labels

"""

    def close_html(self):
        return """
        </script>
        """

    def render_html(self):
        html = [self.base_html()]
        html.append(self.render_data() )
        html.append(self.render_points() )
        html.append(self.render_plot() )
        html.append(self.close_html() )
        return '\n'.join(html)

class SingePointsPerPersonPlot(BasePlot):
    def __init__(self, name, racedata, eid, y, x):
        self.name = name
        self.points = []
        self.highlight = eid
        for pid in racedata:
            self.points.append('{name: "%s", x: %s, y: %s, color: "%s", eid: "%s"}' \
                % (racedata[pid]['name'], racedata[pid][x], racedata[pid][y],
                "grey", str(pid)))
    

class MultiplePointsPerPersonPlot(BasePlot):
    def __init__(self, name, racedata, eid, ydata, ylab, xlab=None):
        self.highlight = eid
        self.name = name
        self.points = []
        points = {}
         
        for pid in racedata:
            for n,spl in enumerate(racedata[pid][ydata]):
                if not n in points:
                    points[n] = []
                points[n].append('{name: "%s", x: %s, y: %s, color: "%s", eid: "%s"}' \
                % (racedata[pid]['name'], n+1, spl, "grey", str(pid)))
        
        xpoints = sorted(points.keys())
        self.points = [x for n in xpoints for x in points[n]]


    def render_points(self):
        return """

    // points
    svg.selectAll("circle").data(data[plotname]).enter().append("svg:circle")
    .attr("cx", function(datum, index) {
    return (x(datum.x) + 5 * (index % 3 -1));
    })
    .attr("cy", function(datum) { return height - y(datum.y);})
    .attr("r", 2)
    .attr("class", "smallpoints");

highlight_point(plotname, "2664");
    """
