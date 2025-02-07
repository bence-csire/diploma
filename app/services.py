import time

from utils import run_adb_command, get_device_info, is_valid_ip
from database import save_record
from models import LaunchTime, CpuUsage, MemoryUsage

# ADB parancsokhoz használt állandók
APP_PACKAGE = 'com.google.android.youtube'
APP_ACTIVITY = '.HomeActivity'


def start_app(ip_address: str) -> None:
    """
    Az alkalmazás elindítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    run_adb_command(ip_address, ['shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'])


def stop_app(ip_address: str) -> None:
    """
    Az alkalmazás leállítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    run_adb_command(ip_address, ['shell', 'am', 'force-stop', APP_PACKAGE])


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
        test_functions[test_name](ip_address)


def launch_time(ip_address: str) -> None:
    """
    Az alkalmazés indítási idejének mérése és mentése adatbázisba

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        return
    result = run_adb_command(ip_address, ['shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'])
    if not result:
        return
    lines = result.stdout.splitlines()
    startup_state = next((line.split()[-1] for line in lines if 'LaunchState' in line), 'Unknown')
    startup_time = next((line.split()[-1] for line in lines if 'TotalTime' in line), '0')
    device_name, android_version = get_device_info(ip_address)
    save_record(
        LaunchTime,
        ip_address=ip_address,
        device=device_name,
        android_version=android_version,
        application=APP_PACKAGE.split('.')[-1],
        startup_state=startup_state,
        startup_time=startup_time)
    time.sleep(3)
    stop_app(ip_address)


def cpu_usage(ip_address: str) -> None:
    """
    Az alkalmazás CPU használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        return
    start_app(ip_address)
    time.sleep(20)
    result = run_adb_command(ip_address, ['shell', 'dumpsys', 'cpuinfo'])
    if result:
        lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
        print(lines)
        cpu_usage_value = lines[0].split()[0] if lines else 'N/A'
        device_name, android_version = get_device_info(ip_address)
        save_record(
            CpuUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            application=APP_PACKAGE.split('.')[-1],
            cpu_usage=cpu_usage_value
        )

    stop_app(ip_address)


def memory_usage(ip_address: str) -> None:
    """
    Az alkalmazás memória használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    if not is_valid_ip(ip_address):
        return
    start_app(ip_address)
    time.sleep(10)
    result = run_adb_command(ip_address, ['shell', 'dumpsys', 'meminfo'])
    if result:
        lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
        memory_usage_value = lines[0].split()[0] if lines else 'N/A'
        device_name, android_version = get_device_info(ip_address)
        save_record(
            MemoryUsage,
            ip_address=ip_address,
            device=device_name,
            android_version=android_version,
            application=APP_PACKAGE.split('.')[-1],
            memory_usage=memory_usage_value
        )

    stop_app(ip_address)
