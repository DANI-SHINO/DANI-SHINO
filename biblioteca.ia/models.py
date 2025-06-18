import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'biblioteca'
}

def crear_tablas():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS libros (
            id INT AUTO_INCREMENT PRIMARY KEY,
            codigo_barra VARCHAR(13) UNIQUE NOT NULL,
            titulo VARCHAR(100) NOT NULL,
            autor VARCHAR(100) NOT NULL,
            estado ENUM('disponible', 'no disponible') DEFAULT 'disponible'
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    
def crear_tabla_ejemplares():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ejemplares (
            id INT AUTO_INCREMENT PRIMARY KEY,
            libro_id INT NOT NULL,
            codigo_ejemplar VARCHAR(20) UNIQUE NOT NULL,
            estado ENUM('disponible', 'prestado') DEFAULT 'disponible',
            FOREIGN KEY (libro_id) REFERENCES libros(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ejemplares (
        id INT AUTO_INCREMENT PRIMARY KEY,
        libro_id INT NOT NULL,
        codigo_ejemplar VARCHAR(20) UNIQUE NOT NULL,
        estado ENUM('disponible', 'prestado') DEFAULT 'disponible',
        FOREIGN KEY (libro_id) REFERENCES libros(id)
    )
    """)


    conn.commit()
    cursor.close()
    conn.close()


def insertar_libro_inicial():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM libros")
    cantidad = cursor.fetchone()['total']

    if cantidad == 0:
        cursor.execute("""
            INSERT INTO libros (codigo_barra, titulo, autor, estado)
            VALUES ('9781234567897', 'Libro Inicial', 'Autor Demo', 'disponible')
        """)
        conn.commit()

        # Obtener ID del libro recién insertado
        cursor.execute("SELECT id FROM libros WHERE codigo_barra = '9781234567897'")
        libro_id = cursor.fetchone()['id']

        # Insertar un ejemplar
        cursor.execute("""
            INSERT INTO ejemplares (libro_id, codigo_ejemplar, estado)
            VALUES (%s, %s, %s)
        """, (libro_id, '9781234567897-0001', 'disponible'))
        conn.commit()

    cursor.close()
    conn.close()


def inicializar_db():
    crear_tablas()
    crear_tabla_ejemplares()
    insertar_libro_inicial()

