import re

from django.core.exceptions import ValidationError


def validate_username(username):
    """Проверяет, соответствует ли имя пользователя допустимому формату."""
    if username == 'me':
        raise ValidationError(
            'Нельзя использовать "me" как имя пользователя.'
        )
    invalid_symbols = re.sub(r'[\w.@+-]+', '', username)
    if invalid_symbols:
        raise ValidationError(
            f'Нельзя использовать символы '
            f'{"".join(set(invalid_symbols))} в имени пользователя.'
        )
    return username
