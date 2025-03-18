import time
import logging
import threading

from flask import Flask, current_app

from utils import run_adb_command, get_device_info, is_valid_ip, cpu_memory_usage
from database import save_record
from models import LaunchTime

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
    """
    if test_name == 'cpu_memory_usage':
        start_metric_collection(ip_address)  # Csak az adatgyűjtést indítjuk el, NEM futtatjuk azonnal a cpu_memory_usage-et!
    else:
        test_functions = {
            'launch_time': launch_time,
        }
        if test_name in test_functions:
            logger.info(f"Tesz futtatása: {test_name}, eszköz: {ip_address}")
            try:
                test_functions[test_name](ip_address)
            except Exception as e:
                logger.error(f"Hiba történt a teszt futtatása közben: {e}", exc_info=True)


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


def collect_metrics(app: Flask, ip_address: str):
    """
    A metrikák (CPU és memória használat) gyűjtése és mentése adatbázisba.

    Args:
        app (Flask): A Flask alkalmazás példánya.
        ip_address (str): Az eszköz IP címe.
    """
    with app.app_context():  # Biztosítjuk az alkalmazás kontextusát a háttérszálban
        try:
            while True:
                start_time = time.time()
                cpu_memory_usage(ip_address)  # CPU és memória mentése az adatbázisba
                elapsed_time = time.time() - start_time
                time.sleep(max(10 - elapsed_time, 0))  # 10 másodpercenként fusson
        except Exception as e:
            logger.error(f"Hiba történt a metrikák gyűjtése közben: {e}", exc_info=True)


active_threads = {}


def start_metric_collection(ip_address: str):
    """
    Új szálon indítja az adatgyűjtést egy adott IP-címmel rendelkező eszközhöz.
    """
    if ip_address in active_threads and active_threads[ip_address].is_alive():
        logger.info(f"Az adatgyűjtés már folyamatban van ezen az eszközön: {ip_address}")
        return

    app = current_app._get_current_object()  # Flask alkalmazás példányának lekérése
    metric_thread = threading.Thread(target=collect_metrics, args=(app, ip_address), daemon=True)
    metric_thread.start()
    active_threads[ip_address] = metric_thread
    logger.info(f"Adatgyűjtés elindítva az eszközön: {ip_address}")
