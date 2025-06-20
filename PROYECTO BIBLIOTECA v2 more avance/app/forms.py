from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError, Optional, NumberRange, Email
from app.models import Usuario
from datetime import date

class RegistroForm(FlaskForm):
    username = StringField('Nombre de usuario', validators=[DataRequired(), Length(min=4, max=25)])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])  # NUEVO
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$', message='La contraseña debe ser alfanumérica (letras y números).')
    ])
    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    submit = SubmitField('Registrarse')

    def validate_username(self, username):
        usuario = Usuario.query.filter_by(username=username.data).first()
        if usuario:
            raise ValidationError('El nombre de usuario ya está en uso. Por favor elige otro.')
        
    def validate_correo(self, correo):
        usuario = Usuario.query.filter_by(correo=correo.data).first()
        if usuario:
            raise ValidationError('Ya existe una cuenta con este correo electrónico.')

class LibroForm(FlaskForm):
    isbn = StringField('ISBN', validators=[DataRequired()])
    titulo = StringField('Título', validators=[DataRequired()])
    autor = StringField('Autor', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    categoria = SelectField(
        'Categoría',
        choices=[
            ('novela', 'Novela'),
            ('filosofia', 'Filosofía'),
            ('poesia', 'Poesía'),
            ('teatro', 'Teatro'),
            ('ensayo', 'Ensayo'),
            ('cronica', 'Crónica'),
            ('historieta', 'Historieta'),
            ('biografia', 'Biografía'),
            ('cuento', 'Cuento'),
            ('audiolibro', 'Audiolibro')
        ],
        validators=[DataRequired()]
    )
    editorial = StringField('Editorial')
    fecha_publicacion = DateField(
        'Fecha de Publicación',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    cantidad_total = IntegerField(
        'Cantidad Total',
        validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField('Guardar')

class EditarLibroForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired()])
    autor = StringField("Autor", validators=[DataRequired()])
    descripcion = TextAreaField("Descripción", validators=[Optional()])
    categoria = SelectField(
        "Categoría",
        choices=[
            ('novela', 'Novela'),
            ('filosofia', 'Filosofía'),
            ('poesia', 'Poesía'),
            ('teatro', 'Teatro'),
            ('ensayo', 'Ensayo'),
            ('cronica', 'Crónica'),
            ('historieta', 'Historieta'),
            ('biografia', 'Biografía'),
            ('cuento', 'Cuento'),
            ('audiolibro', 'Audiolibro')
        ],
        validators=[DataRequired()]
    )
    cantidad_total = IntegerField(
        "Cantidad Total",
        validators=[Optional(), NumberRange(min=0)]
    )
    cantidad_disponible = IntegerField(
        "Cantidad Disponible",
        validators=[Optional(), NumberRange(min=0)]
    )
    fecha_publicacion = DateField(
        "Fecha de Publicación",
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    editorial = StringField(
        "Editorial",
        validators=[Optional()]
    )
    submit = SubmitField("Guardar cambios")

