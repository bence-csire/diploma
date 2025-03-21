import logging

from flask import Blueprint, render_template, redirect, url_for, session, flash
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from forms import IpForm, TestForm
from services import run_selected_test
from utils import (is_valid_ip, connect_device, start_cpu_memory_collection,
                   start_bad_frames_collection, stop_cpu_memory_collection, stop_bad_frames_collection)

# Logger inicializálása
logger = logging.getLogger(__name__)

# blueprint definiálása
blueprint = Blueprint('routes', __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def home():
    """
    Kezdőoldal, ahol megadható az eszköz IP-címe és csatlakozni lehet hozzá.

    GET: Megjeleníti az IP cím bekérő űrlapot.
    POST: Validálja az IP címet és ADB-n keresztül megpróbál csatlakozni az eszközhöz.

    Returns:
        Response: A renderelt HTML sablon (index.html), vagy átirányítás a /teszt oldalra.
    """
    form = IpForm()

    if form.validate_on_submit():
        ip_address = form.ip.data.strip()
        logger.info(f'Kapott IP cím: {ip_address}')

        if not is_valid_ip(ip_address):
            flash('Érvénytelen IP cím.', 'Hiba')
            logger.warning(f'Érvénytelen IP cím: {ip_address}')
            return redirect(url_for('routes.home'))

        success, message = connect_device(ip_address)
        if success:
            session['ip_address'] = ip_address
            flash(f'Csatlakoztatva az eszközhöz {ip_address}.', 'Siker')
            return redirect(url_for('routes.test'))
        else:
            flash(f'Sikertelen csatlakozás: {message}', 'Hiba')
            logger.error(f'Nem sikerült csatlakozni az eszközhöz ({ip_address}): {message}')

    return render_template('index.html', form=form)


@blueprint.route('/teszt', methods=['GET', 'POST'])
def test():
    """
    Tesztoldal, ahol kiválasztható és elindítható egy vagy több teszt az eszközön.

    GET: Megjeleníti a tesztválasztó űrlapot.
    POST: Lefuttatja a kiválasztott tesztet, és elindítja a hozzá tartozó adatgyűjtést (ha szükséges).

    Returns:
        Response: A renderelt HTML sablon (test.html), vagy átirányítás hiba esetén.
    """
    form = TestForm()
    ip_address = session.get('ip_address')

    if not ip_address or not is_valid_ip(ip_address):
        flash('Nincs kapcsolódó eszköz vagy hibás az IP cím.', 'hiba')
        return redirect(url_for('routes.home'))

    if form.validate_on_submit():
        test_name = form.tests.data
        try:
            run_selected_test(test_name, ip_address)
            logger.info(f'Teszt futtatva: {test_name}, eszköz: {ip_address}')

            # Ha CPU és Memória teszt, akkor indítsuk el az adatgyűjtést
            if test_name == 'cpu_memory_usage':
                start_cpu_memory_collection(ip_address)

            if test_name == 'bad_frames':
                start_bad_frames_collection(ip_address)

        except Exception as e:
            logger.error(f'Hiba a teszt futtatása közben: {e}', exc_info=True)
            flash('Nem sikerült lefuttatni a tesztet.', 'Hiba')

    return render_template('test.html', form=form)


@blueprint.route('/metrics')
def prometheus_metrics():
    """
    A Prometheus által lekérdezhető metrikákat adja vissza formázott szövegként.

    Returns:
        tuple: A metrikák, HTTP státuszkód (200), és a tartalom típusa.
    """
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# eszköz lecsatlakozása gomb
@blueprint.route('/disconnect')
def disconnect():
    """
    Az aktuálisan csatlakoztatott eszköz lecsatlakoztatása.

    Törli a session-ben tárolt IP-címet, és visszairányít a kezdőoldalra.

    Returns:
        Response: Átirányítás a kezdőlapra.
    """
    session.pop('ip_address', None)
    flash('Eszköz lecsatlakoztatva.', 'info')
    logger.info('Eszköz lecsatlakoztatva.')
    return redirect(url_for('routes.home'))


@blueprint.route('/stop_test/<test_name>', methods=['POST'])
def stop_test(test_name):
    """
    Egy vagy több futó teszt (CPU/memória, hibás frame-ek) leállítása.

    Args:
        test_name (str): A leállítandó teszt neve ('cpu_memory_usage', 'bad_frames', 'all_tests').

    Returns:
        Response: Átirányítás a tesztoldalra. Hiba esetén figyelmeztető üzenet.
    """
    ip_address = session.get('ip_address')

    if not ip_address or not is_valid_ip(ip_address):
        flash('Nincs kapcsolódó eszköz vagy hibás az IP cím.', 'hiba')
        return redirect(url_for('routes.test'))

    if test_name == 'cpu_memory_usage':
        stop_cpu_memory_collection(ip_address)
    elif test_name == 'bad_frames':
        stop_bad_frames_collection(ip_address)
    elif test_name == 'all_tests':
        stop_cpu_memory_collection(ip_address)
        stop_bad_frames_collection(ip_address)
    else:
        flash('Érvénytelen teszt leállítási kérés.', 'Hiba')
        return redirect(url_for('routes.test'))

    flash(f'{test_name} teszt(ek) leállítva.', 'info')
    return redirect(url_for('routes.test'))
