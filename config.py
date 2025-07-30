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
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Configuraciones adicionales para producción
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 