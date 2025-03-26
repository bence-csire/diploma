import logging
import subprocess

from flask import flash

from validation import is_valid_ip

# Logger inicializálása
logger = logging.getLogger(__name__)


# ADB parancsokat kezelő függvények
def run_adb_command(ip_address: str, command: list[str]) -> subprocess.CompletedProcess:
    """
    Végrehajt egy ADB parancsot a megadott IP-címmel rendelkező eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
        command (list[str]): Egy lista, amely tartalmazza az ADB parancsot és annak argumentumait.

    Returns:
        subprocess.CompletedProcess: Az ADB parancs végrehajtásának eredménye,
        amely tartalmazza a standard kimenetet (stdout) és a hibakimenetet (stderr).
        None: Ha az IP-cím érvénytelen.

    Errors:
        - Ha az IP-cím érvénytelen, egy hibaüzenet jelenik meg a felhasználói felületen (flash üzenet).
    """
    if not is_valid_ip(ip_address):
        flash('Érvénytelen IP cím.', 'Hiba')
        logger.error(f'Érvénytelen IP cím: {ip_address}, ADB parancs futtatása sikertelen')
        return subprocess.CompletedProcess(args=['adb'], returncode=1)  # Dummy return, hogy a type egyforma maradjon

    logger.info(f'ADB parancs futtatása: {command} az eszközön {ip_address}')
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
        logger.error(f'Eszköz információ lekérése sikertelen: Érvénytelen IP cím - {ip_address}')
        raise ValueError('Érvénytelen IP cím.')
    try:
        device_name = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.product.name'],
            encoding='utf-8').strip()
        android_version = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.build.version.release'],
            encoding='utf-8').strip()
        logger.info(f'Eszköz neve: {device_name}, Android verzió: {android_version}, IP cím {ip_address}.')
        return device_name, android_version
    except subprocess.CalledProcessError as e:
        logger.error(f'Hiba az eszköz információ lekérésekor: {e}', exc_info=True)
        raise RuntimeError(f'Hiba: {e}')


def connect_device(ip_address: str) -> tuple[bool, str]:
    """
    Eszközhöz való csatlakozás ADB paranccsal.

    Args:
        ip_address (str): Az eszköz IP-címe.

    Returns:
        tuple[bool, str]:
            - bool: `True`, ha a csatlakozás sikeres, `False` egyébként.
            - str: A csatlakozás eredményét leíró üzenet (siker vagy hiba).
    """
    if not is_valid_ip(ip_address):
        logger.error(f'Csatlakozás sikertelen: Érvénytelen IP cím - {ip_address}')
        return False, 'Érvénytelen IP cím.'

    result = run_adb_command(ip_address, ['connect', ip_address])

    if 'connected' in result.stdout.lower():
        logger.info(f'Sikeresen csatlakozott az eszközhöz: {ip_address}')
        return True, f'Csatlakoztatva az eszközhöz {ip_address}.'

    logger.warning(f'Csatlakozás sikertelen az eszközhöz: {ip_address}, válasz: {result.stdout or result.stderr}')
    return False, result.stdout or result.stderr


def disconnect_device(ip_address: str) -> tuple[bool, str]:
    """
    Eszközről való lecsatlakozás ADB paranccsal.

    Args:
        ip_address (str): Az eszköz IP-címe.

    Returns:
        tuple[bool, str]:
            - bool: `True`, ha a lecsatlakozás sikeres, `False` egyébként.
            - str: A lecsatlakozás eredményét leíró üzenet (siker vagy hiba).
    """
    if not is_valid_ip(ip_address):
        logger.error(f'Lecsatlakozás sikertelen: Érvénytelen IP cím - {ip_address}')
        return False, 'Érvénytelen IP cím.'

    result = run_adb_command(ip_address, ['disconnect', ip_address])

    if 'disconnected' in result.stdout.lower():
        logger.info(f'Sikeresen lecsatlakozott az eszközről: {ip_address}')
        return True, f'Lecsatlakoztatva a {ip_address} eszközről.'

    logger.warning(f'Lecsatlakozás sikertelen: {ip_address}, válasz: {result.stdout or result.stderr}')
    return False, result.stdout or result.stderr
