import time
import logging

from utils import run_adb_command, get_device_info, is_valid_ip
from database import save_record
from models import LaunchTime, CpuUsage, MemoryUsage

# Logger inicializálása
logger = logging.getLogger(__name__)

# ADB parancsokhoz használt állandók
APP_PACKAGE = 'com.google.android.youtube'
APP_ACTIVITY = '.HomeActivity'


def start_app(ip_address: str) -> None:
    """
    Az alkalmazás elindítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    logger.info(f"Az alkalmazás indítása: {APP_PACKAGE}, eszköz: {ip_address}")
    result = run_adb_command(ip_address, ['shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'])
    if result.returncode != 0:
        logger.error(f"Nem sikerült elindítani az alkalmazást, eszköz: {ip_address}. Hiba: {result.stderr}")


def stop_app(ip_address: str) -> None:
    """
    Az alkalmazás leállítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    logger.info(f"Az alkalmazás leállítása: {APP_PACKAGE}, eszköz: {ip_address}")
    result = run_adb_command(ip_address, ['shell', 'am', 'force-stop', APP_PACKAGE])
    if result.returncode != 0:
        logger.error(f"Nem sikerült leállítani az alkalmazást, eszköz {ip_address}. Hiba: {result.stderr}")


def run_selected_test(test_name: str, ip_address: str) -> None:
    """
    Futtatja a kiválasztott tesztet.

    Args:
        test_name (str): Futtatandó teszt neve
        ip_address (str): Az eszköz IP-címe.
    """
    test_functions = {
        'launch_time': launch_time,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage
    }

    if test_name in test_functions:
        logger.info(f"Tesz futtatása: {test_name}, eszköz: {ip_address}")
        try:
            test_functions[test_name](ip_address)
        except Exception as e:
            logger.error(f"Hiba történt a teszt futtatása közben: {e}", exc_info=True)
    else:
        logger.warning(f"Ismeretlen teszt: {test_name}")


def launch_time(ip_address: str) -> None:
    """
    Az alkalmazés indítási idejének mérése és mentése adatbázisba

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        logger.warning(f"Érvénytelen IP cím a teszt futtatása során: {ip_address}")
        return

    logger.info(f"Indítási idő mérése, eszköz: {ip_address}")
    result = run_adb_command(ip_address, ['shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'])

    if not result or result.returncode != 0:
        logger.error(f"Hiba történt az alkalmazás indítása közben, eszköz: {ip_address}. Hiba: {result.stderr}")
        return

    lines = result.stdout.splitlines()
    startup_state = next((line.split()[-1] for line in lines if 'LaunchState' in line), 'Unknown')
    startup_time = next((line.split()[-1] for line in lines if 'TotalTime' in line), '0')

    try:
        device_name, android_version = get_device_info(ip_address)
        save_record(
            LaunchTime,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            application=APP_PACKAGE.split('.')[-1],
            startup_state=startup_state,
            startup_time=startup_time
        )
        logger.info(f"Sikeres indítási idő mérés, eszköz: {ip_address}")
    except Exception as e:
        logger.error(f"Hiba történt az indítási idő mérése közben: {e}", exc_info=True)

    time.sleep(3)
    stop_app(ip_address)


def cpu_usage(ip_address: str) -> None:
    """
    Az alkalmazás CPU használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        logger.warning(f"Érvénytelen IP cím a CPU használat méréséhez: {ip_address}")
        return

    start_app(ip_address)
    time.sleep(20)
    result = run_adb_command(ip_address, ['shell', 'dumpsys', 'cpuinfo'])

    if not result or result.returncode != 0:
        logger.error(f"Nem sikerült lekérni a CPU használatot. Eszköz: {ip_address}. Hiba: {result.stderr}")
        return

    lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
    cpu_usage_value = lines[0].split()[0] if lines else 'N/A'

    try:
        device_name, android_version = get_device_info(ip_address)
        save_record(
            CpuUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            application=APP_PACKAGE.split('.')[-1],
            cpu_usage=cpu_usage_value
        )
        logger.info(f"Sikeres CPU használat mérés: {cpu_usage_value}, eszköz: {ip_address}")
    except Exception as e:
        logger.error(f"Hiba történt a CPU használat mérése közben: {e}", exc_info=True)

    stop_app(ip_address)


def memory_usage(ip_address: str) -> None:
    """
    Az alkalmazás memória használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        logger.warning(f"Érvénytelen IP cím a memóriahasználat méréséhez: {ip_address}")
        return

    start_app(ip_address)
    time.sleep(10)
    result = run_adb_command(ip_address, ['shell', 'dumpsys', 'meminfo'])

    if not result or result.returncode != 0:
        logger.error(f"Nem sikerült lekérni a memóriahasználati adatokat. Eszköz: {ip_address}. Hiba: {result.stderr}")
        return

    lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
    memory_usage_value = lines[0].split()[0] if lines else 'N/A'

    try:
        device_name, android_version = get_device_info(ip_address)
        save_record(
            MemoryUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            application=APP_PACKAGE.split('.')[-1],
            memory_usage=memory_usage_value
        )
        logger.info(f"Sikeres memóriahasználat mérés: {memory_usage_value}, eszköz: {ip_address}")
    except Exception as e:
        logger.error(f"Hiba történt a memóriahasználat mérése közben: {e}", exc_info=True)

    stop_app(ip_address)
