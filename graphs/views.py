from django.http import HttpResponse
from graphs.models import PersonRun, Classrace, Result, Split, Person
from django.shortcuts import get_object_or_404, get_list_or_404, render
from graphs import plots, userchecker, races

def home(request):
    """Just show list of classraces -- how many?- and welcome message/news. 
    Showing all races may be too much, but at least give an option to show more."""
    # get logged in user
    user = 'x'

    crlist = get_list_or_404(PersonRun, person=1) #FIXME get person.id fr auth 
    output = '<br>'.join([x.classrace.name for x in crlist])
    
    return HttpResponse(output)

def userraces(request):
    # get all user races
    user = userchecker.User(request.user)
    racelist = races.RaceList(user)
    
    # display them in template with nice formatting and date
    return render(request, 'graphs/userraces.html', {'racelist': racelist, 'user': user})


def race(request, race_id):
    """"Show results for a single race"""
    # first check if user has run this race or if race exists
    user = userchecker.User(request.user)
    racelist = races.RaceList(user)

    if not user.is_loggedin():
        plotset = False
        latestraces = False
    elif user.has_race(race_id):
        # get results
        # FIXME which fields need to go to graphing? times, pos, names, clubs?
        cr = Classrace.objects.get(pk=race_id)
        results = Result.objects.get(classrace=cr.id,
        person_eventor_id=user.get_eventorID() )

        # get picked graphs, put results in there, or background parse all possible
        # graphs and let user pick, just show some prioritized in the meantime
        plotset = plots.PlotSet(cr, [user.get_eventorID()] )
    
        # best would be to only pass results from here once -> let graph module do
        # magic. This would go bad with the one graph - one class thingie though

        # which graphs?

        # get last 10 races of a competitor
        latestraces = racelist.get_latest_races(10)
    else:
        plotset = False
        # FIXME next stuff is also in other if clause. abstract it into
        # competitor or something.
        latestraces = racelist.get_latest_races(10)

    # graphs to template
    return render(request, 'graphs/index.html', {'plots' : plotset, 'result':
        results, 'racelist': latestraces, 'user': user})


def multirace(request, race_ids):
    """Show results for multiple races"""
    # check first if user has run all races
    user = 1
    
    # get results
    race_ids = race_ids.split('/')

    # 
    return HttpResponse('Multiple races {0}'.format('<br>'.join(race_ids)))


def period(request, fromdate, todate):
    """Show results of races over a period of time."""
    return HttpResponse('Analyze results over time {0} - {1}'.format(fromdate,
    todate))

