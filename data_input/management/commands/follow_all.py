"""
Script to let all persons get eachother as Follower
"""

from followers.models import Following
from accounts.models import Person

allfollowers = []
for person_that_follows in Person.objects.all():
    for person_to_follow in Person.objects.all():
        if not person_that_follows == person_to_follow:
            allfollowers.append(Following(followed=person_to_follow,
                                follower=person_that_follows,
                                          ))
Following.objects.bulk_create(allfollowers)
