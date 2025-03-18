import logging

from flask import Blueprint, render_template, redirect, url_for, session, flash, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from models import LaunchTime
from utils import is_valid_ip, connect_device
from services import run_selected_test,  start_metric_collection
from forms import IpForm, TestForm


# Logger inicializálása
logger = logging.getLogger(__name__)

# blueprint definiálása
blueprint = Blueprint("routes", __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def home():
    """
    Kezdőoldal az eszköz IP-címének megadására és csatlakozásra.

    Returns:
        Renderelt HTML sablon a kezdőoldalhoz.
    """
    form = IpForm()

    if form.validate_on_submit():
        ip_address = form.ip.data.strip()
        logger.info(f"Kapott IP cím: {ip_address}")

        if not is_valid_ip(ip_address):
            flash('Érvénytelen IP cím.', 'Hiba')
            logger.warning(f"Érvénytelen IP cím: {ip_address}")
            return redirect(url_for('routes.home'))

        success, message = connect_device(ip_address)
        if success:
            session['ip_address'] = ip_address
            flash(f'Csatlakoztatva az eszközhöz {ip_address}.', 'Siker')
            logger.info(f"Sikeresen csatlakozott az eszközhöz: {ip_address}")
            return redirect(url_for('routes.test'))
        else:
            flash(f'Sikertelen csatlakozás: {message}', 'Hiba')
            logger.error(f"Nem sikerült csatlakozni az eszközhöz ({ip_address}): {message}")

    return render_template('index.html', form=form)


@blueprint.route('/teszt', methods=['GET', 'POST'])
def test():
    form = TestForm()
    ip_address = session.get('ip_address')

    if not ip_address or not is_valid_ip(ip_address):
        flash('Nincs kapcsolódó eszköz vagy hibás az IP cím.', 'hiba')
        return redirect(url_for('routes.home'))

    if form.validate_on_submit():
        test_name = form.tests.data
        try:
            run_selected_test(test_name, ip_address)
            logger.info(f"Tesz futtatva: {test_name}, eszköz: {ip_address}")

            # Ha CPU és Memória teszt, akkor indítsuk el az adatgyűjtést
            if test_name == "cpu_memory_usage":
                start_metric_collection(ip_address)

        except Exception as e:
            logger.error(f"Hiba történt a teszt futtatása közben: {e}", exc_info=True)
            flash("Nem sikerült lefuttatni a tesztet.", "Hiba")

    return render_template('test.html', form=form)


@blueprint.route('/metrics')
def prometheus_metrics():
    """
    Prometheus formátumban visszaadja az aktuális metrikákat.
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@blueprint.route('/eredmenyek', methods=['GET'])
def chart():
    """
    Tesztek eredményeit grafikonon jeleníti meg, az "eredmenyek" oldalon.

    Returns:
        Renderelt HTML sablon az eredmények oldalhoz.
    """
    try:
        logger.info("Eredmények oldal megnyitása.")
        return render_template('result.html')
    except Exception as e:
        logger.error(f"Hiba történt az eredmények oldal betöltésekor: {e}", exc_info=True)
        flash("Nem sikerült betölteni az eredmények oldalt.", "Hiba")
        return redirect(url_for('routes.home'))


# Route to serve data for the chart
@blueprint.route('/chart_data', methods=['GET'])
def chart_data():
    """
    Adatokat biztosít az eredmény grafikon számára.

    Returns:
        JSON objektum a tesztek eredményeivel és átlagértékekkel.
    """
    try:
        data = LaunchTime.query.order_by(LaunchTime.timestamp.desc()).limit(10).all()
        logger.info(f"Eredményadatok lekérése: {len(data)} rekord.")

        result = [
            {
                'timestamp': record.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'startup_time': int(record.startup_time),
                'startup_state': record.startup_state
            }
            for record in data
        ]

        average_startup_time = sum(item['startup_time'] for item in result) / len(result) if result else 0

        return jsonify({'data': result, 'average': average_startup_time})

    except Exception as e:
        logger.error(f"Hiba történt az eredmények lekérése közben: {e}", exc_info=True)
        return jsonify({'error': 'Nem sikerült lekérni az eredményeket.'}), 500


# eszköz lecsatlakozása gomb
@blueprint.route('/disconnect')
def disconnect():
    """
    Eszköz lecsatlakoztatása.
    """
    session.pop('ip_address', None)
    flash('Eszköz lecsatlakoztatva.', 'info')
    logger.info("Eszköz lecsatlakoztatva.")
    return redirect(url_for('routes.home'))
