import ipaddress
import subprocess
import logging
import re
import time
import threading

from flask import Flask, flash, current_app
from flask_wtf import FlaskForm
from wtforms.validators import ValidationError
from wtforms.fields.core import Field
from prometheus_client import Gauge

from database import save_record
from models import CpuMemoryUsage, StorageUsage, UptimeUsage, BadFramesUsage

# Logger inicializálása
logger = logging.getLogger(__name__)

# Alapértelmezett változók
STORAGE_PATH = '/data'  # Tárhely monitorozásának elérési útvonala
MONITORED_PACKAGE = 'com.google.android.youtube'    # Applikáció, ahol a hiábs frameket figyeli
METRIC_INTERVAL_SECONDS = 10    # Metrika lekérdezésének gyakorisága másodpercben


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
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.product.marketname'],
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


def get_storage_info(ip_address: str, path: str = STORAGE_PATH) -> dict[str, str]:
    """
    Lekéri az eszköz tárhelyének állapotát ADB paranccsal.

    Args:
        ip_address (str): Az eszköz IP címe.
        path (str): A file system, amely tárhely adatait kinyeri

    Returns:
        dict: A tárhely adatait tartalmazó szótár.
    """
    if not is_valid_ip(ip_address):
        logger.error(f'Érvénytelen IP cím: {ip_address}')
        return {}

    try:
        result = run_adb_command(ip_address, ['shell', 'df', '-h', path])

        if result.returncode != 0:
            logger.error(f'Hiba a tárhely adatok lekérésekor: {result.stderr}')
            return {}

        lines = result.stdout.splitlines()
        if len(lines) < 2:
            logger.error('Nem sikerült feldolgozni a tárhely adatokat.')
            return {}

        data_line = lines[1].split()
        storage_info = {
            'total': data_line[1],  # Teljes tárhely
            'usage': data_line[2],  # Foglalt tárhely
            'available': data_line[3],  # Szabad tárhely
            'percentage': data_line[4]  # Használati arány
        }

        storage_usage.set(sanitize_numeric_value(storage_info['usage']))
        storage_percentage.set(sanitize_numeric_value(storage_info['percentage']))

        try:
            device_name, android_version = get_device_info(ip_address)
            save_record(
                StorageUsage,
                ip_address=ip_address,
                device=device_name,
                android_version=android_version,
                total=storage_info['total'],
                used=storage_info['usage'],
                available=storage_info['available'],
                percentage=storage_info['percentage']
            )
            logger.info(f'Tárhely adatok sikeresen mentve: {storage_info}')
        except Exception as e:
            logger.error(f'Hiba a tárhely adatok mentése közben: {e}', exc_info=True)
    except Exception as e:
        logger.error(f'Hiba a tárhely adatok lekérésekor: {e}', exc_info=True)
        return {}


def get_uptime(ip_address: str) -> float | None:
    """
    Lekéri az eszköz futási idejét (órában), és elmenti adatbázisba.

    Args:
        ip_address (str): Az eszköz IP címe.

    Returns:
        float | None: Az eszköz futási ideje órában, vagy None, ha hiba történt.
    """
    if not is_valid_ip(ip_address):
        logger.warning(f'Érvénytelen IP cím: {ip_address}')
        return None

    try:
        result = run_adb_command(ip_address, ['shell', 'cat', '/proc/uptime'])
        if result.returncode != 0:
            logger.error(f'Hiba az uptime lekérésekor: {result.stderr}')
            return None

        uptime_seconds = float(result.stdout.split()[0])
        uptime_hours = uptime_seconds / 3600
        uptime_metric.set(uptime_hours)

        # Eszköz adatok lekérése
        device_name, android_version = get_device_info(ip_address)

        # Uptime mentése adatbázisba
        save_record(
            UptimeUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            uptime_hours=uptime_hours
        )
        logger.info(f'Uptime adatok sikeresen mentve: {uptime_hours} óra')

        return uptime_hours
    except Exception as e:
        logger.error(f'Hiba az uptime lekérésekor: {e}')
        return None


def cpu_memory_usage(ip_address: str, cpu_core: int) -> None:
    """
    ADB paranccsal lekéri az eszköz CPU és memóriahasználati adatait és elmenti adatbázisba.

    Args:
        ip_address (str): Az eszköz IP címe.
        cpu_core (int): Processzor magok száma.

    Returns:
        None
    """
    try:
        output = subprocess.check_output(['adb', '-s', ip_address, 'shell', 'top', '-n', '1'], text=True)
        lines = output.split('\n')

        cpu_used = None
        memory_total = None
        memory_used = None

        for line in lines:
            # CPU used keresése
            cpu_match = re.search(r'(\d+)%user', line)
            if cpu_match:
                cpu_used = int(cpu_match.group(1))

            # Memóriahasználat keresése
            mem_match = re.search(r'Mem:\s+(\d+)K total,\s+(\d+)K used', line)
            if mem_match:
                memory_total = int(mem_match.group(1))
                memory_used = int(mem_match.group(2))

        # Ha megtaláltuk az adatokat, frissítjük a Prometheus metrikákat
        if cpu_used is not None:
            cpu_user_usage.set(cpu_used)
            logger.info(f'CPU használat: {cpu_used}%')

        if memory_total is not None and memory_used is not None:
            mem_total.set(memory_total)
            mem_usage.set(memory_used)
            mem_percentage.set((memory_used / memory_total) * 100)
            logger.info(f'Összes memória: {memory_total} KB, Használt memória: {memory_used} KB, '
                        f'használt memória (százalékban): {round((memory_used / memory_total) * 100, 2)}%')

        # Adatok mentése adatbázisba
        if cpu_used is not None or (memory_total is not None and memory_used is not None):
            device_name, android_version = get_device_info(ip_address)
            save_record(
                CpuMemoryUsage,
                ip_address=ip_address,
                device=device_name,
                android_version=android_version,
                cpu_usage=str(cpu_used),
                cpu_core=str(cpu_core),
                memory_usage=str(memory_used),
                memory_percentage=str((memory_used / memory_total) * 100)
            )
            logger.info(f'CPU és Memória adatok sikeresen mentve: '
                        f'{cpu_used}, {memory_used}, {(memory_used / memory_total) * 100}%')

    except subprocess.CalledProcessError as e:
        logger.error(f'Hiba az ADB parancs futtatása közben: {e}')


def get_bad_frames(ip_address: str, package_name: str = MONITORED_PACKAGE) -> int | None:
    """
    Lekéri az adott alkalmazás hibás framejeinek számát ADB paranccsal és elmenti adatbázisba.

    Args:
        ip_address (str): Az eszköz IP címe.
        package_name (str): A figyelt alkalmazás csomagneve

    Returns:
        int | None: Hibás frame-ek száma, vagy None, ha hiba történt.
    """
    try:
        result = run_adb_command(ip_address, ['shell', 'dumpsys', 'gfxinfo', package_name])
        if result.returncode != 0:
            logger.error(f'Hiba a frame adatok lekérésekor: {result.stderr}')
            return None

        dropped_frames = 0
        for line in result.stdout.splitlines():
            if 'Janky frames' in line:
                frame_value = line.split(':')[1].strip()
                frame_number = re.findall(r'\d+', frame_value)  # Csak számokat keresünk
                if frame_number:
                    dropped_frames = int(frame_number[0])  # Az első számot használjuk
                break

        bad_frames_metric.set(dropped_frames)
        # Eszköz adatok lekérése
        device_name, android_version = get_device_info(ip_address)

        # Hibás framek mentése adatbázisba
        save_record(
            BadFramesUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            bad_frames=dropped_frames
        )
        logger.info(f'Hibás frame adatok sikeresen mentve: {dropped_frames}')

        return dropped_frames
    except Exception as e:
        logger.error(f'Hiba a hibás frame adatok lekérésekor: {e}')
        return None


stop_flags_cpu_memory = {}


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
