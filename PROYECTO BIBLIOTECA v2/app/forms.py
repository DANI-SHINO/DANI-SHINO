from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError, Optional, NumberRange
from app.models import Usuario
from datetime import date

class RegistroForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$', message='La contraseña debe ser alfanumérica (letras y números).')
    ])
    confirmar_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    submit = SubmitField('Registrarse')

    def validate_username(self, username):
        usuario = Usuario.query.filter_by(username=username.data).first()
        if usuario:
            raise ValidationError('El nombre de usuario ya está en uso. Por favor elige otro.')

class LibroForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired()])
    autor = StringField("Autor", validators=[DataRequired()])
    isbn_base = StringField("ISBN Base", validators=[Optional()])
    descripcion = TextAreaField("Descripción", validators=[Optional()])
    disponible = SelectField("¿Disponible?", choices=[("1", "Sí"), ("0", "No")], validators=[DataRequired()])
    fecha_creacion = StringField("Fecha de Creación", default=date.today().strftime('%Y-%m-%d'), validators=[Optional()])
    categoria = StringField("Categoría", validators=[Optional()])
    cantidad_total = IntegerField("Cantidad Total", validators=[Optional(), NumberRange(min=0)])
    cantidad_disponible = IntegerField("Cantidad Disponible", validators=[Optional(), NumberRange(min=0)])
    fecha_publicacion = DateField("Fecha de Publicación", format='%Y-%m-%d', validators=[Optional()])
    editorial = StringField("Editorial", validators=[Optional()])
    
    # Nuevo campo para indicar cuántos ejemplares generar automáticamente
    cantidad = IntegerField("Cantidad de ejemplares", validators=[Optional(), NumberRange(min=1, message="Debe ser al menos 1")])
    
    submit = SubmitField("Guardar")

class EditarLibroForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired()])
    autor = StringField("Autor", validators=[DataRequired()])
    descripcion = TextAreaField("Descripción", validators=[Optional()])
    categoria = StringField("Categoría", validators=[Optional()])
    cantidad_total = IntegerField("Cantidad Total", validators=[Optional(), NumberRange(min=0)])
    cantidad_disponible = IntegerField("Cantidad Disponible", validators=[Optional(), NumberRange(min=0)])
    fecha_publicacion = DateField("Fecha de Publicación", format='%Y-%m-%d', validators=[Optional()])
    editorial = StringField("Editorial", validators=[Optional()])
    submit = SubmitField("Guardar cambios")
