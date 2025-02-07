import subprocess
import time
import ipaddress

from flask import Flask, render_template, redirect, url_for, session, flash, jsonify
from flask_bootstrap import Bootstrap5  #BootstrapFlask telepítése, ez támogatja Bootstrap5-öt, ezért van ez a warning
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError
from wtforms.fields.core import Field

from database import db, init_app, save_record, LaunchTime, CpuUsage, MemoryUsage

# TODO Hibakezelés
# TODO Kapcsolódó eszköz jelzése a teszt oldalon (honlap)
# TODO disconnect gomb hozáádása
# TODO Log
# TODO config file a kulcsokhoz
# TODO IP address class, validálás
# TODO main legyen tiszta, külön utils file function és classoknak
# TODO THREDING sleep helyett!!!
# TODO input validálás
# TODO honlapon eredményeknél választani lehessen


# ADB parancsokhoz használt állandók
APP_PACKAGE = 'com.google.android.youtube'
APP_ACTIVITY = '.HomeActivity'
DATABASE_URI = 'sqlite:///android.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

# Adatbázis és Bootstrap inicializálása
init_app(app)
Bootstrap5(app)


# Általános IP ellenőrzés
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


# Flask IP ellenőrzés
def validate_ip(form: FlaskForm, field: Field) -> None:
    """
    Egyedi IP cím validáló függvény, Flask formmal.
    ValidationError-t ad vissza, ha a bemenet nem egy érvényes IP cím.
    Felhasználása Flask form-nál.

    Args:
        form (FlaskForm): Form, amely tartalmazza a mezőt.
        field (Field): Ellenőrzendő mező.
    """
    if not is_valid_ip(field.data):
        raise ValidationError('Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.')


class IpForm(FlaskForm):
    """
    Form a tesztelni kívánt eszköz IP címének megadásához.
    """
    ip = StringField('IP address', validators=[DataRequired(), validate_ip])
    submit = SubmitField('Küldés')


class TestForm(FlaskForm):
    """
    Form a teszt kiválasztásához és elindításához.
    """
    tests = SelectField('Select an option:', choices=[('launch_time', 'Indítási idő'), ('cpu_usage', 'CPU'),
                                                      ('memory_usage', 'Memória')],
                        validators=[DataRequired()])
    submit = SubmitField('Küldés')


def start_app(ip_address: str) -> None:
    """
    Az alkalmazás elindítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if is_valid_ip(ip_address):
        subprocess.run(
            ['adb', '-s', ip_address, 'shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'],
            capture_output=True,
            text=True
        )
    else:
        flash('Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.', 'Hiba')


def stop_app(ip_address: str) -> None:
    """
    Az alkalmazás leállítása a megadott eszközön.

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    if is_valid_ip(ip_address):
        subprocess.run(
            ['adb', '-s', ip_address, 'shell', 'am', 'force-stop', APP_PACKAGE],
            capture_output=True,
            text=True
        )
    else:
        flash('Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.', 'Hiba')


def get_device_info(ip_address: str) -> tuple[str, str]:
    """
    Az eszköz nevének és Android verziójának lekérése.

    Args:
        ip_address (str): Az eszköz IP-címe.

    Returns:
        tuple: Az eszköz neve és Android verziója.

    Raises:
        ValueError: Ha az IP cím érvénytelen.
    """
    if not is_valid_ip(ip_address):
        raise ValueError("Érvénytelen IP cím. Kérlek, adj meg egy érvényes IPv4 vagy IPv6 címet.")

    try:
        device_name = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.product.marketname'],
            encoding='utf-8'
        ).strip()

        android_version = subprocess.check_output(
            ['adb', '-s', ip_address, 'shell', 'getprop', 'ro.build.version.release'],
            encoding='utf-8'
        ).strip()

        return device_name, android_version

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Hiba történt az eszköz információinak lekérésekor: {e}") from e


# Eszközhöz való első csatlakozáskor manuálisan ki kell adni az "adb tcpip 5555" parancsot. Később esetleg lekódolni
def launch_time(ip_address: str) -> None:
    """
    Az alkalmazés indítási idejének mérése és mentése adatbázisba

    Args:
        ip_address (str): Az eszköz IP-címe.
    """
    result = subprocess.run(
        ['adb', '-s', ip_address, 'shell', 'am', 'start', '-W', f'{APP_PACKAGE}/{APP_ACTIVITY}'],
        capture_output=True,
        text=True
    )
    lines = result.stdout.splitlines()

    startup_state = next((line.split()[-1] for line in lines if 'LaunchState' in line), 'Unknown')
    startup_time = next((line.split()[-1] for line in lines if 'TotalTime' in line), '0')

    device_name, android_version = get_device_info(ip_address)

    # Mentés adatbázisba
    save_record(
        LaunchTime,
        ip_address=ip_address,
        device=device_name,
        android_version=android_version,
        application=APP_PACKAGE.split('.')[-1],
        startup_state=startup_state,
        startup_time=startup_time
    )

    time.sleep(3)

    stop_app(ip_address)


def cpu_usage(ip_address: str) -> None:
    """
    Az alkalmazás CPU használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    start_app(ip_address)

    time.sleep(10)

    result = subprocess.run(
        ['adb', '-s', ip_address, 'shell', 'dumpsys', 'cpuinfo'],
        capture_output=True,
        text=True
    )
    lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
    cpu_usage_value = lines[0].split()[0]

    device_name, android_version = get_device_info(ip_address)

    # Mentés adatbázisba
    save_record(
        CpuUsage,
        ip_address=ip_address,
        device=device_name,
        android_version=android_version,
        application = APP_PACKAGE.split('.')[-1],
        cpu_usage = cpu_usage_value
    )

    time.sleep(3)

    stop_app(ip_address)


def memory_usage(ip_address: str) -> None:
    """
    Az alkalmazás memória használatának mérése és mentése adatbázisba

    Args:
         ip_address (str): Az eszköz IP-címe.
    """
    start_app(ip_address)

    time.sleep(10)

    result = subprocess.run(
        ['adb', '-s', ip_address, 'shell', 'dumpsys', 'meminfo'],
        capture_output=True,
        text=True)
    lines = [line for line in result.stdout.splitlines() if 'youtube' in line.lower()]
    memory_usage_value = lines[0].split()[0]
    memory_usage_value = memory_usage_value[:-1]    # Az utolsó karakter levágása, ami egy ':'

    device_name, android_version = get_device_info(ip_address)

    # Mentés adatbázisba
    save_record(
        MemoryUsage,
        ip_address=ip_address,
        device=device_name,
        android_version=android_version,
        application=APP_PACKAGE.split('.')[-1],
        memory_usage=memory_usage_value
    )

    time.sleep(3)

    stop_app(ip_address)


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
        adb_connect_command = ['adb', 'connect', ip_address]
        result = subprocess.run(adb_connect_command, capture_output=True, text=True)
        if 'connected' in result.stdout.lower():
            session['ip_address'] = ip_address
            flash(f'Csatlakoztatva az eszközhöz {ip_address}.', 'Siker')
            return redirect(url_for('test'))
        else:
            flash(f'Sikertelen csatlakozás: {result.stdout or result.stderr}.', 'Hiba')
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
    if not ip_address:
        flash('Nincs kapcsolódó eszköz. Először csatlakoztasson egy eszközt.', 'hiba')
        return redirect(url_for('home'))

    test_functions = {
        'launch_time': launch_time,
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage
    }

    if form.validate_on_submit():
        selected_test = form.tests.data
        test_function = test_functions.get(selected_test)
        if test_function:
            test_function(ip_address)
    return render_template('test.html', form=form)


@app.route('/eredmenyek', methods=['GET'])
def chart():
    """
    Eredmények oldal, amely a tesztek eredményeit grafikonon jeleníti meg.

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
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
