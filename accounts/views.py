# vim: set fileencoding=utf-8 :
from urlparse import urljoin
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.http import HttpResponseRedirect
from django.utils.http import base36_to_int
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import get_current_site
from models import Person, AccountActivationTimestamp
from graphs.views import home
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
            import sys
            token = default_token_generator.make_token(user)
            link = '/'.join(['http:/', current_site.domain, 'accounts/activate',
            token])
            accounts.send_new_account_mail(user, link)
            
            # create a urllogin with timestamp for finer control of time
            ts_db = AccountActivationTimestamp(user=user)
            ts_db.save()
            # upon clicking the link, we make the person account status 'new'
            
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
        post_reset_redirect = reverse('django.contrib.auth.views.password_reset_complete')
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(pk=uid_int)
    except (ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and token_generator.check_token(user, token):
        return HttpResponseRedirect(post_reset_redirect)
    else:
        return HttpResponseRedirect(home)
    
