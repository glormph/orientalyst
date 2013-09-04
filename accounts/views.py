from graphs.models import Person
from accounts import accounts

def signup(request):
    # MAY BELONG IN ANOTHER MODULE THEN GRAPHS
    """Signs up new users"""
    if request.method == 'POST':
        mail = request.POST['email']
        usercheck = accounts.UserChecks(request.user)
        if not usercheck.user_email_exists(mail):
            msg = 'Your email address could not be found on eventor. Please '
            'enter correct mail addresss'
            return signup_error(msg)
        elif usercheck.account_exists(mail):
            msg = 'Your email address is already coupled to an account. '
            'Please try to login, or click the forgot my password link.'
        else:
            username = request.POST['username']
            password = request.POST['password']
            errmsg = usercheck.check_account_details(username, password)
            if errmsg.values() != [None, None]:
                return signup_error(errmsg)
            
            # create useraccount and send mail
            user = accounts.create_user_account(mail, password, person, username)
            accounts.send_new_account_mail(user)
            # upon clicking the link, we make the person account status 'new'
            
            # return a mail sent template
            return render() # FIXME
    else:
        return render(request, 'registration/signup.html')


def signup_error(msg):
    return render(request, 'registration/signup.html', {'error': msg})
