import ipaddress
import subprocess

from flask import flash
from flask_wtf import FlaskForm
from wtforms.validators import ValidationError
from wtforms.fields.core import Field


def is_valid_ip(ip: str) -> bool:
    """
    Ellenőrzi, hogy a megadott IP cím létező IPv4 vagy IPv6 cím.
    Felhasználása általánosan a kódban.

    Args:
        ip (str): Az ellenőrzendő IP cím.

    Returns:
        bool: True ha helyes, különben False.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


# Flask IP validáció
def validate_ip(form: FlaskForm, field: Field) -> None:
    """
    Egyedi IP cím validáló függvény, Flask formmal.
    ValidationError-t ad vissza, ha a bemenet nem egy érvényes IP cím.
    Felhasználása Flask form-nál.

    Args:
        form (FlaskForm): Flask form ami az ellenőrzendő mezőt tartalmazza
        field (Field): Ellenőrzendő mező.
    """
    if not is_valid_ip(field.data):
        raise ValidationError('Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.')


# ADB parancsokat kezelő függvények
def run_adb_command(ip_address: str, command: list[str]) -> subprocess.CompletedProcess:
    """
    Végrehajt egy ADB parancsot a megadott IP-címmel rendelkező eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
        command (list[str]): Egy lista, amely tartalmazza az ADB parancsot és annak argumentumait.

    Returns:
        subprocess.CompletedProcess: Az ADB parancs végrehajtásának eredménye, amely tartalmazza a standard kimenetet (stdout) és a hibakimenetet (stderr).
        None: Ha az IP-cím érvénytelen.

    Errors:
        - Ha az IP-cím érvénytelen, egy hibaüzenet jelenik meg a felhasználói felületen (flash üzenet).
    """
    if not is_valid_ip(ip_address):
        flash('Érvénytelen IP cím.', 'Hiba')
        return subprocess.CompletedProcess(args=['adb'], returncode=1)  # Dummy return, hogy a type egyforma maradjon
    return subprocess.run(['adb', '-s', ip_address] + command, capture_output=True, text=True)


def get_device_info(ip_address: str) -> tuple[str, str]:
    """
    Az eszköz nevének és Android verziójának lekérése.

    Args:
        ip_address (str): Az eszköz IP-címe.

    Returns:
        tuple: Az eszköz neve és Android verziója.

    Raises:
        ValueError: Ha az IP cím érvénytelen.
    """
    if not is_valid_ip(ip_address):
        raise ValueError("Érvénytelen IP cím.")
    try:
        device_name = subprocess.check_output(['adb', '-s', ip_address, 'shell', 'getprop', 'ro.product.marketname'], encoding='utf-8').strip()
        android_version = subprocess.check_output(['adb', '-s', ip_address, 'shell', 'getprop', 'ro.build.version.release'], encoding='utf-8').strip()
        return device_name, android_version
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Hiba történt: {e}")


def connect_device(ip_address: str) -> tuple[bool, str]:
    """Csatlakozás az eszközhöz ADB-n keresztül."""
    result = run_adb_command(ip_address, ['connect', ip_address])
    if 'connected' in result.stdout.lower():
        return True, f'Csatlakoztatva az eszközhöz {ip_address}.'
    return False, result.stdout or result.stderr
