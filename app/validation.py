import logging
import ipaddress

from flask_wtf import FlaskForm
from wtforms.validators import ValidationError
from wtforms.fields.core import Field

# Logger inicializálása
logger = logging.getLogger(__name__)


def is_valid_ip(ip: str) -> bool:
    """
    Ellenőrzi, hogy a megadott IP cím létező IPv4 vagy IPv6 cím.

    Args:
        ip (str): Az ellenőrzendő IP cím.

    Returns:
        bool: True ha helyes, különben False.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        logger.warning(f'Érvénytelen IP cím: {ip}')
        return False


# Flask IP validáció
def validate_ip(form: FlaskForm, field: Field) -> None:
    """
    Egyedi IP cím validáló függvény, Flask formmal.


    Args:
        form (FlaskForm): Flask form ami az ellenőrizendő mezőt tartalmazza
        field (Field): Ellenőrizendő mező.

    Raises:
        ValidationError: Bemenet nem érvényes IP cím.
    """
    if not is_valid_ip(field.data):
        logger.error(f'Form validációs hiba: Érvénytelen IP cím - {field.data}')
        raise ValidationError('Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.')
