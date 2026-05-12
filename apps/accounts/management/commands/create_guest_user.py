# =============================================================================
# Management command: create a read-only "guest" user for local development.
# =============================================================================
# Usage:
#     # Create the default guest (guest / guest123)
#     poetry run python manage.py create_guest_user
#
#     # Custom credentials
#     poetry run python manage.py create_guest_user \
#         --username guest2 --password secret --email guest2@prism.dev
#
#     # Batch-create several guests (guest1, guest2, guest3)
#     poetry run python manage.py create_guest_user --count 3
#
# The command is idempotent: re-running it just resets the password and
# re-adds the user to the "guest" Group.
# =============================================================================

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.permissions import GUEST_GROUP_NAME


class Command(BaseCommand):
    # Create (or reset) one or more read-only guest users for local development.
    help = "Create (or reset) one or more read-only guest users for local development."

    def add_arguments(self, parser):
        # Wire up the CLI flags this command accepts.
        parser.add_argument(
            '--username',
            default='guest',
            help='Base username (default: "guest"). With --count>1 becomes guest1, guest2, ...',
        )
        parser.add_argument(
            '--password',
            default='guest123',
            help='Password (default: "guest123"). Used for all accounts when --count>1.',
        )
        parser.add_argument(
            '--email',
            default=None,
            help='Email (default: <username>@prism.dev).',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='How many guest users to create (default: 1).',
        )

    def handle(self, *args, **options):
        # Ensure the local "guest" Group exists, then create or reset
        # the requested user(s). Each account is forced read-only by
        # clearing is_staff / is_superuser and adding it to the Group
        # so the same permission machinery used in production (via
        # OIDC claims) also catches dev-only accounts.
        User = get_user_model()

        base_username = options['username']
        password = options['password']
        count = options['count']
        base_email = options['email']

        if count < 1:
            raise CommandError('--count must be >= 1')

        # Ensure the guest Group exists once, up front.
        guest_group, group_created = Group.objects.get_or_create(name=GUEST_GROUP_NAME)
        if group_created:
            self.stdout.write(self.style.SUCCESS(f'Created Group "{GUEST_GROUP_NAME}".'))

        for i in range(count):
            # When creating only one guest, keep the username as given;
            # when batching, suffix a number so usernames don't collide.
            if count == 1:
                username = base_username
            else:
                username = f'{base_username}{i + 1}'

            email = base_email or f'{username}@prism.dev'

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': 'Guest',
                    'last_name': f'User {i + 1}' if count > 1 else 'User',
                },
            )
            # Always reset: guests are a dev convenience, not a secret.
            user.email = email
            user.set_password(password)
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            user.save()
            user.groups.add(guest_group)

            action = 'Created' if created else 'Reset'
            self.stdout.write(self.style.SUCCESS(
                f'{action} guest user: {username} / {password}  ({email})'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.NOTICE(
            'Guests have read-only access. They can view every page but '
            'cannot save schemas, initialize the DB, or add/delete entries.'
        ))
