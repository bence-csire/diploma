# Általános IP ellenőrzés
import ipaddress

def is_valid_ip(ip: str) -> bool:
    """
    Ellenőrzi, hogy a megadott IP cím létező IPv4 vagy IPv6 cím.
    Felhasználása általánosan a kódban.

    Args:
        ip (str): Az ellenőrzendő IP cím.

    Returns:
        bool: True ha helyes, különben False.
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False