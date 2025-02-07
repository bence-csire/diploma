from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_app(app):
    """
    Az adatbázis inicializálása és létrehozza a szükséges táblákat.

    Args:
        app (Flask): A Flask alkalmazás.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()


def save_record(model, **kwargs):
    """
    Új rekord mentése az adatbázisba.

    Args:
        model (db.Model): Az adatbázis modell osztálya.
        **kwargs: Az új rekord mezőinek értékei.
    """
    try:
        record = model(**kwargs)
        db.session.add(record)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f'Database error: {e}')
