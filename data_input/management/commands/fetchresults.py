from django.core.management.base import BaseCommand, CommandError
from data_input import dbupdate, data
from optparse import make_option


class Command(BaseCommand):
    args = ''
    help = 'Downloads new data from eventor, updates database with it'
    option_list = BaseCommand.option_list +  
        (make_option('--competitor', '-c', type='int', default=None, dest='competitor')) +
        (make_option('--event', '-e', type='int', default=None, dest='events',
                        action="append")) +
        (make_option('--period', '-t', type='int', default=None, dest='period'))
        (make_option('--onlyold', '-o', action='store_true', dest='onlyold'))

    def handle(self, *args, **options):
        self.data = data.EventorData()
        
        # FIXME check if options are ok
        # set amount of past days to download results from
        newperiod = None
        oldperiod = 7
        
        # FIXME --competitor should already be in db.

        if None not in [options['events'], options['period']]:
            pass # TODO error here
        if options['onlyold'] is True and \
                [options['events'], options['period'], 
                options['competitor']]!=[None, None, None]:
            pass # TODO error here, onlyold cannot be combined with other options
        
        elif options['period'] is not None:
            oldperiod = options['period'] # newperiod should always be None?
            # better if no new people are fetched when updating w period.
        
        self.stdout.write('Downloading competitors from eventor...')
        self.data.get_competitors(options['competitor'])
        # FIXME check if problems with competitor download
        # if none downloaded, stop here (wrong ev_id, connection problems)
        if options['onlyold'] is False:
            self.stdout.write('Updating person database...')
            old_members, new_members = dbupdate.update_db_persons(data)
            # FIXME new members and personid?
        else:
            self.stdout.write('Only old members, skipping person database update...')
            old_members, new_members = dbupdate.get_old_members(data)[0], []
        
        self.stdout.write('Downloading results data from eventor (may take a'
               ' while)...')
        self.data.get_results(new_members, events=options['events'],
                                    period=newperiod)
        self.data.get_results(old_members, event=options['events'],
                                period=oldperiod)
        dbupdate.password_reset_for_new_users(new_members)
        self.update_db()
    

    def update_db(self):
        self.data.finalize() # modifies classraces into a list instead of convolutd dict
        self.stdout.write('Updating database...')
        self.stdout.write('Events...')
        events = dbupdate.update_events(self.data.events)
        self.stdout.write('Races...')
        dbupdate.update_classraces(events, self.data.classraces)
        self.stdout.write('Results...')
        dbupdate.update_results(self.data.classraces)
        self.stdout.write('Splits...')
        dbupdate.update_splits(self.data.classraces)
        self.stdout.write('PersonRuns...')
        dbupdate.update_personruns(self.data)
        self.stdout.write('All done!')

    def handle_person(self, person):
        # get person and update person table
        # call to get results of person
        # parseResults
        # if new member, create password
        # finalize
        # update all things

    def handle_event(self, event):
        # get all people as usual
        # call eventor getResults, make it only get event
        # finalize
        # update all

    def handle_period(self, event):
        # call eventor api for a period only
        # update all things
