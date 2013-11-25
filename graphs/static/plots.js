var colors = ['orange', 'purple', 'green', 'brown'];
var colorindex = 0;

var data = new Array();
        d3.selection.prototype.moveToFront = function() {
            return this.each(function(){
                this.parentNode.appendChild(this);
                });
        };

        get_all_ids = function(selection) {
            ids = [];
            selection.each(function(d) { 
              ids.push(d3.select(this).attr("id"));
            });
          return ids
        }
        
        highlight_point = function(d) {
            if (d.dataclass == "friendpoint") {
                tooltip(this, d);
                circleid = d3.select(this).attr("id");
                d3.selectAll("#"+circleid)
                .attr("r", 7)
                .attr("class", "highlightpoint");
            }
        }
        
        click_point = function(d) {
            if (d.dataclass == "friendpoint" && colorindex<4) {
                color = colors[colorindex];
                colorindex += 1;
                circleid = d3.select(this).attr("id");
                circleid = circleid.split("__");
                ev_id = circleid[circleid.length - 1];
                hex_id = circleid[circleid.length - 2];
                plotids = get_all_ids(d3.selectAll("svg"));
                for (i=0; i<plotids.length; i++) {
                  pointid = plotids[i] + "__" + hex_id + "__" + ev_id;
                  d3.selectAll("#"+pointid)
                  .attr("r", 7)
                  .attr("class", "clickedpoint")
                  .attr("fill", color)
                  .on("mouseover", null)
                  .on("mouseout", null)
                  .on("click", null);
                  ;
                  }
                remove_tooltip(this);
                legend(d, color);
                }
            }
        
        declick_point = function() {
            legend_id = d3.select(this.parentNode).attr("id");
            point_id = legend_id.substring(1);
            plotids = get_all_ids(d3.selectAll(".plot"));
            colorindex -= 1;
            for (i=0; i<plotids.length; i++) {
                fullpointid = plotids[i]+"__"+point_id;
                d3.selectAll("#"+fullpointid)
                .attr("class", function(d) {return d.dataclass;})
                .attr("r", function(d) {return d.rad;})
                .on("mouseover", highlight_point)
                .on("mouseout", dehighlight_point) 
                .on("click", click_point)
                ;
            }
            remove_legend(legend_id);
        }

        dehighlight_point = function(d) {
            remove_tooltip(this);
            circleid = d3.select(this).attr("id");
            d3.selectAll("#"+circleid)
            .attr("r", d.rad)
            .attr("class", d.dataclass);
            }
        
        legend = function(d, color) {
            legsvg = d3.select("#rightcolumn")
            .append("svg")
            .attr("id", "_"+d.nhex+"__"+d.eid)
            .attr("height", "30px");
            text = legsvg.append("text").text(d.name)
            .attr("class", "legendtext")
            .attr("x", 30)
            .attr("y", 20);
            bbox = text.node().getBBox();
            legsvg.append("rect")
            .attr("class", "legendbox")
            .attr("x", bbox.x-30)
            .attr("y", bbox.y-10)
            .attr("width", bbox.width + 40)
            .attr("height", bbox.height + 20)
            ;
            legcircle = legsvg.append("circle")
            .attr("class", "clickedpoint")
            .attr("r", 7)
            .attr("cx", 14)
            .attr("cy", 15)
            .attr("fill", color)
            .on("click", declick_point)
            ;
            text.moveToFront();
            legcircle.moveToFront();
            }

        remove_legend = function(legend_id) {
            d3.select("#"+legend_id)
            .data([]).exit().remove();
        }

        tooltip = function(circle, d) {
            tipx = circle.cx.animVal.value;
            tipy = circle.cy.animVal.value - 20;
            textelement = d3.select(circle.parentNode)
            .append("text")
            .text(d.name)
            .attr("text-anchor", "middle")
            .attr("class", "tooltiptext")
            .attr("x", tipx)
            .attr("y", tipy);
            
            bbox = textelement.node().getBBox();
            d3.select(circle.parentNode)
            .append("rect")
            .attr("class", "tooltipbox")
            .attr("x", bbox.x-5)
            .attr("y", bbox.y-5)
            .attr("width", bbox.width+10)
            .attr("height", bbox.height+10);
            
            textelement.moveToFront();
            }


        remove_tooltip = function(circle) {
            d3.selectAll(".tooltiptext")
            .data([]).exit().remove();
            d3.selectAll(".tooltipbox")
            .data([]).exit().remove();
        }
