from django.core.management.base import BaseCommand, CommandError
from eventor import dbupdate

class DbUpdateCommand(BaseCommand):
    args = ''
    help = 'Downloads new data from eventor, updates database with it'
    
    def handle(self):
        self.stdout.write('Starting downloading from eventor and updating db.')
        dbupdate.update()        
        self.stdout.write('All done!')

