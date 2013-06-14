from django.http import HttpResponse
from graphs.models import PersonRun, Classrace, Result, Split, Person, UrlLogin
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.http import Http404
from django.contrib.auth.views import password_reset
from graphs import plots, userchecker, races

def check_user_logged_in(request):
    user = userchecker.User(request.user)
    if not user.is_loggedin():
        return False
    else:
        return True

def home(request):
    """Just show list of classraces -- how many?- and welcome message/news. 
    Showing all races may be too much, but at least give an option to show more."""
    # get logged in user
    user = userchecker.User(request.user)
    racelist = races.RaceList(user)

    if not user.is_loggedin():
        latestraces = False
    else:
        latestraces = racelist.get_latest_races(10)
        
    return render(request, 'graphs/home.html', {'user': user, 'racelist':
    latestraces})

def about(request): 
    user = userchecker.User(request.user)

    return render(request, 'graphs/about.html', {'user': user})

def my_profile(request, change_psw=False, first_time=False):
    if not check_user_logged_in(request):
        return home(request)
    if request.method == 'POST':
        # for password changes, etc
        if request.POST['newpass'] == request.POST['repeatnewpass']:
            pass
            # change pass in db
            # login user
            # redirect to profile, display success message
        else:
            return render(request, 'graphs/profile.html', {'psw': True,
                'pswerror':'Passworden matchade inte.'
                })
            # redirect to profile, 
    elif request.method == 'GET':
        user = userchecker.User(request.user)
        if not user.is_loggedin() and not change_psw:
            raise Http404 # FIXME display error and redirect home page instead
        return render(request, 'graphs/profile.html', {'psw': change_psw,
                        'firsttime': first_time, 'user': user})



def forgot_password(request):
    # get email or login from post data
    password_reset(request)

def urllogin(request, random_id):
    """Also used when mailing users their account"""
    # lookup random id in random db
    anonuser = userchecker.AnonymousUser()
    user = anonuser.get_user_from_urllogin(random_id)
    if user:
        request.user = user
        return my_profile(request, change_psw=True, first_time=user.firsttime)
    else:
        raise Http404

def userraces(request):
    if not check_user_logged_in(request):
        return home(request)
    # get all user races
    user = userchecker.User(request.user)
    racelist = races.RaceList(user)
    # display them in template with nice formatting and date
    return render(request, 'graphs/userraces.html', {'racelist': racelist, 'user': user})


def race(request, race_id):
    """"Show results for a single race"""
    if not check_user_logged_in(request):
        return home(request)
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

        # get picked graphs, put results in there, or background parse all possible
        # graphs and let user pick, just show some prioritized in the meantime
        plotset = plots.PlotSet(cr, user.get_eventorID() )
    
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
    return render(request, 'graphs/plots.html', {'plots' : plotset,
            'racelist': latestraces, 'user': user})


def multirace(request, race_ids):
    """Show results for multiple races"""
    if not check_user_logged_in(request):
        return home(request)
    # check first if user has run all races
    user = 1
    
    # get results
    race_ids = race_ids.split('/')

    # 
    return HttpResponse('Multiple races {0}'.format('<br>'.join(race_ids)))


def period(request, fromdate, todate):
    """Show results of races over a period of time."""
    if not check_user_logged_in(request):
        return home(request)
    return HttpResponse('Analyze results over time {0} - {1}'.format(fromdate,
    todate))

