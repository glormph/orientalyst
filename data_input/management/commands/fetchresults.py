import logging
from django.core.management.base import BaseCommand, CommandError
from data_input import dbupdate, data
from optparse import make_option

logger = logging.getLogger('data_input')

class Command(BaseCommand):
    args = ''
    help = 'Downloads new data from eventor, updates database with it'
    option_list = BaseCommand.option_list + (
        make_option('--competitor', '-c', type='int', 
            default=None, dest='competitor'),) + (
        make_option('--event', '-e', type='int', default=None, dest='events',
                        action="append"), ) + (
        make_option('--period', '-t', type='int', default=None,
                        dest='period'),) + (
        make_option('--onlyold', '-o', action='store_true', default=False, dest='onlyold'),)

    def handle(self, *args, **options):
        self.eventordata = data.EventorData()
        
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
        if options['competitor'] is not None:
            options['competitor'] = str(options['competitor'])
        self.eventordata.get_competitors(options['competitor'])
        # FIXME check if problems with competitor download
        # if none downloaded, stop here (wrong ev_id, connection problems)
        if options['onlyold'] is False:
            logger.info('Updating person database...')
            old_members, new_members = dbupdate.update_db_persons(self.eventordata)
            # FIXME new members and personid?
        else:
            logger.info('Only old members, skipping person database update...')
            old_members, new_members = dbupdate.get_old_members(self.eventordata)[0], []
        
        if new_members != []:
            self.update_newmember_data([new_members[1]])
        #self.update_all_recent_member_data(new_members+old_members)

        # why is this below the result fetching?
            # dbupdate.password_reset_for_new_users(new_members)
    
    def update_newmember_data(self, new_members):
        """Gets races for new members, filters out the ones already in db, then
        gets results (splits) for each event not filtered and updates db"""
        logger.info('Downloading results data from eventor for {0} '
        'new members'.format(len(new_members)))
        newmember_races = self.eventordata.get_newmember_races(new_members[:1])
        # do a db query to see which races not in db
        races_not_in_db = dbupdate.get_events_not_in_db(newmember_races)
        self.eventordata.filter_races(races_not_in_db)
        self.eventordata.get_results_of_races()
        self.update_db()        
        self.eventordata.wipe_data()

    def update_all_recent_member_data(self, members):
        self.eventordata.get_recent_races(members)
        self.eventordata.get_results_of_races()
        self.update_db()

    def update_db(self):
        self.eventordata.finalize() # modifies classraces into a list instead of convolutd dict
        self.stdout.write('Updating database...')
        logger.info('Updating {0} events'.format(len(self.eventordata.events)))
        events = dbupdate.update_events(self.eventordata.events)
        self.stdout.write('Eventraces...')
        eventraces = dbupdate.update_eventraces(self.eventordata.eventraces)
        self.stdout.write('Races...')
        dbupdate.update_classraces(eventraces, self.eventordata.classraces)
        self.stdout.write('Results...')
        dbupdate.update_results(self.eventordata.classraces)
        self.stdout.write('Splits...')
        dbupdate.update_splits(self.eventordata.classraces)
        self.stdout.write('PersonRuns...')
        dbupdate.update_personruns(self.eventordata)
        self.stdout.write('All done!')
