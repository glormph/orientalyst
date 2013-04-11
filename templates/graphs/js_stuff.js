


        var dehighlight_point = function(plotid, eid) {
            // filter eid and remove
            // plot new small
            toremove = filter_eid(plotid, eid);
            dp = get_datapoints_obj(data[plotid], eid);
            points = plotpoint(dp, plotid, "smallpoints", 2);
            points.attr("onmouseover", "mouseOver(evt)");
            toremove.remove();
        }
        # plot order:
        # axes, small dots, r=2
        # delete user points
        # highlight points (top layer, class-styled) (plotuserfn)
        # on mouseover:
            # dehighlight:
                # delete current highlighted points (filter on class or eid)
                # replot as small points
            # highlight:
                # delete tobe highglihged small points(filter eid)
                # plot highlightpoints
        # on mouseout:
            # dehighlight:
                # delete current highlighted points
                # replot them as small points
                # highlight user points
        mouseOver = function(evt) {
            id = evt.target.getAttribute("id");
            id = id.split('#');
            highlight_point(id[1], id[0]);
            }
        
        mouseOut = function(evt) {
            id = evt.target.getAttribute("id");
            id = id.split('#');
            dehighlight_point(id[1], id[0]);
            }

