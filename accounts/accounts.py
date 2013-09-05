# vim: set fileencoding=utf-8 :

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.contrib.auth.models import User
from models import Person, Si
from graphs.models import PersonRun

class UserChecks(object):
    def __init__(self, user):
        self.user = user
        if user.is_authenticated():
            self.fullname = '{0} {1}'.format(
                user.first_name.encode('utf-8'),
                user.last_name.encode('utf-8'))
            self.alias = user.username
            self.person = Person.objects.get(user=self.user.id)
            self.sis = Si.objects.filter(person=self.person)
    
    def get_person_by_email(self, email):
        try:
            return Person.objects.get(email=email)
        except ObjectDoesNotExist:
            return False
    
    def account_exists(self, email):
        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            return False
        else:
            return True

    def check_account_details(self, username, password):
        errmsg = {'password': None, 'username': None}
        # FIXME check if username is ok with regex, check if password ok
        if len(password) < 8:
            errmsg['password'] = """Ditt password är för kort. Använd minst 8
                                tecken"""
        # check password has no forbidden chars??
        # check username exists
        # check username has right chars
        return errmsg    

    def is_loggedin(self):
        return self.user.is_authenticated()

    def has_race(self, raceid):
        races = PersonRun.objects.all().filter(classrace_id=raceid,
        person_id=self.get_competitorID() )
        if len(races) > 0 and int(raceid) in [x.classrace_id for x in races]:
            return True

    def is_uk(self):
        pass
    
    def get_sportident(self):
        return [x.si for x in self.sis]

    def get_eventorID(self):
        return self.person.eventor_id

    def get_competitorID(self):
        return self.person.id


def create_user_account(email, password, person, username=None):
    if username is None:
        # username, generate one
        username = person.firstname
        samefirstname = User.objects.all().filter(first_name=username)
        nr = len(samefirstname)
        if nr > 0:
            username += str(nr)
    username = username.lower()
    
    # generate random password
    #chars = string.ascii_letters + string.digits
    #random.seed = (os.urandom(1024))
    #password = ''.join(random.choice(chars) for i in range(12))
        
    # now create user and save
    user = User.objects.create_user(username, email, password)
    user.first_name = person.firstname
    user.last_name = person.lastname
    user.save()
    return user    

def send_new_account_mail(user, link):
    subject = 'Välkommen till orientalyst!'
    msg = """Du har nu anmält dig till orientalyst. För att vi ska dubbelkolla
    att det stämmer, behöver du klicka på nedanstående länken för att aktivera
    ditt konto. Länken är endast giltig i 15 minuter.

    {0}
    
    Inte en aning var detta mail kom ifrån? Då kan någon av misstag ha använt
    ditt mailaddress för att registrera sig, och du kan lugnt ignorera detta
    mail.
    """.format(link)
    send_mail(subject, msg, 'boekeltjuh@hotmail.com', [user.email], fail_silently=False)
    

#    for person in persons:
#        form = PasswordResetForm({'email': person.email}) 
#        if form.is_valid():
#            form.save(from_email=constants.FROM_EMAIL)
#
