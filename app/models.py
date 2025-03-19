import datetime

from database import db


# adatbázis táblák létrehozása
class StorageUsage(db.Model):
    """
    Az eszköz tárhelyének rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        total (str): Teljes tárhely.
        used (str): Foglalt tárhely.
        available (str): Szabad tárhely.
        percentage (str): Használat tárhely százalékban.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    total = db.Column(db.String(100), nullable=False)
    used = db.Column(db.String(100), nullable=False)
    available = db.Column(db.String(100), nullable=False)
    percentage = db.Column(db.String(100), nullable=False)


class CpuMemoryUsage(db.Model):
    """
    Az alkalmazás CPU-használatának rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        cpu_usage (str): CPU használati érték.
        memory_usage (str): Memória használati érték.
        memory_percentage (str): Memória használat százalékban
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    cpu_usage = db.Column(db.String(100), nullable=False)
    memory_usage = db.Column(db.String(100), nullable=False)
    memory_percentage = db.Column(db.String(100), nullable=False)


class UptimeUsage(db.Model):
    """
    Az eszköz futási idejének rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        uptime_hours (float): Az eszköz uptime értéke órákban.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    uptime_hours = db.Column(db.Float, nullable=False)


class BadFramesUsage(db.Model):
    """
    Az eszköz hibás frame-jeinek rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        bad_frames (int): Hibás frame-ek száma.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    bad_frames = db.Column(db.Integer, nullable=False)