from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from dotenv import load_dotenv
import os
import PyPDF2
import docx
import re
import time
import json
from datetime import datetime
from io import BytesIO
import requests
import base64
import xml.etree.ElementTree as ET
import traceback
from supabase import create_client, Client

load_dotenv()

# Configuración de la aplicación
app = Flask(__name__, template_folder='Templates')
app.config.from_object('config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.DevelopmentConfig')
app.jinja_env.globals.update(range=range)

# Configuración de Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://youohevduvkkptdcrmut.supabase.co')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvdW9oZXZkdXZra3B0ZGNybXV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU2MjgyOTQsImV4cCI6MjA3MTIwNDI5NH0.VTg8bqARO-R11D-vNw6epmK6XkGVrT05BcdXyOkBW24')

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("✅ Supabase client initialized successfully!")
except Exception as e:
    print(f"❌ Error initializing Supabase: {e}")
    supabase = None

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app_id = "AV6EGRRK9V"

# Modelo de Usuario simplificado para Supabase
class User(UserMixin):
    def __init__(self, id, email, nombre, fecha_registro, como_nos_conociste=None, uso_plataforma=None):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.fecha_registro = fecha_registro
        self.como_nos_conociste = como_nos_conociste
        self.uso_plataforma = uso_plataforma
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    try:
        if supabase:
            # Buscar usuario en Supabase
            response = supabase.table('usuarios').select('*').eq('id', user_id).execute()
            if response.data:
                user_data = response.data[0]
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    nombre=user_data['nombre'],
                    fecha_registro=datetime.fromisoformat(user_data['fecha_registro'].replace('Z', '+00:00')),
                    como_nos_conociste=user_data.get('como_nos_conociste'),
                    uso_plataforma=user_data.get('plataforma_uso')
                )
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        nombre = request.form["nombre"]
        
        try:
            if supabase:
                # Verificar si el usuario ya existe en Supabase
                response = supabase.table('usuarios').select('*').eq('email', email).execute()
                if response.data:
                    flash("El email ya está registrado. Por favor, usa otro email.")
                    return render_template("registro.html")
                
                # Crear nuevo usuario en Supabase
                password_hash = generate_password_hash(password)
                user_data = {
                    'email': email,
                    'nombre': nombre,
                    'password_hash': password_hash,
                    'fecha_registro': datetime.utcnow().isoformat(),
                    'activo': True
                }
                
                response = supabase.table('usuarios').insert(user_data).execute()
                
                if response.data:
                    flash("Usuario registrado exitosamente. Ahora puedes iniciar sesión.")
                    return redirect(url_for('login'))
                else:
                    flash("Error al registrar usuario. Intenta de nuevo.")
                    
        except Exception as e:
            print(f"Error en registro: {e}")
            flash("Error al registrar usuario. Intenta de nuevo.")
        
        return render_template("registro.html")
    
    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        
        try:
            if supabase:
                # Buscar usuario en Supabase
                response = supabase.table('usuarios').select('*').eq('email', email).execute()
                
                if response.data and len(response.data) > 0:
                    user_data = response.data[0]
                    if check_password_hash(user_data['password_hash'], password):
                        user = User(
                            id=user_data['id'],
                            email=user_data['email'],
                            nombre=user_data['nombre'],
                            fecha_registro=datetime.fromisoformat(user_data['fecha_registro'].replace('Z', '+00:00')),
                            como_nos_conociste=user_data.get('como_nos_conociste'),
                            uso_plataforma=user_data.get('plataforma_uso')
                        )
                        login_user(user)
                        
                        # Log de actividad
                        try:
                            log_data = {
                                'usuario_id': user_data['id'],
                                'tipo_actividad': 'login',
                                'fecha_actividad': datetime.utcnow().isoformat(),
                                'detalles': {'accion': 'Usuario inició sesión'},
                                'ip_address': request.remote_addr
                            }
                            supabase.table('logs_actividad').insert(log_data).execute()
                        except Exception as e:
                            print(f"Error logging activity: {e}")
                        
                        return redirect(url_for('preguntas_usuario'))
                    else:
                        flash("Contraseña incorrecta.")
                else:
                    flash("Email no encontrado.")
                    
        except Exception as e:
            print(f"Error en login: {e}")
            flash("Error al iniciar sesión. Intenta de nuevo.")
        
        return render_template("login.html")
    
    return render_template("login.html")

@app.route("/preguntas-usuario", methods=["GET", "POST"])
@login_required
def preguntas_usuario():
    if request.method == "POST":
        como_nos_conociste = request.form.get("como_nos_conociste")
        uso_plataforma = request.form.get("uso_plataforma")
        
        try:
            if supabase:
                # Actualizar usuario en Supabase
                update_data = {
                    'como_nos_conociste': como_nos_conociste,
                    'plataforma_uso': uso_plataforma,
                    'ultima_actividad': datetime.utcnow().isoformat()
                }
                
                supabase.table('usuarios').update(update_data).eq('id', current_user.id).execute()
                
                # Log de actividad
                log_data = {
                    'usuario_id': current_user.id,
                    'tipo_actividad': 'completar_perfil',
                    'fecha_actividad': datetime.utcnow().isoformat(),
                    'detalles': {
                        'como_nos_conociste': como_nos_conociste,
                        'uso_plataforma': uso_plataforma
                    },
                    'ip_address': request.remote_addr
                }
                supabase.table('logs_actividad').insert(log_data).execute()
                
                flash("Información guardada exitosamente!")
                return redirect(url_for('generar'))
                
        except Exception as e:
            print(f"Error guardando preguntas: {e}")
            flash("Error al guardar información. Intenta de nuevo.")
        
        return render_template("preguntas_usuario.html")
    
    return render_template("preguntas_usuario.html")

@app.route("/logout")
@login_required
def logout():
    try:
        if supabase:
            # Log de actividad
            log_data = {
                'usuario_id': current_user.id,
                'tipo_actividad': 'logout',
                'fecha_actividad': datetime.utcnow().isoformat(),
                'detalles': {'accion': 'Usuario cerró sesión'},
                'ip_address': request.remote_addr
            }
            supabase.table('logs_actividad').insert(log_data).execute()
    except Exception as e:
        print(f"Error logging logout: {e}")
    
    logout_user()
    return redirect(url_for('index'))

@app.route("/perfil")
@login_required
def perfil():
    return render_template("perfil.html")

# Mantener las demás rutas igual por ahora...
@app.route("/generar", methods=["GET", "POST"])
@login_required
def generar():
    return render_template("generar.html")

@app.route("/historial")
@login_required
def historial():
    return render_template("historial.html")

@app.route("/planificacion", methods=["GET", "POST"])
@login_required
def planificacion():
    return render_template("planificacion.html")

@app.route("/como-funciona")
def como_funciona():
    return render_template("como_funciona.html")

@app.route("/wolfram", methods=["GET", "POST"])
@login_required
def wolfram_query():
    return render_template("wolfram.html")

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=debug)
