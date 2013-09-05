# vim: set fileencoding=utf-8 :
from urlparse import urljoin
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import int_to_base36, base36_to_int
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import get_current_site
from models import Person
from graphs.views import home
from tokens import default_token_generator
import accounts

def signup(request):
    # MAY BELONG IN ANOTHER MODULE THEN GRAPHS
    """Signs up new users"""
    if request.method == 'POST':
        mail = request.POST['email']
        usercheck = accounts.UserChecks(request.user)
        person = usercheck.get_person_by_email(mail)
        if person is False:
            msg = """Ditt email kunde inte hittas på eventor. Var god och
            använd email addressen som du använder på idrottonline."""
            return signup_error(request, msg)
        elif usercheck.account_exists(mail):
            msg = """Ditt email har redan ett konto. Var god och försök att
            logga in istället."""
            return signup_error(request, msg)
        else:
            username = request.POST['username']
            password = request.POST['password']
            errmsg = usercheck.check_account_details(username, password)
            if errmsg.values() != [None, None]:
                if errmsg['password'] is not None:
                    msg = errmsg['password']
                if errmsg['username'] is not None:
                    msg = errmsg['username']
                return signup_error(request, msg)
            
            # create useraccount and send mail
            user = accounts.create_user_account(mail, password, person, username)
            current_site = get_current_site(request)
            uidb36 = int_to_base36(user.pk)
            token = default_token_generator.make_token(user)
            link = '/'.join(['http:/', current_site.domain,
            'accounts/activate/{0}-{1}'.format(uidb36,token)])
            accounts.send_new_account_mail(user, link)
            
            # return a mail sent template
            return render(request, 'registration/signup_successful.html')
    else:
        return render(request, 'registration/signup.html')


def signup_error(request, msg):
    return render(request, 'registration/signup.html', {'errors': msg})


@sensitive_post_parameters()
@never_cache
def activate_account(request, uidb36=None, token=None,
                           token_generator=default_token_generator,
                           post_reset_redirect=None,
                           current_app=None, extra_context=None):
    """
    View that checks the hash in an activate account link.
    """
    assert uidb36 is not None and token is not None  # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse(home)
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(pk=uid_int)
    except (ValueError, OverflowError, User.DoesNotExist):
        raise
        user = None
    if user is not None and token_generator.check_token(user, token):
        person = Person.objects.get(email=user.email)
        person.user = user
        person.account_status = 'new'
        person.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return HttpResponseRedirect(post_reset_redirect)
    else:
        # TODO make nice error message page here w 404
        return HttpResponseRedirect(reverse(home))
    
