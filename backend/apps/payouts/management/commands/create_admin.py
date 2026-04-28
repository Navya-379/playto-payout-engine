from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        User = get_user_model()

        # delete any wrong admin
        User.objects.filter(username="admn").delete()

        # create fresh admin
        User.objects.create_superuser(
            username="name",
            email="someemail",
            password="mypassword"
        )

        print("Admin reset done")
