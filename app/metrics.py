import logging
import threading
import time

from prometheus_client import Gauge
from flask import Flask, current_app

from adb import run_adb_command
from utils import cpu_memory_usage, get_bad_frames


METRIC_INTERVAL_SECONDS = 10    # Metrika lekérdezésének gyakorisága másodpercben

# Logger inicializálása
logger = logging.getLogger(__name__)

# Prometheus metrikák
cpu_user_usage = Gauge('android_cpu_user', 'User CPU usage of Android device in %')
mem_total = Gauge('android_mem_total', 'Total memory of Android device in KB')
mem_usage = Gauge('android_mem_used', 'Memory usage of Android device in KB')
mem_percentage = Gauge('android_mem_usage_percent', 'Memory usage percentage of Android device')
storage_usage = Gauge('android_storage_usage', 'Storage usage of Android device')
storage_percentage = Gauge('android_storage_percentage', 'Storage usage percentage of Android device')
uptime_metric = Gauge('android_uptime', 'Device uptime in seconds')
bad_frames_metric = Gauge('android_bad_frames', 'Number of dropped frames')
cpu_cores = Gauge('android_cpu_cores', 'Number of CPU cores in the Android device')

stop_flags_cpu_memory = {}


def sanitize_numeric_value(value: str) -> float:
    """
    Eltávolítja az utolsó karaktert, ha az nem numerikus (pl. G, M, K, %) és lebegőpontos számmá alakítja.

    Args:
        value (str): Az átalakítandó érték (pl. "1.2G", "500M", "75%")

    Returns:
        float: Az átalakított numerikus érték
    """
    if value[-1] in "GMK%":
        value = value[:-1]  # Levágjuk az utolsó karaktert
    try:
        return float(value)
    except ValueError:
        logger.error(f'Nem sikerült átalakítani numerikus értékké: {value}')
        return 0.0  # Visszaadhatunk egy alapértelmezett értéket


def collect_cpu_memory(app: Flask, ip_address: str) -> None:
    """
    Folyamatosan gyűjti az eszköz CPU és memória használatát és elmenti adatbázisba.

    Args:
        app (Flask): A Flask alkalmazás példánya.
        ip_address (str): Az eszköz IP címe.
    """

    try:
        result = run_adb_command(ip_address,
                                 ['shell', 'cat', '/proc/cpuinfo', '|', 'grep', 'processor', '|', 'wc', '-l'])
        if result.returncode != 0:
            logger.error(f'Hiba a CPU magok számának lekérésekor: {result.stderr}')
            return None

        cpu_cores_count = int(result.stdout.strip())
        cpu_cores.set(cpu_cores_count)  # Prometheus metrika beállítása
        logger.info(f'CPU magok száma sikeresen mentve: {cpu_cores_count}')

    except Exception as e:
        logger.error(f'Hiba a CPU magok számának lekérésekor: {e}', exc_info=True)
        return None

    with app.app_context():
        stop_flag = stop_flags_cpu_memory.get(ip_address, threading.Event())  # Meglévő vagy új Event()
        stop_flags_cpu_memory[ip_address] = stop_flag  # Elmentjük a stop_flag-et

        try:
            while not stop_flag.is_set():  # Ha a stop_flag nincs beállítva, folytatódik a ciklus
                start_time = time.time()
                cpu_memory_usage(ip_address, cpu_cores_count)
                elapsed_time = time.time() - start_time
                stop_flag.wait(max(METRIC_INTERVAL_SECONDS - elapsed_time, 0))  # Stop flag figyelése
        except Exception as e:
            logger.error(f'Hiba a CPU és Memória gyűjtése közben: {e}', exc_info=True)


active_threads = {}


def start_cpu_memory_collection(ip_address: str) -> None:
    """
    Elindítja az eszköz CPU és Memória használatának gyűjtését egy új szálon.

    Ha már van aktív gyűjtés az adott IP-címhez, nem indít új szálat.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if ip_address in active_threads and active_threads[ip_address].is_alive():
        logger.info(f'Az adatgyűjtés már folyamatban van ezen az eszközön: {ip_address}')
        return None

    app = current_app._get_current_object()
    stop_flags_cpu_memory[ip_address] = threading.Event()  # Új stop flag létrehozása
    metric_thread = threading.Thread(target=collect_cpu_memory, args=(app, ip_address), daemon=True)
    metric_thread.start()
    active_threads[ip_address] = metric_thread
    logger.info(f'CPU és Memória adatgyűjtés elindítva: {ip_address}')


def stop_cpu_memory_collection(ip_address: str) -> None:
    """
    Leállítja az eszközön futó CPU és Memória használatának gyűjtését.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if ip_address in active_threads:
        stop_flag = stop_flags_cpu_memory.pop(ip_address, None)
        if stop_flag:
            stop_flag.set()  # Megállítjuk a szál ciklusát
        thread = active_threads.pop(ip_address, None)
        if thread and thread.is_alive():
            thread.join()  # Várunk, hogy a szál leálljon
        logger.info(f'CPU és Memória monitorozás leállítva: {ip_address}')
    else:
        logger.warning(f'Nincs aktív CPU és Memória monitorozás az eszközön: {ip_address}')


stop_flags_bad_frames = {}


def collect_bad_frames(app: Flask, ip_address: str) -> None:
    """
    Folyamatosan gyűjti az alkalmazása használata közben előforduló hibás frame-k számát és elmenti adatbázisba.

    Args:
        app (Flask): A Flask alkalmazás példánya.
        ip_address (str): Az eszköz IP címe.
    """
    with app.app_context():
        stop_flag = stop_flags_bad_frames.get(ip_address, threading.Event())
        stop_flags_bad_frames[ip_address] = stop_flag

        try:
            while not stop_flag.is_set():
                start_time = time.time()
                get_bad_frames(ip_address)
                elapsed_time = time.time() - start_time
                stop_flag.wait(max(METRIC_INTERVAL_SECONDS - elapsed_time, 0))
        except Exception as e:
            logger.error(f'Hiba a hibás frame-ek gyűjtése közben: {e}', exc_info=True)


bad_frames_threads = {}


def start_bad_frames_collection(ip_address) -> None:
    """
    Elindítja az eszközön a hibás frame-k gyűjtését egy új szálon.

    Ha már van aktív gyűjtés az adott IP-címhez, nem indít új szálat.

    Args:
        ip_address (str): Az eszköz IP címe.
    """
    if ip_address in bad_frames_threads and bad_frames_threads[ip_address].is_alive():
        logger.info(f'A hibás frame-ek gyűjtése már folyamatban van: {ip_address}')
        return None

    app = current_app._get_current_object()
    stop_flags_bad_frames[ip_address] = threading.Event()
    bad_frames_thread = threading.Thread(target=collect_bad_frames, args=(app, ip_address), daemon=True)
    bad_frames_thread.start()
    bad_frames_threads[ip_address] = bad_frames_thread
    logger.info(f'Hibás frame-ek adatgyűjtése elindítva: {ip_address}')


def stop_bad_frames_collection(ip_address) -> None:
    """
    Leállítja az eszközön futó hibás frame-k gyűjtését.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if ip_address in bad_frames_threads:
        stop_flag = stop_flags_bad_frames.pop(ip_address, None)
        if stop_flag:
            stop_flag.set()
        thread = bad_frames_threads.pop(ip_address, None)
        if thread and thread.is_alive():
            thread.join()
        logger.info(f'Hibás frame-ek monitorozása leállítva: {ip_address}')
    else:
        logger.warning(f'Nincs aktív hibás frame monitorozás az eszközön: {ip_address}')
