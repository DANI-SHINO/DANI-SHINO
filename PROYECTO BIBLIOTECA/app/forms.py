from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, SubmitField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError, Optional, NumberRange, Email
from app.models import Usuario
from datetime import date

class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=50)])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    documento = StringField('Número de Documento', validators=[DataRequired(), Length(min=5, max=20)])
    direccion = StringField('Dirección', validators=[DataRequired(), Length(min=5, max=100)])
    telefono = StringField('Teléfono', validators=[DataRequired(), Length(min=7, max=20)])
    fecha_nacimiento = DateField('Fecha de Nacimiento', format='%Y-%m-%d', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$', message='Debe contener letras y números.')
    ])

    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])

    submit = SubmitField('Registrarse')

    def validate_correo(self, correo):
        if Usuario.query.filter_by(correo=correo.data).first():
            raise ValidationError('Ya existe una cuenta con este correo.')

    def validate_documento(self, documento):
        if Usuario.query.filter_by(documento=documento.data).first():
            raise ValidationError('Ya existe una cuenta con este número de documento.')

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
    fecha_publicacion = DateField('Fecha de Publicación', format='%Y-%m-%d', validators=[Optional()])
    cantidad_total = IntegerField('Cantidad Total', validators=[DataRequired(), NumberRange(min=0)])
    portada_url = HiddenField('URL de Portada', validators=[Optional()])
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
    cantidad_total = IntegerField("Cantidad Total", validators=[Optional(), NumberRange(min=0)])
    cantidad_disponible = IntegerField("Cantidad Disponible", validators=[Optional(), NumberRange(min=0)])
    fecha_publicacion = DateField("Fecha de Publicación", format='%Y-%m-%d', validators=[Optional()])
    editorial = StringField("Editorial", validators=[Optional()])
    portada_url = HiddenField('URL de Portada', validators=[Optional()])
    submit = SubmitField("Guardar cambios")

class PrestamoForm(FlaskForm):
    llave_prestamo = StringField("Llave de préstamo", validators=[
        DataRequired(),
        Length(min=7, max=7, message="La llave debe tener el formato XXX-XXX (7 caracteres)")
    ])
    libro_id = SelectField("Libro", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Guardar")

class NuevaReservaForm(FlaskForm):
    llave_prestamo = StringField("Llave de préstamo", validators=[
        DataRequired(),
        Length(min=7, max=7, message="La llave debe tener el formato XXX-XXX")
    ])
    libro_id = SelectField("Libro", coerce=int, validators=[DataRequired()])
    fecha_expiracion = DateField("Fecha Expiración", format='%Y-%m-%d')
    submit = SubmitField("Guardar")


class EditarReservaForm(FlaskForm):
    usuario_id = SelectField('Usuario', coerce=int, validators=[DataRequired()])
    libro_id = SelectField('Libro', coerce=int, validators=[DataRequired()])
    fecha_expiracion = DateField('Fecha de Expiración', format='%Y-%m-%d', validators=[DataRequired()])
    estado = SelectField('Estado', choices=[
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
        ('confirmada', 'Confirmada')
    ], validators=[DataRequired()])
    submit = SubmitField('Guardar cambios')
