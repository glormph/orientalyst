import os
from django.core import serializers
from django.core.management.base import BaseCommand
from accounts.models import Person, Si
from graphs.models import Event, EventRace, Classrace, PersonRun, Result
from graphs.models import Split


JSONserializer = serializers.get_serializer('json')
serializer = JSONserializer()
dumpdir = '../dump/stage'
if not os.path.exists(dumpdir):
    os.makedirs(dumpdir)


def run_dump(queryset, outdir, outfile):
    with open(os.path.join(outdir, outfile), 'w') as fp:
        serializer.serialize(queryset, stream=fp, indent=2)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # get persons
        pk_persons = [121, 114]  # Jorrit, Mattias
        test_persons = Person.objects.filter(pk__in=pk_persons)

        # dump accounts
        run_dump(test_persons, dumpdir, 'accounts.persons.json')
        run_dump(Si.objects.filter(person__in=test_persons), dumpdir,
                 'account.si.json')

        # prepare graph data
        person_runs = PersonRun.objects.filter(person__in=test_persons)
        classraces = Classrace.objects.filter(personrun__in=person_runs)
        eventraces = EventRace.objects.filter(classrace__in=classraces)
        events = Event.objects.filter(eventrace__in=eventraces)
        results = Result.objects.filter(classrace__in=classraces)
        splits = Split.objects.filter(result__in=results)

        # dump graph data
        for qset, outfn in zip([person_runs, classraces, eventraces, events,
                                results, splits],
                               ['graphs.{0}.json'.format(x) for x in
                                ['personrun', 'classrace', 'eventrace',
                                 'event', 'result', 'split']]):
            run_dump(qset, dumpdir, outfn)
