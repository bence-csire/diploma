from flask import Flask, render_template, redirect, url_for, session, flash, jsonify
from flask_bootstrap import Bootstrap5

from database import init_app
from models import LaunchTime
from utils import is_valid_ip, connect_device
from services import run_selected_test
from forms import IpForm, TestForm
from config import SECRET_KEY, DATABASE_URI

# TODO Hibakezelés
# TODO Kapcsolódó eszköz jelzése a teszt oldalon (honlap)
# TODO disconnect gomb hozáádása
# TODO Log
# TODO main legyen tiszta, külön utils file function és classoknak
# TODO THREDING sleep helyett!!!
# TODO input validálás
# TODO honlapon eredményeknél választani lehessen
# TODO docstring és commentek


def create_app():
    """Flask alkalmazás inicializálása"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

    # Adatbázis inicializálása
    init_app(app)

    # Bootstrap inicializálása
    Bootstrap5(app)

    return app

app = create_app()


@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Kezdőoldal az eszköz IP-címének megadására és csatlakozásra.

    Returns:
        Renderelt HTML sablon a kezdőoldalhoz.
    """
    form = IpForm()
    if form.validate_on_submit():
        ip_address = form.ip.data.strip()
        if not is_valid_ip(ip_address):
            flash('Érvénytelen IP cím.', 'Hiba')
            return redirect(url_for('home'))
        success, message = connect_device(ip_address)
        if success:
            session['ip_address'] = ip_address
            flash(f'Csatlakoztatva az eszközhöz {ip_address}.', 'Siker')
            return redirect(url_for('test'))
        else:
            flash(f'Sikertelen csatlakozás: {message}', 'Hiba')

    return render_template('index.html', form=form)


@app.route('/teszt', methods=['GET', 'POST'])
def test():
    """
    Oldal a tesztek futtatására a csatlakoztatott eszközön.

    Returns:
        Renderelt HTML sablon a tesztválasztó oldalhoz.
    """
    form = TestForm()
    ip_address = session.get('ip_address')

    if not ip_address or not is_valid_ip(ip_address):
        flash('Nincs kapcsolódó eszköz vagy hibás az IP cím.', 'hiba')
        return redirect(url_for('home'))

    if form.validate_on_submit():
        run_selected_test(form.tests.data, ip_address)

    return render_template('test.html', form=form)


@app.route('/eredmenyek', methods=['GET'])
def chart():
    """
    Tesztek eredményeit grafikonon jeleníti meg, az "eredmenyek" oldalon.

    Returns:
        Renderelt HTML sablon az eredmények oldalhoz.
    """
    return render_template('result.html')


# Route to serve data for the chart
@app.route('/chart_data', methods=['GET'])
def chart_data():
    """
    Adatokat biztosít az eredmény grafikon számára.

    Returns:
        JSON objektum a tesztek eredményeivel és átlagértékekkel.
    """
    data = LaunchTime.query.order_by(LaunchTime.timestamp.desc()).limit(10).all()

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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)