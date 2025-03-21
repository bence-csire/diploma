import logging

from flask import Flask
from flask_bootstrap import Bootstrap5
from config import SECRET_KEY, DATABASE_URI
from database import init_app
from routes import blueprint

# Log konfiguráció
logging.basicConfig(
    level=logging.INFO,  # DEBUG ha több infót szeretnék
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # Log egy fájlba
        logging.StreamHandler()  # Log konzolba
    ]
)

logger = logging.getLogger(__name__)  # Main logger


def create_app():
    """
    Flask, adatbázis és Bootstrap5 inicializálása, blueprintek regisztrálása

    Returns:
        Flask: Inicializált Flask alkalmazás.
    """
    app = Flask(__name__)

    try:
        app.config['SECRET_KEY'] = SECRET_KEY
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

        # Adatbázis inicializálása
        with app.app_context():
            init_app(app)

        # Bootstrap inicializálása
        Bootstrap5(app)
        logger.info('Bootstrap inicializálása sikeres volt.')

        app.register_blueprint(blueprint)
        logger.info('Blueprintek regisztrálása sikeres volt.')

    except Exception as e:
        logger.error(f'Hiba az app inicializálása közben: {e}', exc_info=True)
        raise

    return app
