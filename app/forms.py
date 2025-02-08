import logging

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

from utils import validate_ip

# Logger inicializálása
logger = logging.getLogger(__name__)


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
    try:
        tests = SelectField(
            'Select an option:',
            choices=[
                ('launch_time', 'Indítási idő'),
                ('cpu_usage', 'CPU'),
                ('memory_usage', 'Memória')
            ],
            validators=[DataRequired()]
        )
        submit = SubmitField('Küldés')

        logger.info("TestForm sikeresen inicializálva.")

    except Exception as e:
        logger.error(f"Hiba történt a TestForm létrehozásakor: {e}", exc_info=True)
        raise RuntimeError("Nem sikerült a form inicializálása.") from e