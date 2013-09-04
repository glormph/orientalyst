# vim: set fileencoding=utf-8 :
from models import Person
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
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
            accounts.send_new_account_mail(user)
            # upon clicking the link, we make the person account status 'new'
            
            # return a mail sent template
            return render(request, '') # FIXME
    else:
        return render(request, 'registration/signup.html')


def signup_error(request, msg):
    return render(request, 'registration/signup.html', {'errors': msg})
