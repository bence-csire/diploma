import logging

from utils import cpu_memory_usage, get_storage_info, get_bad_frames, get_uptime, start_metric_collection

# Logger inicializálása
logger = logging.getLogger(__name__)

# ADB parancsokhoz használt állandók
APP_PACKAGE = 'com.google.android.youtube'
APP_ACTIVITY = '.HomeActivity'


# def start_app(ip_address: str) -> None:
#     """
#     Az alkalmazás elindítása a megadott eszközön.
#
#     Args:
#         ip_address (str): Az eszköz IP-címe.
#     """
#     logger.info(f"Az alkalmazás indítása: {APP_PACKAGE}, eszköz: {ip_address}")
#     result = run_adb_command(ip_address, ['shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'])
#     if result.returncode != 0:
#         logger.error(f"Nem sikerült elindítani az alkalmazást, eszköz: {ip_address}. Hiba: {result.stderr}")


# def stop_app(ip_address: str) -> None:
#     """
#     Az alkalmazás leállítása a megadott eszközön.
#
#     Args:
#         ip_address (str): Az eszköz IP-címe.
#     """
#     logger.info(f"Az alkalmazás leállítása: {APP_PACKAGE}, eszköz: {ip_address}")
#     result = run_adb_command(ip_address, ['shell', 'am', 'force-stop', APP_PACKAGE])
#     if result.returncode != 0:
#         logger.error(f"Nem sikerült leállítani az alkalmazást, eszköz {ip_address}. Hiba: {result.stderr}")


def run_selected_test(test_name: str, ip_address: str) -> None:
    """
    Futtatja a kiválasztott tesztet a megfelelő metrika alapján.

    Args:
        test_name (str): A kiválasztott teszt neve.
        ip_address (str): Az eszköz IP címe.
    """
    test_functions = {
        'storage_usage': get_storage_info,
        'cpu_memory_usage': start_metric_collection,  # CPU és Memória gyűjtése folyamatosan
        'uptime': get_uptime,
        'bad_frames': get_bad_frames,
        'all_tests': run_all_tests
    }

    if test_name in test_functions:
        logger.info(f"Teszt futtatása: {test_name}, eszköz: {ip_address}")
        try:
            test_functions[test_name](ip_address)  # Az adott teszt függvényének meghívása
        except Exception as e:
            logger.error(f"Hiba történt a teszt futtatása közben: {e}", exc_info=True)
    else:
        logger.warning(f"Ismeretlen teszt: {test_name}")


def run_all_tests(ip_address: str):
    """
    Az összes metrika lekérése egyszerre.
    """
    get_storage_info(ip_address)
    cpu_memory_usage(ip_address)
    get_uptime(ip_address)
    get_bad_frames(ip_address)
