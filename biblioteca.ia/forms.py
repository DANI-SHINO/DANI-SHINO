# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class RegisterBookForm(FlaskForm):
    isbn = StringField('ISBN (Código de Barras)', validators=[DataRequired(), Length(min=10, max=13)])
    titulo = StringField('Título', validators=[DataRequired(), Length(max=100)])
    autor = StringField('Autor', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Registrar Libro')

class BarcodeScanForm(FlaskForm):
    isbn = StringField('Escanear ISBN', validators=[DataRequired()])
    submit = SubmitField('Procesar Escaneo')
    
class RegisterFromScanForm(FlaskForm):
    isbn = StringField('ISBN escaneado', validators=[DataRequired()])
    titulo = StringField('Título', validators=[DataRequired()])
    autor = StringField('Autor', validators=[DataRequired()])
    cantidad = StringField('Cantidad de Ejemplares', validators=[DataRequired()])
    submit = SubmitField('Registrar Libro y Ejemplares')
