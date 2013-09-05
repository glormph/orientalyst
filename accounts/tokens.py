from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import base36_to_int
from django.utils.crypto import constant_time_compare
from django.conf import settings
from datetime import datetime

class AccountActivateTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism. Subclassed to get finer control over timestamp, which
    works with days in the original.
    """
    def make_token(self, user):
        """
        Returns a token that can be used once to do a password reset
        for the given user.
        """
        return self._make_token_with_timestamp(user, self._num_seconds(self._today()))
    
    def check_token(self, user, token):
        """
        Check that a password reset token is correct for a given user.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(user, ts), token):
            return False

        # Check the timestamp is within limit
        if (self._num_seconds(self._today()) - ts) > \
                    settings.PASSWORD_RESET_TIMEOUT_SECONDS:
            return False
        return True
    
    def _num_seconds(self, dt):
        return (dt - datetime(2001, 1, 1)).seconds

    def _today(self):
        # Used for mocking in tests
        return datetime.now()

default_token_generator = AccountActivateTokenGenerator()
