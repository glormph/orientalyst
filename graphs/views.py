from django.http import HttpResponse
from graphs.models import Classrace
from followers.models import Following
from comments.models import Comment
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.views import password_reset
from graphs import plots, races
from accounts import accounts
from comments.models import CommentForm


def check_user_logged_in(request):
    user = accounts.UserChecks(request.user)
    if not user.is_loggedin():
        return False
    else:
        return True


def front_page(request):
    return render(request, 'graphs/home.html', {'user': user, 'racelist':
                    latestraces})

def home(request, message=None):
    """Just show list of classraces -- how many?- and welcome message/news.
    Showing all races may be too much, but at least give an option to show more."""
    # get logged in user
    user = accounts.UserChecks(request.user)
    racelist = races.RaceList(user)
    latestraces = racelist.get_latest_races(10)
    return render(request, 'graphs/home.html', {'user': user, 'racelist':
                    latestraces, 'message': message})


def about(request): 
    user = accounts.UserChecks(request.user)
    racelist = races.RaceList(user)
    latestraces = racelist.get_latest_races(10)
    return render(request, 'graphs/about.html', {'user': user, 
                            'racelist': latestraces})


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
        user = accounts.UserChecks(request.user)
        racelist = races.RaceList(user)
        latestraces = racelist.get_latest_races(10)
        if not user.is_loggedin() and not change_psw:
            raise Http404 # FIXME display error and redirect home page instead
        return render(request, 'graphs/profile.html', {'psw': change_psw,
                      'racelist': latestraces, 'firsttime': first_time, 'user': user})



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
    user = accounts.UserChecks(request.user)
    racelist = races.RaceList(user)
    # display them in template with nice formatting and date
    return render(request, 'graphs/userraces.html', {'racelist': racelist, 'user': user})


def race(request, race_id):
    """"Show plots, info and comments for a single race"""
    if not check_user_logged_in(request):
        return home(request)
    # first check if user has run this race or if race exists
    user = accounts.UserChecks(request.user)
    racelist = races.RaceList(user)  # deprecate when we have feed?
    cr = get_object_or_404(Classrace, pk=race_id)

    # Post comment if there has been one
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            newcomment = form.save(commit=False)
            newcomment.author = user.person
            newcomment.classrace = cr
            newcomment.save()
    followed_eventor_ids = [
        x.followed.eventor_id for x in
        Following.objects.filter(follower=user.person)]
    plotset = plots.PlotSet(cr, user.get_eventorID(), followed_eventor_ids)
    raceresulttext = races.RaceData(cr, user.get_eventorID())  # FIXME ok?
    comments = Comment.objects.filter(classrace=cr).order_by('created')
    latestraces = racelist.get_latest_races(10)

    # graphs to template
    return render(request, 'graphs/plots.html', {
        'plots': plotset,
        'racedata': raceresulttext,
        'comments': comments,
        'racelist': latestraces,
        'user_is_logged_in': user.is_loggedin(),
        'user': user})


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

