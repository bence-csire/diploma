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
from models import CpuMemoryUsage, StorageUsage

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
        logger.info(f"Sikeres IP validáció: {ip}")
        return True
    except ValueError:
        logger.warning(f"Érvénytelen IP cím: {ip}")
        return False


# Flask IP validáció
def validate_ip(form: FlaskForm, field: Field) -> None:
    """
    Egyedi IP cím validáló függvény, Flask formmal.
    ValidationError-t ad vissza, ha a bemenet nem egy érvényes IP cím.

    Args:
        form (FlaskForm): Flask form ami az ellenőrzendő mezőt tartalmazza
        field (Field): Ellenőrzendő mező.
    """
    if not is_valid_ip(field.data):
        logger.error(f"Form validációs hiba: Érvénytelen IP cím - {field.data}")
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
        logger.error(f"Érvénytelen IP cím lett megadva: {ip_address}, ADB parancs futtatása sikertelen")
        return subprocess.CompletedProcess(args=['adb'], returncode=1)  # Dummy return, hogy a type egyforma maradjon

    logger.info(f"ADB parancs futtatása: {command} az eszközön {ip_address}")
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
        logger.error(f"Eszköz információ lekérése sikertelen: Érvénytelen IP cím - {ip_address}")
        raise ValueError("Érvénytelen IP cím.")
    try:
        device_name = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.product.marketname'],
            encoding='utf-8').strip()
        android_version = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.build.version.release'],
            encoding='utf-8').strip()
        logger.info(f"Eszköz neve: {device_name}, Android verzió: {android_version}, IP cím {ip_address}.")
        return device_name, android_version
    except subprocess.CalledProcessError as e:
        logger.error(f"Hiba történt az eszköz információ lekérésekor: {e}", exc_info=True)
        raise RuntimeError(f"Hiba történt: {e}")


def connect_device(ip_address: str) -> tuple[bool, str]:
    """
    Csatlakozás az eszközhöz ADB-n keresztül.
    """
    if not is_valid_ip(ip_address):
        logger.error(f"Csatlakozás sikertelen: Érvénytelen IP cím - {ip_address}")
        return False, 'Érvénytelen IP cím.'

    result = run_adb_command(ip_address, ['connect', ip_address])

    if 'connected' in result.stdout.lower():
        logger.info(f"Sikeresen csatlakozott az eszközhöz: {ip_address}")
        return True, f'Csatlakoztatva az eszközhöz {ip_address}.'

    logger.warning(f"Csatlakozás sikertelen az eszközhöz: {ip_address}, válasz: {result.stdout or result.stderr}")
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



def cpu_memory_usage(ip_address: str):
    """
    ADB segítségével lekéri az eszköz CPU és memóriahasználati adatait és elmenti az adatbázisba.

    Args:
        ip_address (str): Az eszköz IP címe.
    """
    try:
        output = subprocess.check_output(["adb", "-s", ip_address, "shell", "top", "-n", "1"], text=True)
        lines = output.split("\n")

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
            logger.info(f"CPU used: {cpu_used}%")

        if memory_total is not None and memory_used is not None:
            mem_total.set(memory_total)
            mem_usage.set(memory_used)
            mem_percentage.set((memory_used / memory_total) * 100)
            logger.info(f"MEM total: {memory_total} KB, MEM used: {memory_used} KB, MEM usage: {round((memory_used / memory_total) * 100, 2)}%")

        # Adatok mentése adatbázisba
        if cpu_used is not None or (memory_total is not None and memory_used is not None):
            device_name, android_version = get_device_info(ip_address)
            save_record(
                CpuMemoryUsage,
                ip_address=ip_address,
                device=device_name,
                android_version=android_version,
                cpu_usage=str(cpu_used),
                memory_usage=str(memory_used),
                memory_percentage=str((memory_used / memory_total) * 100)
            )
            logger.info(f"CPU adat elmentve DB-be: {cpu_used}, {memory_used}, {(memory_used / memory_total) * 100}%")
        start_metric_collection(ip_address)


    except subprocess.CalledProcessError as e:
        logger.error(f"Error running adb command: {e}")


def get_uptime(ip_address: str):
    """
    Lekéri az eszköz uptime értékét.
    """
    if not is_valid_ip(ip_address):
        logger.warning(f"Érvénytelen IP cím: {ip_address}")
        return

    try:
        result = run_adb_command(ip_address, ["shell", "cat", "/proc/uptime"])
        if result.returncode != 0:
            logger.error(f"Hiba az uptime lekérésekor: {result.stderr}")
            return None

        uptime_seconds = float(result.stdout.split()[0])
        uptime_hours = uptime_seconds / 3600
        uptime_metric.set(uptime_hours)
        logger.info(f"Uptime: {uptime_hours} óra")

        return uptime_hours
    except Exception as e:
        logger.error(f"Hiba az uptime lekérésekor: {e}")
        return None


def sanitize_numeric_value(value: str) -> float:
    """
    Eltávolítja az utolsó karaktert, ha az nem numerikus (pl. G, M, K, %),
    és lebegőpontos számmá alakítja.

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
        logger.error(f"Nem sikerült átalakítani numerikus értékké: {value}")
        return 0.0  # Visszaadhatunk egy alapértelmezett értéket


def get_storage_info(ip_address: str):
    """
    Lekéri az eszköz tárhelyének állapotát az ADB segítségével.

    Args:
        ip_address (str): Az eszköz IP címe.

    Returns:
        dict: A tárhely adatait tartalmazó szótár.
    """
    if not is_valid_ip(ip_address):
        logger.error(f"Érvénytelen IP cím: {ip_address}")
        return {}

    try:
        result = run_adb_command(ip_address, ["shell", "df", "-h", "/data"])

        if result.returncode != 0:
            logger.error(f"Hiba a tárhelyinformációk lekérésekor: {result.stderr}")
            return {}

        lines = result.stdout.splitlines()
        if len(lines) < 2:
            logger.error("Nem sikerült feldolgozni a tárhely információkat.")
            return {}

        data_line = lines[1].split()
        storage_info = {
            "total": data_line[1],  # Teljes tárhely
            "usage": data_line[2],  # Foglalt tárhely
            "available": data_line[3],  # Szabad tárhely
            "percentage": data_line[4]  # Használati arány
        }

        storage_usage.set(sanitize_numeric_value(storage_info["usage"]))
        storage_percentage.set(sanitize_numeric_value(storage_info["percentage"]))
        logger.info(f"Tárhely információk: {storage_info}")

        try:
            device_name, android_version = get_device_info(ip_address)
            save_record(
                StorageUsage,
                ip_address=ip_address,
                device=device_name,
                android_version=android_version,
                total=storage_info["total"],
                used=storage_info["usage"],
                available=storage_info["available"],
                percentage=storage_info["percentage"]
            )
            logger.info(f"Tárhelyadatok sikeresen mentve: {storage_info}")
        except Exception as e:
            logger.error(f"Hiba történt a tárhelyadatok mentése közben: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Hiba történt a tárhelyadatok lekérésekor: {e}", exc_info=True)
        return {}


def get_bad_frames(ip_address: str):
    """
    Lekéri a hibás framek számát az ADB dumpsys gfxinfo segítségével.
    """
    try:
        result = run_adb_command(ip_address, ["shell", "dumpsys", "gfxinfo", "framestats"])
        if result.returncode != 0:
            logger.error(f"Hiba a frame információ lekérésekor: {result.stderr}")
            return None

        dropped_frames = 0
        for line in result.stdout.splitlines():
            if "Janky frames" in line:
                dropped_frames = int(line.split(":")[1].strip())
                break

        bad_frames_metric.set(dropped_frames)
        logger.info(f"Hibás framek: {dropped_frames}")

        return dropped_frames
    except Exception as e:
        logger.error(f"Hiba a frame információ lekérésekor: {e}")
        return None


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

                # CPU és memória mentése az adatbázisba
                cpu_memory_usage(ip_address)

                # Hibás framek lekérése
                get_bad_frames(ip_address)

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
