import logging
from django.core.management.base import BaseCommand, CommandError
from data_input import dbupdate, data
from optparse import make_option

logger = logging.getLogger('data_input')

class Command(BaseCommand):
    args = ''
    help = 'Downloads new data from eventor, updates database with it'
    option_list = BaseCommand.option_list + (
        make_option('--persons', '-p', action='store_true', default=False,
        dest='persons'),) + (
        make_option('--newcompetitor', '-n', type='int', 
            default=None, dest='newcompetitor'),) + (
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
        
        if None not in [options['events'], options['period']]:
            pass # TODO error here
        if options['onlyold'] is True and \
                [options['events'], options['period'], 
                options['competitor']]!=[None, None, None]:
            pass # TODO error here, onlyold cannot be combined with other options
        
        elif options['period'] is not None:
            oldperiod = options['period'] # newperiod should always be None?
            # better if no new people are fetched when updating w period.
        
        if options['persons'] is True:
            self.update_person_db()
        elif options['newcompetitor'] is not None:
            members = dbupdate.get_members([options['newcompetitor']])
            self.get_newmember_data(members)
        else:
            self.update_all_recent_member_data()

        logger.info('Finished updating')
        return
###################################################

        # FIXME check if problems with competitor download
        # if none downloaded, stop here (wrong ev_id, connection problems)
        if options['onlyold'] is False:
            logger.info('Updating person database...')
            # FIXME new members and personid?
                
            # dbupdate.password_reset_for_new_users(new_members)
   ############################## 
    def update_person_db(self):
        logger.info('Downloading competitors from eventor')
        self.eventordata.get_competitors()
        logger.info('Updating db with persons')
        dbupdate.update_db_persons(self.eventordata)
        
    def get_newmember_data(self, members):
        """Gets races for new member, filters out the ones already in db, then
        gets results (splits) for each event not filtered and updates db"""
        clubmembers = self.eventordata.create_clubmembers(members)
        logger.info('Downloading results data from eventor for {0}'
        ' new members'.format(len(members)))
        newmember_races = self.eventordata.get_newmember_races(clubmembers)
        # do a db query to see which races not in db
        races_not_in_db = dbupdate.get_events_not_in_db(newmember_races)
        logger.info('Amount of classraces downloaded: {0}. Amount not yet in '
                    'db: {1}'.format(len(newmember_races), len(races_not_in_db)))
        self.update_db_races()
        self.eventordata.filter_races(races_not_in_db)
        self.eventordata.get_results_of_races()
        self.update_db_results()

    def update_all_recent_member_data(self):
        members = dbupdate.get_all_members_with_accounts()
        clubmembers = self.eventordata.create_clubmembers(members)
        self.eventordata.get_recent_races(clubmembers[:2])
        self.update_db_races()
        self.eventordata.get_results_of_races()
        self.update_db_results()
    
    def update_db_races(self):
        logger.info('Updating {0} events'.format(len(self.eventordata.events)))
        events = dbupdate.update_events(self.eventordata.events)
        logger.info('Updating {0} '
                    'eventraces'.format(len(self.eventordata.eventraces)))
        eventraces = dbupdate.update_eventraces(self.eventordata.eventraces)
        classraces = self.eventordata.get_classraces_as_list()
        logger.info('Updating {0} '
                    'classraces'.format(len(classraces)))
        dbupdate.update_classraces(eventraces, classraces)
        logger.info('Updating {0} '
                'personruns'.format(len(self.eventordata.personruns)))
        dbupdate.update_personruns(classraces, self.eventordata.personruns)

    def update_db_results(self):
        classraces = self.eventordata.get_classraces_as_list()
        classraces = self.eventordata.reformat_split_results(classraces)
        logger.info('Updating results')
        dbupdate.update_results(classraces)
        logger.info('Updating splits')
        dbupdate.update_splits(classraces)
