import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _pass

class ComplexityValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _pass("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _pass("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _pass("Password must contain at least one number."),
                code='password_no_number',
            )

    def get_help_text(self):
        return _pass(
            "Your password must contain at least one uppercase letter, one lowercase letter, and one number."
        )
