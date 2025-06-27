class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/biblioteca_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'clave-secreta-super-segura'

    MAIL_SERVER = 'sandbox.smtp.mailtrap.io'
    MAIL_PORT = 2525
    MAIL_USERNAME = '5941fdd25fae2b'
    MAIL_PASSWORD = 'd4e6b9abc0517e'
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

