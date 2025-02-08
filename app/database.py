import logging

from flask_sqlalchemy import SQLAlchemy

# Logger inicializálása
logger = logging.getLogger(__name__)

db = SQLAlchemy()


def init_app(app):
    """
    Az adatbázis inicializálása és létrehozza a szükséges táblákat.

    Args:
        app (Flask): A Flask alkalmazás.
    """
    try:
        db.init_app(app)
        with app.app_context():
            db.create_all()
        logger.info("Az adatbázis inicializálása sikeres volt.")
    except Exception as e:
        logger.error(f"Hiba történt az adatbázis inicializálása közben: {e}", exc_info=True)
        raise RuntimeError("Nem sikerült inicializálni az adatbázist.") from e


def validate_record(model, data):
    """
    Validálja a rekordot az adatbázis modelljének megfelelően.

    Args:
        model (db.Model): Az adatbázis modell osztálya.
        data (dict): A beszúrandó rekord adatai.

    Returns:
        dict: A validált adatokat tartalmazó szótár.

    Raises:
        ValueError: Ha érvénytelen mezőt találunk, vagy ha egy szükséges mező hiányzik.
    """
    valid_fields = {column.name for column in model.__table__.columns}  # Megengedett mezők
    validated_data = {}

    for key, value in data.items():
        if key not in valid_fields:
            logger.warning(f"Érvénytelen mező: {key} nem létezik a {model.__name__} modellben.")
            raise ValueError(f"Érvénytelen mező: {key}")

        if value is None:
            logger.warning(f"Üres mező: {key} a {model.__name__} modellben.")
            raise ValueError(f"Az {key} mező nem lehet üres.")

        validated_data[key] = value

    return validated_data


def save_record(model, **kwargs):
    """
    Új rekord mentése az adatbázisba.

    Args:
        model (db.Model): Az adatbázis modell osztálya.
        **kwargs: Az új rekord mezőinek értékei.

    Returns:
        object: A mentett rekord
    """
    try:
        # Validáció
        validated_data = validate_record(model, kwargs)

        record = model(**validated_data)
        db.session.add(record)
        db.session.commit()
        logger.info(f"Sikeresen mentett rekord: {record}")
        return record
    except ValueError as ve:
        logger.error(f"Validációs hiba: {ve}")
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Adatbázis hiba a rekord mentése közben: {e}", exc_info=True)
        raise RuntimeError("Nem sikerült menteni a rekordot az adatbázisba.") from e
