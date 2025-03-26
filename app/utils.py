import subprocess
import logging
import re

from database import save_record
from models import CpuMemoryUsage, StorageUsage, UptimeUsage, BadFramesUsage
from validation import is_valid_ip
from adb import run_adb_command, get_device_info
from metrics import sanitize_numeric_value, storage_usage, storage_percentage, uptime_metric, mem_usage, mem_total, mem_percentage, cpu_user_usage, bad_frames_metric

# Logger inicializálása
logger = logging.getLogger(__name__)

# Alapértelmezett változók
STORAGE_PATH = '/data'  # Tárhely monitorozásának elérési útvonala
MONITORED_PACKAGE = 'com.telekom.onetv.tv'    # Applikáció, ahol a hiábs frameket figyeli


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
        output = subprocess.check_output(['adb', '-s', ip_address, 'shell', 'top', '-b', '-n', '1'], text=True)
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
