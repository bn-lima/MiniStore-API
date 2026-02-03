from django.core.validators import RegexValidator


NUMERIC_VALIDATOR = RegexValidator(r'^\d{11}$', 'Enter exactly 11 numbers')

