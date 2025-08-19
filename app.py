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

# Supabase imports
from supabase import create_client, Client

load_dotenv()

# Configuración de la aplicación
app = Flask(__name__, template_folder='Templates')
app.config.from_object('config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.DevelopmentConfig')

app.jinja_env.globals.update(range=range)

# Inicializar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if SUPABASE_URL and SUPABASE_ANON_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("✅ Supabase client initialized successfully!")
else:
    print("❌ Supabase credentials not found!")
    supabase = None

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app_id = "AV6EGRRK9V"

# Modelo de Usuario simplificado para Supabase
class User(UserMixin):
    def __init__(self, id, email, nombre, fecha_registro, como_nos_conociste=None, uso_plataforma=None, preguntas_completadas=False):
        self.id = id
        self.email = email
        self.nombre = nombre
        self.fecha_registro = fecha_registro
        self.como_nos_conociste = como_nos_conociste
        self.uso_plataforma = uso_plataforma
        self.preguntas_completadas = preguntas_completadas
    
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
                    uso_plataforma=user_data.get('plataforma_uso'),
                    preguntas_completadas=user_data.get('preguntas_completadas', False)
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
                    'activo': True,
                    'preguntas_completadas': False
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
                            uso_plataforma=user_data.get('plataforma_uso'),
                            preguntas_completadas=user_data.get('preguntas_completadas', False)
                        )
                        login_user(user)
                        
                        # Log de actividad
                        log_data = {
                            'usuario_id': user.id,
                            'tipo_actividad': 'login',
                            'fecha_actividad': datetime.utcnow().isoformat(),
                            'detalles': {'accion': 'Usuario inició sesión'},
                            'ip_address': request.remote_addr
                        }
                        supabase.table('logs_actividad').insert(log_data).execute()
                        
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
                    'preguntas_completadas': True,
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

@app.route("/generar", methods=["GET", "POST"])
@login_required
def generar():
    if request.method == "POST":
        try:
            # Obtener datos del formulario
            materia = request.form.get('materia', '')
            nivel = request.form.get('nivel', '')
            cantidad = int(request.form.get('cantidad', 5))
            tipo_examen = request.form.get('tipo_examen', 'opcion_multiple')
            
            # Obtener archivo si se subió
            archivo = request.files.get('archivo')
            texto = ""
            
            if archivo and archivo.filename:
                # Procesar archivo según su tipo
                if archivo.filename.lower().endswith('.txt'):
                    texto = archivo.read().decode('utf-8')
                    print(f"📄 Archivo TXT procesado: {len(texto)} caracteres")
                    
                elif archivo.filename.lower().endswith('.pdf'):
                    try:
                        pdf_reader = PyPDF2.PdfReader(archivo)
                        max_pages = min(len(pdf_reader.pages), 7)  # Limitar a 7 páginas
                        
                        for i in range(max_pages):
                            page = pdf_reader.pages[i]
                            texto += page.extract_text() + "\n"
                        
                        print(f"📄 PDF procesado: {max_pages} páginas, {len(texto)} caracteres")
                        
                        if max_pages < len(pdf_reader.pages):
                            print(f"⚠️ PDF limitado a {max_pages} páginas de {len(pdf_reader.pages)} total")
                        
                    except Exception as e:
                        print(f"❌ Error procesando PDF: {e}")
                        flash("Error al procesar el archivo PDF. Intenta con otro archivo.")
                        return render_template("generar.html")
                        
                elif archivo.filename.lower().endswith('.docx'):
                    try:
                        doc = docx.Document(archivo)
                        max_paragraphs = min(len(doc.paragraphs), 50)  # Limitar a 50 párrafos
                        
                        for i in range(max_paragraphs):
                            if doc.paragraphs[i].text.strip():
                                texto += doc.paragraphs[i].text + "\n"
                        
                        print(f"📄 DOCX procesado: {max_paragraphs} párrafos, {len(texto)} caracteres")
                        
                        if max_paragraphs < len(doc.paragraphs):
                            print(f"⚠️ DOCX limitado a {max_paragraphs} párrafos de {len(doc.paragraphs)} total")
                        
                    except Exception as e:
                        print(f"❌ Error procesando DOCX: {e}")
                        flash("Error al procesar el archivo DOCX. Intenta con otro archivo.")
                        return render_template("generar.html")
                
                if not texto.strip():
                    print("⚠️ Archivo procesado pero sin contenido extraído")
                    flash("El archivo no contiene texto legible. Intenta con otro archivo.")
                    return render_template("generar.html")
            
            # Si no hay archivo, usar texto del formulario
            if not texto:
                texto = request.form.get('texto', '')
            
            if not texto.strip():
                flash("Por favor, proporciona un texto o sube un archivo.")
                return render_template("generar.html")
            
            # Limitar el texto a 3000 caracteres para evitar timeouts
            texto = texto[:3000]
            
            # Generar prompt para OpenAI
            if tipo_examen == 'opcion_multiple':
                prompt = f"""Genera un examen de {materia} de nivel {nivel} con {cantidad} preguntas de opción múltiple.

Texto de referencia:
{texto}

Formato de respuesta (JSON):
{{
    "titulo": "Título del examen",
    "materia": "{materia}",
    "nivel": "{nivel}",
    "preguntas": [
        {{
            "enunciado": "Pregunta 1",
            "opciones": ["A) Opción 1", "B) Opción 2", "C) Opción 3", "D) Opción 4"],
            "respuesta_correcta": "A",
            "explicacion": "Explicación de por qué es correcta"
        }}
    ]
}}

Asegúrate de que las preguntas sean claras, relevantes al texto y que solo una opción sea correcta."""
            
            elif tipo_examen == 'verdadero_falso':
                prompt = f"""Genera un examen de {materia} de nivel {nivel} con {cantidad} preguntas de verdadero o falso.

Texto de referencia:
{texto}

Formato de respuesta (JSON):
{{
    "titulo": "Título del examen",
    "materia": "{materia}",
    "nivel": "{nivel}",
    "preguntas": [
        {{
            "enunciado": "Pregunta 1",
            "respuesta_correcta": "Verdadero",
            "explicacion": "Explicación de por qué es verdadero o falso"
        }}
    ]
}}

Asegúrate de que las preguntas sean claras y relevantes al texto."""
            
            else:  # preguntas_abiertas
                prompt = f"""Genera un examen de {materia} de nivel {nivel} con {cantidad} preguntas abiertas.

Texto de referencia:
{texto}

Formato de respuesta (JSON):
{{
    "titulo": "Título del examen",
    "materia": "{materia}",
    "nivel": "{nivel}",
    "preguntas": [
        {{
            "enunciado": "Pregunta 1",
            "respuesta_esperada": "Respuesta esperada o puntos clave",
            "puntos_clave": ["Punto clave 1", "Punto clave 2", "Punto clave 3"]
        }}
    ]
}}

Asegúrate de que las preguntas sean claras, relevantes al texto y que requieran respuestas detalladas."""
            
            # Llamar a OpenAI
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3000,
                    temperature=0.7,
                    timeout=60
                )
                
                # Procesar respuesta
                contenido = response.choices[0].message.content
                
                # Intentar extraer JSON
                try:
                    # Buscar JSON en la respuesta
                    json_match = re.search(r'\{.*\}', contenido, re.DOTALL)
                    if json_match:
                        examen_data = json.loads(json_match.group())
                        
                        # Guardar en sesión para mostrar
                        session['examen_actual'] = examen_data
                        session['tipo_examen'] = tipo_examen
                        
                        return redirect(url_for('resultado'))
                    else:
                        flash("Error al generar el examen. Intenta de nuevo.")
                        return render_template("generar.html")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"Contenido recibido: {contenido}")
                    flash("Error al procesar la respuesta de la IA. Intenta de nuevo.")
                    return render_template("generar.html")
                    
            except Exception as e:
                print(f"❌ Error llamando a OpenAI: {e}")
                traceback.print_exc()
                flash("Error al generar el examen. Intenta de nuevo.")
                return render_template("generar.html")
                
        except Exception as e:
            print(f"❌ Error general en generación: {e}")
            traceback.print_exc()
            flash("Error inesperado. Intenta de nuevo.")
            return render_template("generar.html")
    
    return render_template("generar.html")

@app.route("/pregunta/<int:numero>", methods=["GET", "POST"])
@login_required
def pregunta(numero):
    if 'examen_actual' not in session:
        flash("No hay examen activo. Genera uno nuevo.")
        return redirect(url_for('generar'))
    
    examen = session['examen_actual']
    preguntas = examen.get('preguntas', [])
    
    if numero < 1 or numero > len(preguntas):
        flash("Número de pregunta inválido.")
        return redirect(url_for('generar'))
    
    pregunta = preguntas[numero - 1]
    
    if request.method == "POST":
        respuesta_usuario = request.form.get('respuesta')
        
        if not respuesta_usuario:
            flash("Por favor, selecciona una respuesta.")
            return render_template("pregunta.html", pregunta=pregunta, numero=numero, total=len(preguntas))
        
        # Guardar respuesta en sesión
        if 'respuestas_usuario' not in session:
            session['respuestas_usuario'] = {}
        session['respuestas_usuario'][str(numero)] = respuesta_usuario
        
        # Si es la última pregunta, ir a resultado
        if numero == len(preguntas):
            return redirect(url_for('resultado'))
        else:
            return redirect(url_for('pregunta', numero=numero + 1))
    
    return render_template("pregunta.html", pregunta=pregunta, numero=numero, total=len(preguntas))

@app.route("/resultado")
@login_required
def resultado():
    if 'examen_actual' not in session:
        flash("No hay examen para mostrar.")
        return redirect(url_for('generar'))
    
    examen = session['examen_actual']
    respuestas_usuario = session.get('respuestas_usuario', {})
    
    # Calcular resultados
    correctas = 0
    parciales = 0
    incorrectas = 0
    total = len(examen['preguntas'])
    
    for i, pregunta in enumerate(examen['preguntas'], 1):
        respuesta_usuario = respuestas_usuario.get(str(i))
        if respuesta_usuario:
            if pregunta.get('respuesta_correcta') == respuesta_usuario:
                correctas += 1
            else:
                incorrectas += 1
    
    # Calcular nota (porcentaje)
    nota = (correctas / total) * 100 if total > 0 else 0
    
    # Guardar resultado en sesión
    session['resultado_examen'] = {
        'nota': nota,
        'correctas': correctas,
        'parciales': parciales,
        'incorrectas': incorrectas,
        'total': total
    }
    
    return render_template("resultado.html", 
                         examen=examen, 
                         respuestas_usuario=respuestas_usuario,
                         nota=nota,
                         correctas=correctas,
                         parciales=parciales,
                         incorrectas=incorrectas,
                         total=total)

@app.route("/cuestionario")
@login_required
def cuestionario():
    if 'examen_actual' not in session:
        flash("No hay examen activo. Genera uno nuevo.")
        return redirect(url_for('generar'))
    
    examen = session['examen_actual']
    return render_template("cuestionario.html", examen=examen)

@app.route("/reiniciar", methods=["POST"])
@login_required
def reiniciar():
    # Limpiar sesión del examen
    session.pop('examen_actual', None)
    session.pop('respuestas_usuario', None)
    session.pop('resultado_examen', None)
    session.pop('tipo_examen', None)
    
    flash("Examen reiniciado. Puedes generar uno nuevo.")
    return redirect(url_for('generar'))

@app.route("/historial")
@login_required
def historial():
    # Por ahora, mostrar mensaje de que no hay historial
    # En el futuro, esto se conectará con Supabase para mostrar exámenes previos
    flash("El historial de exámenes estará disponible próximamente.")
    return render_template("historial.html")

@app.route("/examen/<int:examen_id>")
@login_required
def examen_detalle(examen_id):
    # Por ahora, mostrar mensaje de que no hay detalles
    # En el futuro, esto se conectará con Supabase para mostrar detalles del examen
    flash("Los detalles del examen estarán disponibles próximamente.")
    return render_template("detalle_examen.html")

@app.route("/wolfram", methods=["GET", "POST"])
@login_required
def wolfram_query():
    if request.method == "POST":
        query = request.form.get('query', '')
        
        if not query.strip():
            flash("Por favor, ingresa una consulta matemática.")
            return render_template("wolfram.html")
        
        try:
            # Configuración de Wolfram Alpha
            app_id = "AV6EGRRK9V"
            base_url = "http://api.wolframalpha.com/v2/query"
            
            params = {
                'input': query,
                'appid': app_id,
                'output': 'xml',
                'format': 'plaintext'
            }
            
            # Llamar a Wolfram Alpha con timeout
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Procesar respuesta XML
            root = ET.fromstring(response.content)
            
            # Extraer resultados
            resultados = []
            for pod in root.findall('.//pod'):
                titulo = pod.get('title', '')
                contenido = pod.find('.//plaintext')
                if contenido is not None and contenido.text:
                    resultados.append({
                        'titulo': titulo,
                        'contenido': contenido.text.strip()
                    })
            
            if resultados:
                return render_template("wolfram.html", resultados=resultados, query=query)
            else:
                flash("No se encontraron resultados para tu consulta.")
                return render_template("wolfram.html")
                
        except requests.exceptions.Timeout:
            flash("La consulta tardó demasiado. Intenta con una consulta más simple.")
            return render_template("wolfram.html")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en request a Wolfram: {e}")
            flash("Error al consultar Wolfram Alpha. Intenta de nuevo.")
            return render_template("wolfram.html")
        except Exception as e:
            print(f"❌ Error general en Wolfram: {e}")
            flash("Error inesperado. Intenta de nuevo.")
            return render_template("wolfram.html")
    
    return render_template("wolfram.html")

@app.route("/examen_matematico/<int:numero>", methods=["GET", "POST"])
@login_required
def examen_matematico(numero):
    # Por ahora, mostrar mensaje de que no hay exámenes matemáticos
    # En el futuro, esto se conectará con Supabase para mostrar exámenes matemáticos
    flash("Los exámenes matemáticos estarán disponibles próximamente.")
    return render_template("examen_matematico.html")

@app.route("/resultado_matematico")
@login_required
def resultado_matematico():
    # Por ahora, mostrar mensaje de que no hay resultados matemáticos
    # En el futuro, esto se conectará con Supabase para mostrar resultados matemáticos
    flash("Los resultados matemáticos estarán disponibles próximamente.")
    return render_template("resultado_matematico.html")

@app.route('/como-funciona')
def como_funciona():
    return render_template("como_funciona.html")

@app.route("/planificacion", methods=["GET", "POST"])
@login_required
def planificacion():
    if request.method == "POST":
        try:
            # Obtener datos del formulario
            materia = request.form.get('materia', '')
            nivel = request.form.get('nivel', '')
            objetivo = request.form.get('objetivo', '')
            tiempo_disponible = request.form.get('tiempo_disponible', '')
            archivo = request.files.get('archivo')
            
            texto = ""
            if archivo and archivo.filename:
                # Procesar archivo según su tipo
                if archivo.filename.lower().endswith('.txt'):
                    texto = archivo.read().decode('utf-8')
                    
                elif archivo.filename.lower().endswith('.pdf'):
                    try:
                        pdf_reader = PyPDF2.PdfReader(archivo)
                        # Para planificación, usar todo el PDF
                        for page in pdf_reader.pages:
                            texto += page.extract_text() + "\n"
                    except Exception as e:
                        print(f"❌ Error procesando PDF: {e}")
                        flash("Error al procesar el archivo PDF. Intenta con otro archivo.")
                        return render_template("planificacion.html")
                        
                elif archivo.filename.lower().endswith('.docx'):
                    try:
                        doc = docx.Document(archivo)
                        for paragraph in doc.paragraphs:
                            if paragraph.text.strip():
                                texto += paragraph.text + "\n"
                    except Exception as e:
                        print(f"❌ Error procesando DOCX: {e}")
                        flash("Error al procesar el archivo DOCX. Intenta de nuevo.")
                        return render_template("planificacion.html")
            
            # Si no hay archivo, usar texto del formulario
            if not texto:
                texto = request.form.get('texto', '')
            
            if not texto.strip():
                flash("Por favor, proporciona un texto o sube un archivo.")
                return render_template("planificacion.html")
            
            # Generar plan de estudio
            prompt = f"""Genera un plan de estudio personalizado para {materia} de nivel {nivel}.

Objetivo: {objetivo}
Tiempo disponible: {tiempo_disponible}

Contenido a estudiar:
{texto}

Formato de respuesta (JSON):
{{
    "materia": "{materia}",
    "nivel": "{nivel}",
    "objetivo": "{objetivo}",
    "tiempo_disponible": "{tiempo_disponible}",
    "plan_estudio": [
        {{
            "semana": 1,
            "tema": "Tema a estudiar",
            "actividades": ["Actividad 1", "Actividad 2"],
            "tiempo_estimado": "2 horas",
            "objetivos_semana": "Objetivos específicos de la semana"
        }}
    ],
    "recomendaciones": ["Recomendación 1", "Recomendación 2"],
    "evaluacion": "Cómo evaluar el progreso"
}}

Asegúrate de que el plan sea realista, estructurado y adaptado al tiempo disponible."""
            
            # Llamar a OpenAI
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,
                    temperature=0.7,
                    timeout=90
                )
                
                # Procesar respuesta
                contenido = response.choices[0].message.content
                
                # Intentar extraer JSON
                try:
                    json_match = re.search(r'\{.*\}', contenido, re.DOTALL)
                    if json_match:
                        plan_data = json.loads(json_match.group())
                        session['plan_estudio'] = plan_data
                        return redirect(url_for('planificacion_resultado'))
                    else:
                        flash("Error al generar el plan de estudio. Intenta de nuevo.")
                        return render_template("planificacion.html")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    flash("Error al procesar la respuesta de la IA. Intenta de nuevo.")
                    return render_template("planificacion.html")
                    
            except Exception as e:
                print(f"❌ Error llamando a OpenAI: {e}")
                traceback.print_exc()
                flash("Error al generar el plan de estudio. Intenta de nuevo.")
                return render_template("planificacion.html")
                
        except Exception as e:
            print(f"❌ Error general en planificación: {e}")
            traceback.print_exc()
            flash("Error inesperado. Intenta de nuevo.")
            return render_template("planificacion.html")
    
    return render_template("planificacion.html")

@app.route("/planificacion-resultado")
@login_required
def planificacion_resultado():
    plan = session.get('plan_estudio')
    if not plan:
        flash("No hay plan de estudio para mostrar.")
        return redirect(url_for('planificacion'))
    
    return render_template("planificacion_resultado.html", plan=plan)

@app.route("/sitemap.xml")
def sitemap():
    """Generar sitemap XML para SEO"""
    urls = [
        {
            'loc': url_for('index', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '1.0'
        },
        {
            'loc': url_for('registro', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.8'
        },
        {
            'loc': url_for('generar', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '0.9'
        },
        {
            'loc': url_for('planificacion', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '0.9'
        },
        {
            'loc': url_for('como_funciona', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.7'
        }
    ]
    
    sitemap_xml = render_template('sitemap.xml', urls=urls)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route("/robots.txt")
def robots():
    """Servir robots.txt para SEO"""
    return send_from_directory('static', 'robots.txt')

@app.route("/google48eb92cb7318a041.html")
def google_verification():
    """Archivo de verificación de Google Search Console"""
    return send_from_directory('static', 'google48eb92cb7318a041.html')

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=debug)
