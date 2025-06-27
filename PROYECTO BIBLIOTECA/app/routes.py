from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import extract, func
from time import time
from datetime import timedelta, date
import os
import requests
# Importa las extensiones correctamente
from app.extensions import db, login_manager, mail
from app.models import Usuario, Libro, Prestamo, Reserva, Favorito
from app.forms import RegistroForm, LibroForm, EditarLibroForm, EditarReservaForm, NuevaReservaForm, PrestamoForm
from app.utils import verificar_token, generar_token, generar_llave_prestamo
from app.libro import prestar_libro, devolver_libro



main = Blueprint('main', __name__)
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
    return render_template('login.html')

@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        # Obtener todos los datos del formulario
        nombre = form.nombre.data
        apellido = form.apellido.data
        correo = form.correo.data
        documento = form.documento.data
        direccion = form.direccion.data
        telefono = form.telefono.data
        fecha_nacimiento = form.fecha_nacimiento.data
        password = form.password.data

        # Validar duplicados extra (opcional, ya validado en form)
        if Usuario.query.filter_by(correo=correo).first():
            flash('Correo no disponible.', 'danger')
            return redirect(url_for('main.registro'))
        if Usuario.query.filter_by(documento=documento).first():
            flash('Número de documento ya registrado.', 'danger')
            return redirect(url_for('main.registro'))

        # Crear usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            documento=documento,
            direccion=direccion,
            telefono=telefono,
            fecha_nacimiento=fecha_nacimiento,
            rol='lector',
            activo=True
        )

        # Generar llave_prestamo de préstamo y contraseña
        nuevo_usuario.generar_llave_prestamo()
        nuevo_usuario.set_password(password)

        # Guardar en base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('registro.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(correo=correo, activo=True).first()
        if usuario and usuario.check_password(password):
            login_user(usuario)
            flash('Has iniciado sesión.', 'success')

            if usuario.rol == 'administrador':
                    return redirect(url_for('main.inicio'))
            elif usuario.rol == 'bibliotecario':
                    return redirect(url_for('main.gestion'))
            elif usuario.rol == 'lector':
                    return redirect(url_for('main.catalogo'))
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

    if usuario.nombre == 'admin':
        flash('No se puede desactivar al administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    if current_user.rol == 'bibliotecario' and usuario.rol == 'administrador':
        flash('No tienes permiso para modificar a un administrador.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.activo = not usuario.activo
    db.session.commit()

    estado = 'activado' if usuario.activo else 'desactivado'
    flash(f"El usuario '{usuario.nombre}' ha sido {estado}.", 'success')
    return redirect(url_for('main.lista_usuarios'))

@main.route('/usuarios/<int:usuario_id>/cambiar_rol', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def cambiar_rol(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.nombre == 'admin':
        flash('No se puede cambiar el rol del administrador principal.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    nuevo_rol = request.form.get('rol')
    roles_permitidos = ['lector', 'bibliotecario']

    if nuevo_rol not in roles_permitidos:
        flash('Solo puedes cambiar roles entre lector y bibliotecario.', 'error')
        return redirect(url_for('main.lista_usuarios'))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash(f"El rol del usuario '{usuario.nombre}' ha sido cambiado a {nuevo_rol}.", 'success')
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


@main.route('/api/datos_libro/<isbn>')
def api_datos_libro(isbn):
    # Busca en OpenLibrary
    ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    response = requests.get(ol_url)
    data = response.json()

    portada_url = None # Inicializa la URL de la portada

    if f"ISBN:{isbn}" in data:
        libro = data[f"ISBN:{isbn}"]
        titulo = libro.get('title', '')
        autores = ', '.join(a['name'] for a in libro.get('authors', []))
        editorial = ', '.join(p['name'] for p in libro.get('publishers', [])) if 'publishers' in libro else ''
        fecha = libro.get('publish_date', None)

        # 🖼️ Obtener la URL de la portada
        if 'cover' in libro and 'large' in libro['cover']:
            portada_url = libro['cover']['large']
        elif 'cover' in libro and 'medium' in libro['cover']:
            portada_url = libro['cover']['medium']
        elif 'cover' in libro and 'small' in libro['cover']:
            portada_url = libro['cover']['small']
        # Si no hay cover en la data, se puede intentar con el API de Covers
        elif isbn:
            portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
            # Puedes incluso verificar si la imagen existe antes de enviarla
            # response_cover = requests.head(portada_url)
            # if not response_cover.ok:
            #     portada_url = None # O una URL de imagen por defecto

        return jsonify({
            "success": True,
            "titulo": titulo,
            "autor": autores,
            "editorial": editorial,
            "fecha_publicacion": fecha,
            "isbn": isbn,
            "portada_url": portada_url # Devolver la URL de la portada
        })

    return jsonify({"success": False})



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
@roles_requeridos('administrador', 'bibliotecario')
def admin_libros():
    # solo los que NO esten eliminados
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
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
        apellido = request.form.get('apellido')
        correo = request.form.get('correo')
        archivo = request.files.get('foto_perfil')

        if nombre:
            usuario.nombre = nombre
        if apellido:
            usuario.apellido = apellido
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



@main.route('/catalogo')
@login_required
def catalogo():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    # Para los lectores, podríamos querer información adicional como si el libro está en sus favoritos
    favoritos_ids = []
    if current_user.is_authenticated:
        if current_user.rol == 'lector':
            favoritos_ids = [f.libro_id for f in current_user.favoritos]

    return render_template('catalogo.html', libros=libros, favoritos_ids=favoritos_ids)

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)

# En routes.py
@main.route('/admin/usuarios/agregar')
@login_required
@roles_requeridos('administrador')
def agregar_usuario():
    form = RegistroForm()
    return render_template('registro_fragmento.html', form=form)

@main.route('/admin/usuarios/editar_formulario/<int:id>')
@login_required
@roles_requeridos('administrador')
def editar_formulario_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    return render_template('partials/usuarios_editar.html', usuario=usuario)


@main.route("/admin/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@roles_requeridos('administrador')
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario eliminado"})


@main.route('/admin/libros/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def nuevo_libro():
    form = LibroForm()
    isbn_param = request.args.get('isbn')
    if isbn_param and request.method == 'GET':
        # Rellenar automáticamente desde OpenLibrary
        resp = requests.get(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_param}&format=json&jscmd=data")
        data = resp.json().get(f"ISBN:{isbn_param}", {})
        form.isbn.data = isbn_param
        form.titulo.data = data.get('title', '')
        form.autor.data = ', '.join([a['name'] for a in data.get('authors', [])]) if data.get('authors') else ''
        form.editorial.data = ', '.join([p['name'] for p in data.get('publishers', [])]) if data.get('publishers') else ''

        # 📖 Añadir la descripción si existe
        description = data.get('description')
        if isinstance(description, dict):
            form.descripcion.data = description.get('value', '')
        elif isinstance(description, str):
            form.descripcion.data = description
        else:
            form.descripcion.data = ''

        raw_date = data.get('publish_date', '')
        if raw_date:
            try:
                if len(raw_date) == 4 and raw_date.isdigit():
                    raw_date = f"{raw_date}-01-01"
                form.fecha_publicacion.data = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                form.fecha_publicacion.data = None

        # 🖼️ Obtener la URL de la portada y rellenar el formulario
        portada_url = None
        if 'cover' in data and 'large' in data['cover']:
            portada_url = data['cover']['large']
        elif 'cover' in data and 'medium' in data['cover']:
            portada_url = data['cover']['medium']
        elif 'cover' in data and 'small' in data['cover']:
            portada_url = data['cover']['small']
        elif isbn_param:
            portada_url = f"https://covers.openlibrary.org/b/isbn/{isbn_param}-L.jpg?default=false"
            try:
                check_resp = requests.head(portada_url)
                if not check_resp.ok:
                    portada_url = None
            except requests.exceptions.RequestException:
                portada_url = None

        form.portada_url.data = portada_url # Asignar la URL al campo del formulario

    if form.validate_on_submit():
        isbn = form.isbn.data
        libro_existente = Libro.query.filter_by(isbn=isbn).first()
        if libro_existente:
            flash('Ya existe un libro con ese ISBN.', 'danger')
        else:
            cantidad_total = form.cantidad_total.data or 0
            nuevo_libro = Libro(
                isbn=isbn,
                titulo=form.titulo.data,
                autor=form.autor.data,
                descripcion=form.descripcion.data,
                categoria=form.categoria.data,
                editorial=form.editorial.data,
                fecha_publicacion=form.fecha_publicacion.data,
                cantidad_total=cantidad_total,
                cantidad_disponible=cantidad_total,
                portada_url=form.portada_url.data # Guardar la URL de la portada
            )
            nuevo_libro.actualizar_estado()

            db.session.add(nuevo_libro)
            db.session.commit()

            flash('Libro creado exitosamente.', 'success')
            return redirect(url_for('main.admin_libros'))

    return render_template('nuevo_libro.html', form=form)


@main.route('/admin/libros/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_libros():
    libros = Libro.query.filter(Libro.estado != 'eliminado').all()
    return render_template('libros_tabla.html', libros=libros)


@main.route('/admin/libros/eliminar/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def eliminar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    # Solo eliminamos si no hay préstamos activos
    if libro.cantidad_disponible < libro.cantidad_total:
        flash('No se puede eliminar: hay ejemplares prestados.', 'danger')
        return redirect(url_for('main.admin_libros'))

    libro.marcar_como_eliminado()
    db.session.commit()
    flash('Libro marcado como eliminado.', 'success')
    return redirect(url_for('main.admin_libros'))



@main.route('/admin/libros/editar/<int:libro_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def editar_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    form = EditarLibroForm(obj=libro)

    if form.validate_on_submit():
        # Nueva cantidad total y cantidad disponible del formulario
        nueva_cantidad_total = form.cantidad_total.data
        nueva_cantidad_disponible = form.cantidad_disponible.data

        # Validar que la cantidad disponible nunca sea mayor que la cantidad total
        if nueva_cantidad_disponible > nueva_cantidad_total:
            flash("La cantidad disponible no puede ser mayor que la cantidad total.", "danger")
            return redirect(url_for('main.editar_libro', libro_id=libro_id))

        # Actualizar campos del libro
        libro.titulo = form.titulo.data
        libro.autor = form.autor.data
        libro.categoria = form.categoria.data
        libro.descripcion = form.descripcion.data
        libro.editorial = form.editorial.data
        libro.fecha_publicacion = form.fecha_publicacion.data
        libro.cantidad_total = nueva_cantidad_total
        libro.cantidad_disponible = nueva_cantidad_disponible
        libro.disponible = nueva_cantidad_total > 0  # Disponible solo si hay al menos un ejemplar

        # Guardar cambios
        db.session.commit()
        flash('Libro editado exitosamente.', 'success')
        return redirect(url_for('main.admin_libros'))

    return render_template('editar_libro.html', form=form, libro=libro)

@main.route('/admin/libros/scan', methods=['GET'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def escanear_libro():
    return render_template('escanear_libro.html')

@main.route('/admin/reservas/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador')
def reservas_agregar():
    form = NuevaReservaForm()

    # Solo libro es selección manual
    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.all()]

    # Prellenar fecha expiración
    if request.method == 'GET':
       form.fecha_expiracion.data = date.today() + timedelta(days=7)

    if form.validate_on_submit():
        # Recuperar usuario_id directo del input oculto
        usuario_id = request.form.get('usuario_id')
        usuario = Usuario.query.get(usuario_id)

        # Validar que exista y que la llave_prestamo coincida
        if form.validate_on_submit():
            usuario = Usuario.query.filter_by(llave_prestamo=form.llave_prestamo.data).first()
            if not usuario:
                flash('Llave incorrecta.', 'danger')
                return redirect(url_for('main.reservas_tabla'))
        # Registrar reserva
        nueva_reserva = Reserva(
            usuario_id=usuario.id,
            libro_id=form.libro_id.data,
            fecha_expiracion=date.today() + timedelta(days=7),
            estado='activa'
        )
        db.session.add(nueva_reserva)
        db.session.commit()
        flash('Reserva registrada correctamente.', 'success')
        return redirect(url_for('main.reservas_tabla'))

    return render_template('reservas_agregar.html', form=form)





@main.route('/admin/reservas/editar/<int:reserva_id>', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador')
def editar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    form = EditarReservaForm(obj=reserva)

    # ⚠️ Importante: cargar las opciones para los select
    form.usuario_id.choices = [(u.id, u.nombre) for u in Usuario.query.order_by(Usuario.nombre).all()]
    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.order_by(Libro.titulo).all()]

    if request.method == 'GET':
        # Setear valores actuales para que los campos select se muestren correctamente
        form.usuario_id.data = reserva.usuario_id
        form.libro_id.data = reserva.libro_id

    if form.validate_on_submit():
        reserva.usuario_id = form.usuario_id.data
        reserva.libro_id = form.libro_id.data
        reserva.fecha_expiracion = form.fecha_expiracion.data
        reserva.estado = form.estado.data
        db.session.commit()
        flash('✅ Reserva actualizada correctamente.', 'success')
        return redirect(url_for('main.reservas_tabla'))

    return render_template('editar_reserva.html', form=form, reserva=reserva)



@main.route('/admin/reservas/eliminar/<int:reserva_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def eliminar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    # Devolver disponibilidad solo si la reserva estaba activa
    libro = Libro.query.get(reserva.libro_id)
    if libro and reserva.estado == 'activa':
        libro.cantidad_disponible += 1

    db.session.delete(reserva)
    db.session.commit()
    flash(f'🗑️ Reserva #{reserva.id} eliminada correctamente.', 'success')
    return redirect(url_for('main.reservas_tabla'))


@main.route('/admin/reservas/prestar/<int:reserva_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador')
def prestar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    if reserva.estado != 'activa':
        flash('⚠️ Solo se pueden prestar reservas activas.', 'warning')
        return redirect(url_for('main.reservas_tabla'))

    libro = Libro.query.get(reserva.libro_id)
    if not libro or libro.cantidad_disponible <= 0:
        flash('❌ El libro no está disponible para préstamo.', 'danger')
        return redirect(url_for('main.reservas_tabla'))

    # Validar si ya tiene un préstamo activo del mismo libro
    prestamo_existente = Prestamo.query.filter_by(
        usuario_id=reserva.usuario_id,
        libro_id=reserva.libro_id,
        estado='activo'
    ).first()
    if prestamo_existente:
        flash('⚠️ Este usuario ya tiene un préstamo activo de este libro.', 'warning')
        return redirect(url_for('main.reservas_tabla'))

    nuevo_prestamo = Prestamo(
        usuario_id=reserva.usuario_id,
        libro_id=reserva.libro_id,
        fecha_prestamo=datetime.now().date(),
        fecha_devolucion_esperada=(datetime.now() + timedelta(days=7)).date(),
        estado='activo'
    )
    db.session.add(nuevo_prestamo)

    reserva.estado = 'confirmada'
    libro.cantidad_disponible -= 1
    db.session.commit()

    flash(f'📚 Préstamo creado desde reserva #{reserva.id}.', 'success')
    return redirect(url_for('main.reservas_tabla'))


@main.route('/admin/reservas/mostrar')
@login_required
@roles_requeridos('administrador')
def reservas_tabla():
    reservas = Reserva.query.all()
    return render_template('reservas_tabla.html', reservas=reservas)

@main.route('/admin/prestamos/nuevo', methods=['GET', 'POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def nuevo_prestamo():
    form = PrestamoForm()

    # ⚡ Llena libros disponibles antes de validar
    form.libro_id.choices = [(l.id, l.titulo) for l in Libro.query.filter(Libro.cantidad_disponible > 0).all()]

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(llave_prestamo=form.llave_prestamo.data).first()
        if not usuario:
            flash('Llave incorrecta.', 'danger')
            return redirect(url_for('main.nuevo_prestamo'))

        libro = Libro.query.get(form.libro_id.data)
        if libro and libro.cantidad_disponible > 0:
            nuevo_prestamo = Prestamo(
                usuario_id=usuario.id,
                libro_id=libro.id,
                fecha_prestamo=datetime.now().date(),
                fecha_devolucion_esperada=(datetime.now() + timedelta(days=7)).date(),
                estado='activo'
            )
            libro.cantidad_disponible -= 1
            db.session.add(nuevo_prestamo)
            db.session.commit()
            flash('Préstamo registrado correctamente.', 'success')
            return redirect(url_for('main.mostrar_prestamos'))
        else:
            flash('El libro no está disponible.', 'danger')

    return render_template('prestamos_agregar.html', form=form)





@main.route('/admin/prestamos/devolver/<int:prestamo_id>', methods=['POST'])
@login_required
@roles_requeridos('administrador', 'bibliotecario')
def devolver_prestamo(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)

    if prestamo.fecha_devolucion:
        flash('Este préstamo ya fue devuelto.', 'warning')
    else:
        prestamo.fecha_devolucion = datetime.now().date()
        prestamo.estado = 'devuelto'
        libro = Libro.query.get(prestamo.libro_id)
        if libro:
            libro.cantidad_disponible += 1
        db.session.commit()
        flash('Préstamo marcado como devuelto.', 'success')

    return redirect(url_for('main.mostrar_prestamos'))  # Asegúrate que este nombre sea correcto


@main.route('/admin/prestamos/mostrar')
@login_required
@roles_requeridos('administrador')
def mostrar_prestamos():
    prestamos = Prestamo.query.all()
    return render_template('prestamos_tabla.html', prestamos=prestamos)


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

@main.route('/libro/<int:libro_id>')
@login_required
def detalle_libro(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    es_favorito = False
    if current_user.is_authenticated and current_user.rol == 'lector':
        es_favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first() is not None
    return render_template('detalle_libro.html', libro=libro, es_favorito=es_favorito)

@main.route('/favoritos/toggle/<int:libro_id>', methods=['POST'])
@login_required
@roles_requeridos('lector')
def toggle_favorito(libro_id):
    libro = Libro.query.get_or_404(libro_id)
    favorito = Favorito.query.filter_by(usuario_id=current_user.id, libro_id=libro.id).first()

    if favorito:
        db.session.delete(favorito)
        flash('Libro eliminado de tus favoritos.', 'info')
    else:
        nuevo_favorito = Favorito(usuario_id=current_user.id, libro_id=libro.id)
        db.session.add(nuevo_favorito)
        flash('Libro añadido a tus favoritos.', 'success')

    db.session.commit()
    return redirect(url_for('main.detalle_libro', libro_id=libro.id))

@main.route('/mis_libros')
@login_required
@roles_requeridos('lector')
def mis_libros():
    # Obtener préstamos activos del usuario
    mis_prestamos = Prestamo.query.filter_by(usuario_id=current_user.id, estado='prestado').all()
    # Obtener reservas activas del usuario
    mis_reservas = Reserva.query.filter_by(usuario_id=current_user.id, estado='activa').all()
    # Obtener favoritos del usuario
    mis_favoritos = Favorito.query.filter_by(usuario_id=current_user.id).all()

    return render_template('mis_libros.html',
                           prestamos=mis_prestamos,
                           reservas=mis_reservas,
                           favoritos=mis_favoritos)

@main.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        correo = request.form['correo']
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            token = generar_token(usuario.correo)
            link = url_for('main.restablecer', token=token, _external=True)

            msg = Message('Recuperar contraseña', sender='noreply@biblioteca.com', recipients=[usuario.correo])
            msg.body = (
                        f'Estimado usuario,\n\n'
                        f'Hemos recibido una solicitud para restablecer la contraseña de su cuenta de biblioteca avocado.\n'
                        f'Para continuar con el proceso, por favor haga clic en el siguiente enlace:\n\n'
                        f'{link}\n\n'
                        f'Si usted no solicitó este cambio, puede ignorar este mensaje.\n\n'
                        f'Atentamente,\n'
                        f'El equipo de la Biblioteca'
                    )

            mail.send(msg)

            flash('Te enviamos un correo para recuperar tu contraseña.', 'info')
        else:
            flash('Correo no encontrado.', 'danger')
    return render_template('recuperar.html')

@main.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    email = verificar_token(token)
    if not email:
        flash('El enlace es inválido o ha expirado.', 'danger')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        nueva_pass = request.form['password']
        usuario = Usuario.query.filter_by(correo=email).first()
        if usuario:
            usuario.set_password(nueva_pass)
            db.session.commit()
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('main.login'))
    return render_template('restablecer.html')

@main.route('/admin/usuarios/mostrar')
@login_required
@roles_requeridos('administrador')
def usuarios_modal():
    usuarios = Usuario.query.all()
    return render_template('usuarios_mostrar.html', usuarios=usuarios)


@main.route('/api/prestamos_mes')
@login_required
@roles_requeridos('administrador')
def prestamos_por_mes():
    resultados = db.session.query(
        extract('month', Prestamo.fecha_prestamo).label('mes'),
        func.count().label('total')
    ).group_by('mes').order_by('mes').all()

    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return jsonify([
        {'mes': meses[int(r.mes) - 1], 'total': r.total}
        for r in resultados
    ])

@main.route('/api/libros_populares')
@login_required
@roles_requeridos('administrador')
def libros_populares():
    resultados = db.session.query(
        Libro.titulo,
        func.count(Prestamo.id).label('total')
    ).join(Prestamo).group_by(Libro.id).order_by(func.count(Prestamo.id).desc()).limit(5).all()

    return jsonify([{'titulo': r.titulo, 'total': r.total} for r in resultados])

@main.route('/api/libros_atrasados')
@login_required
@roles_requeridos('administrador')
def libros_atrasados():
    resultados = db.session.query(
        Libro.titulo,
        func.count(Prestamo.id).label('total')
    ).join(Prestamo).filter(Prestamo.estado == 'atrasado') \
     .group_by(Libro.id).order_by(func.count(Prestamo.id).desc()).limit(5).all()

    return jsonify([{'titulo': r.titulo, 'total': r.total} for r in resultados])

@main.route('/ajax/buscar_usuario_por_llave')
@login_required
def ajax_buscar_usuario_por_llave():
    llave_prestamo = request.args.get('llave_prestamo')
    usuario = Usuario.query.filter_by(llave_prestamo=llave_prestamo).first()
    if usuario:
        return jsonify(success=True, correo=usuario.correo, usuario_id=usuario.id)
    else:
        return jsonify(success=False)






