import logging

from utils import get_storage_info, get_uptime, start_cpu_memory_collection, start_bad_frames_collection

# Logger inicializálása
logger = logging.getLogger(__name__)


def run_selected_test(test_name: str, ip_address: str) -> None:
    """
    Futtatja a kiválasztott tesztet.

    Args:
        test_name (str): A kiválasztott teszt neve.
        ip_address (str): Az eszköz IP címe.
    """
    test_functions = {
        'storage_usage': get_storage_info,
        'cpu_memory_usage': start_cpu_memory_collection,  # CPU és Memória gyűjtése folyamatosan
        'uptime': get_uptime,
        'bad_frames': start_bad_frames_collection,  # Hibás frame folyamatos futtatása
        'all_tests': run_all_tests
    }

    if test_name in test_functions:
        logger.info(f'Teszt futtatása: {test_name}, eszköz: {ip_address}')
        try:
            test_functions[test_name](ip_address)  # Az adott teszt függvényének meghívása
        except Exception as e:
            logger.error(f'Hiba a teszt futtatása közben: {e}', exc_info=True)
    else:
        logger.warning(f'Ismeretlen teszt: {test_name}')


def run_all_tests(ip_address: str) -> None:
    """
    Futtatja az összes tesztet egyszerre:
        - Tárhelyhasználat
        - CPU és Memóriainfó (folyamatosan)
        - Rendszer futási ideje
        - Hibás frame-k száma (folyamatosan)

    Args:
        ip_address (str): Az eszköz IP címe.
    """
    get_storage_info(ip_address)
    start_cpu_memory_collection(ip_address)
    get_uptime(ip_address)
    start_bad_frames_collection(ip_address)
