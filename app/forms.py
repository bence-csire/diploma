from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired

from utils import validate_ip


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