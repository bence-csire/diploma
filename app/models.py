import datetime

from flask_sqlalchemy import SQLAlchemy

from database import db


# creating tables
class LaunchTime(db.Model):
    """
    Az alkalmazás indítási idejének rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        startup_state (str): Az indítási állapot.
        startup_time (int): Az indítási idő ms-ban.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    application = db.Column(db.String(100), nullable=False)
    startup_state = db.Column(db.String(100), nullable=False)
    startup_time = db.Column(db.Integer, nullable=False)


class CpuUsage(db.Model):
    """
    Az alkalmazás CPU-használatának rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        cpu_usage (str): CPU-használati érték.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    application = db.Column(db.String(100), nullable=False)
    cpu_usage = db.Column(db.String(100), nullable=False)


class MemoryUsage(db.Model):
    """
    Az alkalmazás memóriahasználatának rögzítésére szolgáló tábla.

    Attributes:
        id (int): Egyedi azonosító.
        memory_usage (str): Memória használati érték.
        device (str): Az eszköz neve.
        android_version (str): Az eszköz Android verziója.
        timestamp (datetime): Az adat rögzítésének ideje.
        ip_address (str): Az eszköz IP-címe.
    """
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now, index=True)
    ip_address = db.Column(db.String(100), nullable=False, index=True)
    device = db.Column(db.String(100), nullable=False)
    android_version = db.Column(db.String(100), nullable=False)
    application = db.Column(db.String(100), nullable=False)
    memory_usage = db.Column(db.String(100), nullable=False)