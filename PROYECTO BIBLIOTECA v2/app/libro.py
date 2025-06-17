from app.models import db
from app.models import Libro, Ejemplar, Prestamo
from datetime import datetime, timedelta

def generar_isbn(base, numero):
    return f"{base}-{str(numero).zfill(4)}"  # ISBN bien formateado

def agregar_libro(titulo, autor, isbn_base, cantidad, descripcion=None,
                  editorial=None, fecha_publicacion=None, categoria=None):
    nuevo_libro = Libro(
        titulo=titulo,
        autor=autor,
        isbn_base=isbn_base,
        descripcion=descripcion,
        editorial=editorial,
        fecha_publicacion=fecha_publicacion,
        categoria=categoria,
        cantidad_total=cantidad,
        cantidad_disponible=cantidad,
        disponible=True
    )
    db.session.add(nuevo_libro)
    db.session.commit()  # Necesitamos el ID para crear ejemplares

    for i in range(1, cantidad + 1):
        isbn = generar_isbn(isbn_base, i)
        ejemplar = Ejemplar(
            libro_id=nuevo_libro.id,
            isbn=isbn,
            estado='disponible'
        )
        db.session.add(ejemplar)

    db.session.commit()
    return nuevo_libro

def actualizar_disponibilidad_libro(libro):
    disponibles = Ejemplar.query.filter_by(libro_id=libro.id, estado='disponible').count()
    libro.cantidad_disponible = disponibles
    libro.disponible = disponibles > 0
    db.session.commit()

def prestar_por_isbn(isbn, usuario_id):
    ejemplar = Ejemplar.query.filter_by(isbn=isbn).first()
    if not ejemplar or ejemplar.estado != 'disponible':
        return "Ejemplar no disponible o no existe"

    prestamo = Prestamo(
        libro_id=ejemplar.libro_id,
        usuario_id=usuario_id,
        fecha_prestamo=datetime.utcnow(),
        fecha_devolucion_esperada=datetime.utcnow().date() + timedelta(days=7),
        estado='prestado'
    )

    ejemplar.estado = 'prestado'
    db.session.add(prestamo)
    db.session.commit()

    actualizar_disponibilidad_libro(ejemplar.libro)
    return "Préstamo realizado correctamente"

def sincronizar_ejemplares(libro, nueva_cantidad_total):
    diferencia = nueva_cantidad_total - libro.cantidad_total

    if diferencia > 0:
        # Agregar nuevos ejemplares
        ultimo = Ejemplar.query.filter_by(libro_id=libro.id).count()
        for i in range(1, diferencia + 1):
            nuevo_isbn = f"978-{libro.isbn_base}-{str(ultimo + i).zfill(4)}"
            nuevo = Ejemplar(libro_id=libro.id, isbn=nuevo_isbn, estado="disponible")
            db.session.add(nuevo)

    elif diferencia < 0:
        # Eliminar ejemplares disponibles
        ejemplares_disponibles = Ejemplar.query.filter_by(libro_id=libro.id, estado="disponible").limit(abs(diferencia)).all()
        if len(ejemplares_disponibles) < abs(diferencia):
            return False  # No hay suficientes disponibles para eliminar
        for ej in ejemplares_disponibles:
            db.session.delete(ej)

    return True  # Todo bien


def eliminar_libro(libro_id):
    libro = Libro.query.get(libro_id)
    if not libro:
        return "Libro no encontrado"

    ejemplares_no_disponibles = Ejemplar.query.filter(
        Ejemplar.libro_id == libro_id,
        Ejemplar.estado != 'disponible'
    ).count()

    if ejemplares_no_disponibles > 0:
        return "No se puede eliminar: tiene ejemplares no disponibles"

    libro.disponible = False
    db.session.commit()
    return "Libro marcado como no disponible"
