from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app.models import db, Usuario, Libro, Prestamo, Reserva
from app.forms import RegistroForm, LibroForm, EditarLibroForm
from functools import wraps
from app.libro import eliminar_libro, sincronizar_ejemplares, actualizar_disponibilidad_libro
from app.models import Ejemplar
from datetime import datetime
import random
import os
from werkzeug.utils import secure_filename
from time import time
from io import BytesIO


main = Blueprint('main', __name__)

login_manager = LoginManager()
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def roles_requeridos(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('main.registro'))

        nuevo_usuario = Usuario(
            username=username,
            rol='lector',
            activo=True
        )
        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso, ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('registro.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        usuario = Usuario.query.filter_by(username=username, activo=True).first()
        if usuario and usuario.check_password(password):
            login_user(usuario)
            flash('Has iniciado sesión.', 'success')

            if usuario.rol == 'administrador':
                    return redirect(url_for('main.inicio'))
            elif usuario.rol == 'bibliotecario':
                    return redirect(url_for('main.gestion'))
            elif usuario.rol == 'lector':
                    return redirect(url_for('main.lectores'))
            else:
                    return redirect(url_for('main.index'))

    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('main.index'))

@main.route('/usuarios')
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def lista_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@main.route('/usuarios/<int:usuario_id>/toggle', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def toggle_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.username == 'admin':
        flash('No se puede desactivar al administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    if current_user.rol == 'bibliotecario' and usuario.rol == 'administrador':
        flash('No tienes permiso para modificar a un administrador.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f"El usuario '{usuario.username}' ha sido {estado}.", 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/usuarios/<int:usuario_id>/cambiar_rol', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def cambiar_rol(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.username == 'admin':
        flash('No se puede cambiar el rol del administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    nuevo_rol = request.form.get('rol')
    roles_permitidos = ['lector', 'bibliotecario']

    if nuevo_rol not in roles_permitidos:
        flash('Solo puedes cambiar roles entre lector y bibliotecario.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash(f"El rol del usuario '{usuario.username}' ha sido cambiado a {nuevo_rol}.", 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/admin/inicio', endpoint='inicio')
@login_required
@roles_requeridos('administrador')
def admin_inicio():
    return render_template('admin.html', version=time())

@main.route('/admin/inicio-contenido')
@login_required
@roles_requeridos('administrador')
def inicio_contenido():
    total_administradores = Usuario.query.filter_by(rol='administrador').count()
    total_lectores = Usuario.query.filter_by(rol='lector').count()
    total_libros = Libro.query.count()
    total_prestamos = Prestamo.query.count() if 'Prestamo' in globals() else 0
    total_reservas = Reserva.query.count() if 'Reserva' in globals() else 0


    return render_template('inicio.html',
        total_administradores=total_administradores,
        total_lectores=total_lectores,
        total_libros=total_libros,
        total_prestamos=total_prestamos,
        total_reservas=total_reservas,

    )

@main.route('/api/dashboard_data')
@login_required
@roles_requeridos('administrador')
def dashboard_data():
    data = {
        'total_administradores': Usuario.query.filter_by(rol='administrador').count(),
        'total_lectores': Usuario.query.filter_by(rol='lector').count(),
        'total_libros': Libro.query.count(),
        'total_prestamos': Prestamo.query.count() if 'Prestamo' in globals() else 0,
        'total_reservas': Reserva.query.count() if 'Reserva' in globals() else 0,

    }
    return jsonify(data)

@main.route('/admin/usuarios')
@login_required
@roles_requeridos('administrador')
def admin_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@main.route('/admin/libros')
@login_required
@roles_requeridos('administrador')
def admin_libros():
    libros = Libro.query.all()
    return render_template('libros.html', libros=libros)

@main.route('/admin/prestamos')
@login_required
@roles_requeridos('administrador')
def admin_prestamos():
    return render_template('prestamos.html')

@main.route('/admin/reservas')
@login_required
@roles_requeridos('administrador')
def admin_reservas():
    return render_template('reservas.html')

@main.route('/admin/reportes')
@login_required
@roles_requeridos('administrador')
def admin_reportes():
    return render_template('reportes.html')


@main.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    usuario = Usuario.query.get(current_user.id)

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        archivo = request.files.get('foto_perfil')

        if nombre:
            usuario.username = nombre  # Cambia esto si usas otro campo para el nombre
        if correo:
            usuario.correo = correo

        if archivo and archivo.filename != '':
            # Guardar la nueva imagen
            filename = secure_filename(archivo.filename)
            extension = os.path.splitext(filename)[1]
            nuevo_nombre = f"user_{usuario.id}{extension}"
            ruta_guardado = os.path.join(current_app.root_path, 'static', 'fotos_perfil', nuevo_nombre)
            archivo.save(ruta_guardado)

            usuario.foto = nuevo_nombre

        db.session.commit()
        flash("Perfil actualizado correctamente", "success")
        return redirect(url_for('main.configuracion'))

    return render_template('configuracion.html', usuario=usuario)


@main.route('/lectores')
@login_required
@roles_requeridos('lector')
def lectores():
    return render_template('lectores.html')  

@main.route('/catalogo')
@login_required
def catalogo():
    libros = Libro.query.all()
    return render_template('catalogo.html', libros=libros)

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')  # Si usas roles
def mostrar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)



@main.route("/admin/usuarios/editar", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def editar_usuario():
    datos = request.get_json()
    usuario = Usuario.query.get(datos["id"])
    usuario.nombre = datos["nombre"]
    usuario.email = datos["email"]
    usuario.rol = datos["rol"]
    db.session.commit()
    return jsonify({"mensaje": "Usuario actualizado"})

@main.route("/admin/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario eliminado"})

@main.route('/admin/libros/nuevo', methods=['GET', 'POST'])
@roles_requeridos('administrador', 'bibliotecario')
@login_required
def nuevo_libro():
    form = LibroForm()
    if form.validate_on_submit():
        isbn_base = form.isbn_base.data.strip() if form.isbn_base.data else ''

        # Generar isbn_base si viene vacío o no se envió
        if not isbn_base:
            ultimo_libro = Libro.query.order_by(Libro.id.desc()).first()
            if ultimo_libro and ultimo_libro.isbn_base and ultimo_libro.isbn_base.isdigit():
                nuevo_isbn_base = str(int(ultimo_libro.isbn_base) + 1)
            else:
                nuevo_isbn_base = "1000"  # Valor inicial por defecto
            isbn_base = nuevo_isbn_base

        nuevo_libro = Libro(
            titulo=form.titulo.data,
            autor=form.autor.data,
            isbn_base=isbn_base,
            descripcion=form.descripcion.data,
            disponible=bool(int(form.disponible.data)),
            fecha_creacion=datetime.now(),
            categoria=form.categoria.data,
            cantidad_total=form.cantidad_total.data,
            cantidad_disponible=0,  # se actualizará luego
            fecha_publicacion=form.fecha_publicacion.data,
            editorial=form.editorial.data
        )

        db.session.add(nuevo_libro)
        db.session.flush()  # Necesario para obtener el ID antes de crear ejemplares

        # Crear ejemplares con ISBN único basado en isbn_base
        cantidad = form.cantidad_total.data or 0
        for i in range(cantidad):
            nuevo_isbn = Ejemplar.generar_isbn_unico(nuevo_libro)
            ejemplar = Ejemplar(
                libro=nuevo_libro,
                isbn=nuevo_isbn,
                estado='disponible'
            )
            db.session.add(ejemplar)

        # Actualizar disponibilidad
        nuevo_libro.cantidad_disponible = cantidad

        db.session.commit()
        flash('Libro y ejemplares agregados correctamente.', 'success')
        return render_template('nuevo_libro.html', form=form)

    return render_template('nuevo_libro.html', form=form)


@main.route('/admin/libros/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_libros():
    libros = Libro.query.all()
    return render_template('libros_tabla.html', libros=libros)


@main.route('/admin/libros/eliminar/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def eliminar_libro(libro_id):
    mensaje = eliminar_libro(libro_id)
    if mensaje.startswith("Libro marcado"):
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'warning')
    return redirect(url_for('main.mostrar_libros'))


@main.route('/admin/libros/editar/<int:libro_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def editar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    form = EditarLibroForm(obj=libro)

    if form.validate_on_submit():
        nueva_cantidad_total = form.cantidad_total.data

        # Intentar sincronizar ejemplares antes de cambiar valores
        if not sincronizar_ejemplares(libro, nueva_cantidad_total):
            flash("No se puede reducir la cantidad: hay ejemplares en préstamo.", "danger")
            return redirect(url_for('main.editar_libro', libro_id=libro_id))

        libro.titulo = form.titulo.data
        libro.autor = form.autor.data
        libro.categoria = form.categoria.data
        libro.cantidad_total = nueva_cantidad_total
        libro.descripcion = form.descripcion.data
        libro.editorial = form.editorial.data
        libro.fecha_publicacion = form.fecha_publicacion.data

        # Actualizar cantidad_disponible en base a ejemplares
        actualizar_disponibilidad_libro(libro)

        db.session.commit()
        flash('Libro editado exitosamente.', 'success')
        return redirect(url_for('main.admin_libros'))

    return render_template('editar_libro.html', form=form, libro=libro)




@main.route('/admin/reservas/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_reserva():
    datos = request.get_json()
    print('Reserva recibida:', datos)
    # Guardar en tabla si tienes el modelo Reserva
    return jsonify({'mensaje': 'Reserva realizada correctamente'})

@main.route('/admin/prestamos/guardar', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def guardar_prestamo():
    datos = request.get_json()
    print('Préstamo recibido:', datos)
    # Guardar en tabla si tienes el modelo Prestamo
    return jsonify({'mensaje': 'Préstamo registrado correctamente'})


# en routes.py
@main.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        usuario = Usuario.query.get(current_user.id)
        usuario.nombre = request.form['nombre']
        usuario.correo = request.form['correo']

        # Si hay una nueva foto de perfil
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file.filename != '':
                filename = secure_filename(file.filename)
                ruta_carpeta = os.path.join('static', 'imagenes', 'perfil')
                os.makedirs(ruta_carpeta, exist_ok=True)  # Crea carpeta si no existe
                filepath = os.path.join(ruta_carpeta, filename)
                file.save(filepath)
                usuario.foto = f'imagenes/perfil/{filename}'

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('main.perfil'))

    return render_template('perfil.html', usuario=current_user)

@main.route('/foto_perfil')
@login_required
def foto_perfil():
    if current_user.foto:
        ruta = os.path.join('static', current_user.foto.replace('/', os.sep))
        if os.path.exists(ruta):
            return send_file(ruta, mimetype='image/jpeg')
    
    # Si no tiene foto, o no existe el archivo
    return redirect(url_for('static', filename='imagenes/perfil/default.png'))
