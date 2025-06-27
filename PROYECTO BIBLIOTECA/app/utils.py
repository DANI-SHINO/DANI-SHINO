from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import random
from app.models import Usuario

def generar_token(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='recuperar-contrasena')

def verificar_token(token, max_age=3600):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='recuperar-contrasena', max_age=max_age)
    except:
        return None
    return email

def generar_llave_prestamo():
    while True:
        nueva_llave = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
        if not Usuario.query.filter_by(llave_prestamo=nueva_llave).first():
            return nueva_llave

