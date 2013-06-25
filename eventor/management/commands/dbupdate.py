from django.core.management.base import BaseCommand, CommandError
from eventor import dbupdate, eventorobjects

class DbUpdateCommand(BaseCommand):
    args = ''
    help = 'Downloads new data from eventor, updates database with it'
    
    def handle(self):
        data = eventorobjects.EventorData()
        self.stdout.write('Downloading competitors from eventor...')
        data.get_people()
        self.stdout.write('Updating person database...')
        old_members, new_members = dbupdate.update_db_persons(data)
        self.stdout.write('Downloading results data from eventor (may take a'
        ' while)...')
        for person in new_members[:1]:
            resultxml = data.getResults(person)
            if resultxml:
                data.parseResults(person, resultxml)
        dbupdate.password_reset_for_new_users(new_members)
        for person in old_members[:1]:
            resultxml = data.getResults(person, days=7)
            if resultxml:
                data.parseResults(person, resultxml)
        data.finalize() # modifies classraces into a list instead of convolutd dict
        self.stdout.write('Updating database...')
        events = dbupdate.update_events(data.events)
        dbupdate.update_classraces(events, data.classraces)
        dbupdate.update_results(data.classraces)
        dbupdate.update_splits(data.classraces)
        dbupdate.update_personruns(data)

        self.stdout.write('All done!')

