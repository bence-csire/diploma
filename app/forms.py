from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

from validation import validate_ip


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
    tests = SelectField(
        'Válassz tesztet:',
        choices=[
            ('storage_usage', 'Tárhelyhasználat'),
            ('cpu_memory_usage', 'CPU és Memória'),
            ('uptime', 'Futási Idő'),
            ('bad_frames', 'Hibás framek'),
            ('all_tests', 'Összes teszt')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Küldés')
