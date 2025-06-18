# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify # ¡Importamos jsonify!
import mysql.connector
from forms import RegisterBookForm, BarcodeScanForm
from forms import RegisterFromScanForm
import barcode
from barcode.writer import ImageWriter
from models import inicializar_db
import random
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'

# --- Configuración de la Conexión a MySQL ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'biblioteca'
}

# --- Directorio para guardar las imágenes de códigos de barras ---
BARCODE_DIR = os.path.join(app.root_path, 'static', 'barcodes')
if not os.path.exists(BARCODE_DIR):
    os.makedirs(BARCODE_DIR)

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

# --- Funciones para generación de códigos de barras (sin cambios) ---
def calculate_ean13_checksum(digits):
    total = 0
    for i, digit in enumerate(digits):
        if (i + 1) % 2 == 1:
            total += int(digit)
        else:
            total += int(digit) * 3
    checksum = (10 - (total % 10)) % 10
    return str(checksum)

def generate_random_isbn13():
    prefix = random.choice(['978', '979'])
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    base_isbn = prefix + random_digits
    check_digit = calculate_ean13_checksum(base_isbn)
    return base_isbn + check_digit

def create_barcode_image(isbn):
    try:
        if len(isbn) != 13 or not isbn.isdigit():
            print(f"ERROR_BARCODE: ISBN '{isbn}' no tiene el formato correcto (13 dígitos numéricos).")
            return None
        ean = barcode.EAN13(isbn, writer=ImageWriter())
        filename = f"{isbn}"
        filepath = os.path.join(BARCODE_DIR, filename)
        ean.save(filepath)
        return f"barcodes/{filename}.png"
    except barcode.errors.BarcodeError as e:
        print(f"ERROR_BARCODE: Error al generar código de barras para {isbn}: {e}")
        return None
    except Exception as e:
        print(f"ERROR_GENERICO: Error inesperado al crear código de barras para {isbn}: {e}")
        return None
    
def buscar_libro_por_isbn_online(isbn):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        response = requests.get(url)
        data = response.json()
        libro_data = data.get(f"ISBN:{isbn}")

        if libro_data:
            titulo = libro_data.get("title", "Sin título")
            autores = libro_data.get("authors", [])
            autor_nombres = ', '.join([a['name'] for a in autores]) if autores else "Desconocido"
            return {
                "titulo": titulo,
                "autor": autor_nombres
            }
        else:
            return None
    except Exception as e:
        print(f"Error al consultar OpenLibrary: {e}")
        return None

@app.route('/registrar/scan', methods=['GET', 'POST'])
def registrar_libro_scan():
    form = RegisterFromScanForm()
    barcode_image_path = None
    if request.method == 'POST' and form.validate_on_submit():
        isbn = form.isbn.data
        titulo = form.titulo.data
        autor = form.autor.data
        cantidad = int(form.cantidad.data)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verificar si el libro ya existe
            cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn,))
            libro = cursor.fetchone()

            if not libro:
                cursor.execute(
                    "INSERT INTO libros (codigo_barra, titulo, autor, estado) VALUES (%s, %s, %s, 'disponible')",
                    (isbn, titulo, autor)
                )
                conn.commit()
                cursor.execute("SELECT id FROM libros WHERE codigo_barra = %s", (isbn,))
                libro = cursor.fetchone()

            libro_id = libro['id']

            # Generar ejemplares
            for i in range(1, cantidad + 1):
                cod_ejemplar = f"{isbn}-{i:04d}"
                cursor.execute("""
                    INSERT INTO ejemplares (libro_id, codigo_ejemplar, estado)
                    VALUES (%s, %s, 'disponible')
                """, (libro_id, cod_ejemplar))

            conn.commit()
            flash(f"Libro '{titulo}' registrado con {cantidad} ejemplares.", "success")
            barcode_image_path = create_barcode_image(isbn)
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    return render_template('register_from_scan.html', form=form, barcode_image_path=barcode_image_path)

@app.route('/api/datos_libro/<isbn>')
def api_datos_libro(isbn):
    datos = buscar_libro_por_isbn_online(isbn)
    if datos:
        return jsonify({'success': True, 'titulo': datos['titulo'], 'autor': datos['autor']})
    else:
        return jsonify({'success': False, 'message': 'No se encontró el libro en OpenLibrary'}), 404


# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM libros")
    libros = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', libros=libros)

@app.route('/registrar', methods=['GET', 'POST'])
def registrar_libro():
    form = RegisterBookForm()
    registered_book = None
    barcode_image_path = None

    if form.validate_on_submit():
        isbn = form.isbn.data if form.isbn.data else generate_random_isbn13()
        titulo = form.titulo.data
        autor = form.autor.data

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id FROM libros WHERE codigo_barra = %s", (isbn,))
            libro_existente = cursor.fetchone()

            if libro_existente:
                flash(f'Ya existe un libro con el ISBN "{isbn}".', 'warning')
                cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn,))
                existing_book_data = cursor.fetchone()
                if existing_book_data:
                    registered_book = existing_book_data
                    barcode_image_path = create_barcode_image(isbn) 
                
            else:
                barcode_image_path = create_barcode_image(isbn)
                if not barcode_image_path:
                    flash(f'Error al generar la imagen del código de barras para el ISBN {isbn}.', 'danger')
                else:
                    cursor.execute(
                        "INSERT INTO libros (codigo_barra, titulo, autor, estado) VALUES (%s, %s, %s, 'disponible')",
                        (isbn, titulo, autor)
                    )
                    conn.commit()
                    flash(f'Libro "{titulo}" (ISBN: {isbn}) registrado exitosamente!', 'success')
                    registered_book = {
                        'codigo_barra': isbn,
                        'titulo': titulo,
                        'autor': autor,
                        'estado': 'disponible'
                    }
        except mysql.connector.Error as err:
            flash(f"Error de base de datos: {err}", 'danger')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            
    if request.method == 'GET' or (request.method == 'POST' and not registered_book):
        form.isbn.data = generate_random_isbn13()

    return render_template('register_book.html', form=form, registered_book=registered_book, barcode_image_path=barcode_image_path)

@app.route('/prestamo-devolucion')
def escaner_prestamo_devolucion():
    return render_template('scan_lending.html')


@app.route('/api/ejemplar/escanear', methods=['POST'])
def api_escanear_ejemplar():
    data = request.get_json()
    codigo_ejemplar = data.get('codigo')

    if not codigo_ejemplar:
        return jsonify({'success': False, 'message': 'Código no proporcionado'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT e.*, l.titulo FROM ejemplares e
            JOIN libros l ON e.libro_id = l.id
            WHERE e.codigo_ejemplar = %s
        """, (codigo_ejemplar,))
        ejemplar = cursor.fetchone()

        if not ejemplar:
            return jsonify({'success': False, 'message': f'No se encontró el ejemplar {codigo_ejemplar}'}), 404

        nuevo_estado = 'prestado' if ejemplar['estado'] == 'disponible' else 'disponible'
        cursor.execute("UPDATE ejemplares SET estado = %s WHERE codigo_ejemplar = %s", (nuevo_estado, codigo_ejemplar))
        conn.commit()

        return jsonify({
            'success': True,
            'titulo': ejemplar['titulo'],
            'codigo_ejemplar': codigo_ejemplar,
            'estado_anterior': ejemplar['estado'],
            'estado_nuevo': nuevo_estado,
            'message': f'Ejemplar actualizado a "{nuevo_estado}" correctamente.'
        })

    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f"Error: {err}"}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/registrar/scan-auto', methods=['GET', 'POST'])
def registrar_libro_scan_auto():
    form = RegisterFromScanForm()
    barcode_image_path = None
    if form.validate_on_submit():
        isbn = form.isbn.data
        titulo = form.titulo.data
        autor = form.autor.data
        cantidad = int(form.cantidad.data)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn,))
            libro = cursor.fetchone()
            if not libro:
                cursor.execute("INSERT INTO libros (codigo_barra, titulo, autor, estado) VALUES (%s, %s, %s, 'disponible')",
                               (isbn, titulo, autor))
                conn.commit()
                cursor.execute("SELECT id FROM libros WHERE codigo_barra = %s", (isbn,))
                libro = cursor.fetchone()

            libro_id = libro['id']

            for i in range(1, cantidad + 1):
                cod_ejemplar = f"{isbn}-{i:04d}"
                cursor.execute("INSERT INTO ejemplares (libro_id, codigo_ejemplar, estado) VALUES (%s, %s, 'disponible')",
                               (libro_id, cod_ejemplar))

            conn.commit()
            flash(f"Libro '{titulo}' registrado con {cantidad} ejemplares.", "success")
            barcode_image_path = create_barcode_image(isbn)
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    return render_template('register_from_scan_auto.html', form=form, barcode_image_path=barcode_image_path)


# --- Ruta para el escaneo vía cámara (AJAX) ---
@app.route('/api/escanear_camara', methods=['POST'])
def api_escanear_camara():
    data = request.get_json() # Obtiene los datos JSON enviados desde el frontend
    isbn = data.get('isbn')

    if not isbn:
        return jsonify({'success': False, 'message': 'ISBN no proporcionado'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn,))
        libro = cursor.fetchone()

        if not libro:
            return jsonify({'success': False, 'message': f'Libro con ISBN "{isbn}" no encontrado. Regístralo primero.'}), 404
        else:
            nuevo_estado = 'disponible' if libro['estado'] == 'no disponible' else 'no disponible'
            cursor.execute(
                "UPDATE libros SET estado = %s WHERE codigo_barra = %s",
                (nuevo_estado, isbn)
            )
            conn.commit()
            return jsonify({
                'success': True,
                'message': f'Libro "{libro["titulo"]}" actualizado a "{nuevo_estado}".',
                'titulo': libro['titulo'],
                'estado_anterior': libro['estado'],
                'estado_nuevo': nuevo_estado
            }), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f"Error de base de datos: {err}"}), 500
    finally:
        cursor.close()
        conn.close()

# --- Ruta original /escanear (para la versión con formulario manual, si aún la quieres) ---
@app.route('/escanear', methods=['GET', 'POST'])
def escanear_libro():
    # Esta ruta ahora será principalmente para la vista del escáner con cámara
    # Mantener el formulario manual si es necesario, o quitarlo y dejar solo la vista de cámara
    form = BarcodeScanForm() # Puedes eliminar esta línea y el formulario si solo usas la cámara
    
    # Si recibes un POST aquí, puedes seguir procesándolo como antes
    if request.method == 'POST' and form.validate_on_submit():
        isbn_escaneado = form.isbn.data
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn_escaneado,))
            libro = cursor.fetchone()
            if not libro:
                flash(f'Libro con ISBN "{isbn_escaneado}" no encontrado. Regístralo primero.', 'danger')
            else:
                nuevo_estado = 'disponible' if libro['estado'] == 'no disponible' else 'no disponible'
                cursor.execute("UPDATE libros SET estado = %s WHERE codigo_barra = %s", (nuevo_estado, isbn_escaneado))
                conn.commit()
                flash(f'Libro "{libro["titulo"]}" actualizado a "{nuevo_estado}".', 'info')
        except mysql.connector.Error as err:
            flash(f"Error de base de datos: {err}", 'danger')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('escanear_libro'))
    
    # Renderiza la plantilla con el escáner de cámara
    return render_template('scan_book.html', form=form) # Pasa el formulario si lo mantienes


@app.route('/libro/<string:isbn>')
def detalle_libro(isbn):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM libros WHERE codigo_barra = %s", (isbn,))
    libro = cursor.fetchone()
    cursor.close()
    conn.close()

    if not libro:
        flash(f"El libro con ISBN '{isbn}' no fue encontrado.", 'danger')
        return redirect(url_for('index'))
    
    barcode_image_path = f"barcodes/{libro['codigo_barra']}.png"

    return render_template('book_details.html', libro=libro, barcode_image_path=barcode_image_path)

if __name__ == '__main__':
    inicializar_db()
    app.run(debug=True)