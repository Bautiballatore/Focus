import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///examenes.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Configuración de Wolfram Alpha
    WOLFRAM_APP_ID = os.getenv('WOLFRAM_APP_ID', 'AV6EGRRK9V')
    
    # Configuración de seguridad
    SESSION_COOKIE_SECURE = True  # Cambiado para HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Más estricto para evitar sesiones cruzadas
    PERMANENT_SESSION_LIFETIME = 3600  # Sesiones expiran en 1 hora
    SESSION_COOKIE_MAX_AGE = 3600  # Cookies expiran en 1 hora

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'
    SESSION_COOKIE_SECURE = False  # HTTP para desarrollo
    SESSION_COOKIE_SAMESITE = 'Strict'  # Más estricto para evitar sesiones cruzadas
    PERMANENT_SESSION_LIFETIME = 3600  # Sesiones expiran en 1 hora
    SESSION_COOKIE_MAX_AGE = 3600  # Cookies expiran en 1 hora

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True  # HTTPS para producción
    # Temporalmente usar SQLite para que funcione
    SQLALCHEMY_DATABASE_URI = 'sqlite:///examenes.db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 