from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# from flask_sqlalchemy import SQLAlchemy  # Comentado: no se usa en Supabase
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from dotenv import load_dotenv
from supabase import create_client, Client
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

# Configuración de Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

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

# Modelo de Usuario para Supabase Auth (simplificado)
class SupabaseUser(UserMixin):
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.nombre = user_data.get('user_metadata', {}).get('nombre', user_data.get('email', '').split('@')[0])
        self.fecha_registro = datetime.fromisoformat(user_data.get('created_at', datetime.utcnow().isoformat()).replace('Z', '+00:00'))
        self.como_nos_conociste = user_data.get('user_metadata', {}).get('como_nos_conociste')
        self.uso_plataforma = user_data.get('user_metadata', {}).get('plataforma_uso')
        self.preguntas_completadas = bool(user_data.get('user_metadata', {}).get('preguntas_completadas', 0))
        self.provider = user_data.get('app_metadata', {}).get('provider', 'email')

@login_manager.user_loader
def load_user(user_id):
    try:
        if supabase:
            # Obtener usuario desde Supabase Auth
            response = supabase.auth.get_user()
            if response.user and str(response.user.id) == str(user_id):
                return SupabaseUser(response.user)
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

@app.route("/")
def index():
    return render_template("index.html")

# =====================================================
# NUEVAS RUTAS DE AUTENTICACIÓN CON SUPABASE AUTH
# =====================================================

@app.route("/auth/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        nombre = request.form["nombre"]
        
        try:
            if supabase:
                # Crear usuario con Supabase Auth
                user = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "nombre": nombre,
                            "preguntas_completadas": 0
                        }
                    }
                })
                
                if user.user:
                    print(f"✅ Usuario registrado exitosamente: {user.user.email}")
                    flash("Usuario registrado exitosamente. Revisa tu email para confirmar la cuenta.")
                    return redirect(url_for('login'))
                else:
                    print(f"❌ No se pudo crear usuario")
                    flash("Error al registrar usuario. Intenta de nuevo.")
                    
        except Exception as e:
            print(f"❌ Error en signup: {e}")
            if "already registered" in str(e).lower():
                flash("El email ya está registrado. Por favor, usa otro email.")
            else:
                flash("Error al registrar usuario. Intenta de nuevo.")
                
        return render_template("registro.html")
    
    return render_template("registro.html")

@app.route("/auth/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        
        try:
            if supabase:
                # Iniciar sesión con Supabase Auth
                user = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                if user.user:
                    print(f"✅ Usuario autenticado exitosamente: {user.user.email}")
                    
                    # Guardar usuario en sesión de Flask
                    session['user_id'] = user.user.id
                    session['user_email'] = user.user.email
                    session['user_nombre'] = user.user.user_metadata.get('nombre', email.split('@')[0])
                    
                    print(f"✅ Usuario logueado en sesión Flask: {user.user.email}")
                    
                    # Verificar si el usuario ya completó las preguntas
                    preguntas_completadas = user.user.user_metadata.get('preguntas_completadas', 0)
                    if not preguntas_completadas:
                        print(f"🔄 Redirigiendo a preguntas de usuario")
                        return redirect(url_for("preguntas_usuario"))
                    
                    next_page = request.args.get('next')
                    if next_page:
                        print(f"🔄 Redirigiendo a: {next_page}")
                        return redirect(next_page)
                    else:
                        print(f"🔄 Redirigiendo a generar examen")
                        return redirect(url_for('generar'))
                else:
                    print(f"❌ No se pudo autenticar usuario")
                    flash("Email o contraseña incorrectos")
                    
        except Exception as e:
            print(f"❌ Error en signin: {e}")
            flash("Email o contraseña incorrectos")
            
        return render_template("login.html")
    
    return render_template("login.html")

@app.route("/auth/google")
def google_auth():
    """Iniciar autenticación con Google"""
    try:
        if supabase:
            # Obtener URL de autenticación de Google
            response = supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": f"{request.host_url}auth/callback"
                }
            })
            
            if response.url:
                return redirect(response.url)
            else:
                flash("Error al iniciar autenticación con Google")
                return redirect(url_for('login'))
                
    except Exception as e:
        print(f"Error iniciando Google auth: {e}")
        flash("Error al conectar con Google")
        return redirect(url_for('login'))

@app.route("/auth/callback")
def auth_callback():
    """Callback después de autenticación OAuth"""
    try:
        if supabase:
            # Obtener parámetros de la URL (importante para OAuth)
            code = request.args.get('code')
            error = request.args.get('error')
            
            print(f"🔍 Callback recibido - Code: {code}, Error: {error}")
            
            if error:
                print(f"❌ Error en OAuth: {error}")
                flash(f"Error en la autenticación: {error}")
                return redirect(url_for('login'))
            
            if code:
                # Intercambiar código por sesión
                try:
                    print(f"🔄 Intercambiando código por sesión...")
                    response = supabase.auth.exchange_code_for_session(code)
                    
                    if response.session and response.user:
                        print(f"✅ Sesión obtenida para usuario: {response.user.email}")
                        
                        # Guardar usuario en sesión de Flask
                        session['user_id'] = response.user.id
                        session['user_email'] = response.user.email
                        
                        # Verificar que user_metadata sea un diccionario
                        if hasattr(response.user, 'user_metadata') and isinstance(response.user.user_metadata, dict):
                            session['user_nombre'] = response.user.user_metadata.get('nombre', response.user.email.split('@')[0])
                        else:
                            session['user_nombre'] = response.user.email.split('@')[0]
                        
                        print(f"✅ Usuario autenticado exitosamente: {response.user.email}")
                        
                        # Verificar si el usuario ya completó las preguntas
                        if hasattr(response.user, 'user_metadata') and isinstance(response.user.user_metadata, dict):
                            preguntas_completadas = response.user.user_metadata.get('preguntas_completadas', 0)
                        else:
                            preguntas_completadas = 0
                            
                        if not preguntas_completadas:
                            print(f"🔄 Redirigiendo a preguntas de usuario")
                            return redirect(url_for("preguntas_usuario"))
                        
                        print(f"🔄 Redirigiendo a generar examen")
                        return redirect(url_for('generar'))
                    else:
                        print(f"❌ No se pudo obtener sesión del usuario")
                        flash("Error en la autenticación con Google")
                        return redirect(url_for('login'))
                        
                except Exception as e:
                    print(f"❌ Error intercambiando código por sesión: {e}")
                    flash("Error en la autenticación con Google")
                    return redirect(url_for('login'))
            else:
                print(f"❌ No se recibió código de autorización")
                flash("Error en la autenticación con Google")
                return redirect(url_for('login'))
                
    except Exception as e:
        print(f"❌ Error en auth callback: {e}")
        flash("Error en la autenticación")
        return redirect(url_for('login'))

@app.route("/auth/logout")
def auth_logout():
    """Cerrar sesión con Supabase Auth"""
    try:
        if supabase:
            # Cerrar sesión en Supabase
            supabase.auth.sign_out()
            print(f"✅ Usuario cerró sesión en Supabase")
            
    except Exception as e:
        print(f"❌ Error en logout: {e}")
    
    # Limpiar sesión de Flask
    session.clear()
    print(f"✅ Sesión de Flask limpiada")
    return redirect(url_for("index"))

@app.route("/registro", methods=["GET", "POST"])
def registro():
    # Redirigir a la nueva ruta de Supabase Auth
    return redirect(url_for('signup'))

@app.route("/login", methods=["GET", "POST"])
def login():
    # Redirigir a la nueva ruta de Supabase Auth
    return redirect(url_for('signin'))

@app.route("/preguntas-usuario", methods=["GET", "POST"])
def preguntas_usuario():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    
    if request.method == "POST":
        como_nos_conociste = request.form.get("como_nos_conociste")
        uso_plataforma = request.form.get("uso_plataforma")

        try:
            if supabase:
                # Obtener usuario actual
                current_user = get_current_user()
                
                update_data = {
                    'como_nos_conociste': como_nos_conociste,
                    'plataforma_uso': uso_plataforma,
                    'preguntas_completadas': 1,
                    'ultima_actividad': datetime.utcnow().isoformat()
                }

                # Actualizar metadata del usuario en Supabase Auth
                supabase.auth.update_user({
                    "data": {
                        "como_nos_conociste": como_nos_conociste,
                        "plataforma_uso": uso_plataforma,
                        "preguntas_completadas": 1
                    }
                })

                flash("Información guardada exitosamente!")
                return redirect(url_for('generar'))

        except Exception as e:
            print(f"Error guardando preguntas: {e}")
            flash("Error al guardar información. Intenta de nuevo.")

        return render_template("preguntas_usuario.html")

    return render_template("preguntas_usuario.html")

@app.route("/logout")
def logout():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    
    try:
        if supabase:
            current_user = get_current_user()
            log_data = {
                'usuario_id': current_user['id'],
                'tipo_actividad': 'logout',
                'fecha_actividad': datetime.utcnow().isoformat(),
                'detalles': {'accion': 'Usuario cerró sesión'},
                'ip_address': request.remote_addr
            }
            supabase.table('logs_actividad').insert(log_data).execute()
    except Exception as e:
        print(f"Error logging logout: {e}")

    # Limpiar sesión de Flask
    session.clear()
    return redirect(url_for("index"))

@app.route("/perfil")
def perfil():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    
    return render_template("perfil.html")

@app.route("/generar", methods=["GET", "POST"])
def generar():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    if request.method == "GET":
        return render_template("generar.html")

    # Limpiar datos temporales de la sesión antes de generar un nuevo examen
    session.pop("preguntas", None)
    session.pop("respuestas", None)
    session.pop("pregunta_times", None)
    session.pop("start_time", None)
    session.pop("last_question_time", None)

    nivel = request.form["nivel"]
    cantidad = int(request.form["cantidad"])
    formato = request.form["formato"]
    archivo = request.files.get("archivo")
    tema = request.form.get("tema")
    cantidad_opciones = request.form.get("cantidad_opciones", "4")
    instrucciones_desarrollo = request.form.get("instrucciones_desarrollo", "")
    instrucciones_vf = request.form.get("instrucciones_vf", "")
    temas_math = request.form.getlist("temas")
    tema_personalizado = request.form.get("tema_personalizado", "")

    # --- NUEVO: Ejercicios matemáticos ---
    if formato == "ejercicios matematicos":
        temas = temas_math.copy()
        if tema_personalizado:
            temas.append(tema_personalizado)
        if not temas:
            return "Debes seleccionar al menos un tema de matemática."
        ejercicios = []
        for i in range(cantidad):
            # Generar enunciado con GPT-4
            prompt = (
                f"Generá un ejercicio matemático de nivel {nivel} sobre el tema '{temas[i % len(temas)]}'. "
                "El ejercicio debe tener UNA sola consigna, ser claro, concreto y estar expresado como una expresión matemática o pregunta directa, NO como un problema con partes a) y b). "
                "Incluí la expresión matemática principal entre corchetes al final, por ejemplo: [expresión]. No incluyas la solución ni la respuesta."
            )
            try:
                enunciado_gpt = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Sos un generador de ejercicios matemáticos para exámenes."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=120,
                    timeout=30
                ).choices[0].message.content.strip()
            except Exception as e:
                enunciado_gpt = f"[Error al generar enunciado: {str(e)}]"
            # Extraer expresión entre corchetes
            match = re.search(r"\[(.*?)\]", enunciado_gpt)
            expresion = match.group(1) if match else ""
            # Limpiar delimitadores LaTeX si existen
            expresion = expresion.replace('\\(', '').replace('\\)', '').strip()
            enunciado = enunciado_gpt.replace(f'[{match.group(1)}]', '').strip() if match else enunciado_gpt
            # Obtener imagen y solución con Wolfram usando la expresión
            try:
                url = "https://api.wolframalpha.com/v2/query"
                params = {
                    "input": expresion,
                    "appid": app_id,
                    "format": "image,plaintext"
                }
                resp = requests.get(url, params=params, timeout=30)
                solucion = ""
                pods = []
                img_enunciado = None
                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.text)
                    for pod in root.findall(".//pod"):
                        pod_title = pod.attrib.get("title", "")
                        subpod = pod.find("subpod")
                        pod_plaintext = subpod.findtext("plaintext") if subpod is not None else None
                        pod_img = None
                        if subpod is not None:
                            img_tag = subpod.find("img")
                            if img_tag is not None:
                                pod_img = img_tag.attrib.get("src")
                        # Guardar la imagen del enunciado (primer pod Input)
                        if not img_enunciado and pod_title.lower() in ["input", "entrada"] and pod_img:
                            img_enunciado = pod_img
                        if pod_title.lower() in ["result", "resultado", "solution", "solución"] and pod_plaintext:
                            solucion = pod_plaintext
                        if pod_plaintext or pod_img:
                            pods.append({"title": pod_title, "plaintext": pod_plaintext, "img": pod_img})
                else:
                    solucion = "[Error al consultar Wolfram Alpha]"
                    img_enunciado = None
            except Exception as e:
                solucion = f"[Error al consultar Wolfram: {str(e)}]"
                pods = []
                img_enunciado = None
            ejercicios.append({
                "enunciado": enunciado,
                "expresion": expresion,
                "img_enunciado": img_enunciado,
                "solucion": solucion,
                "pods": pods,
                "respuesta_usuario": ""
            })
        session["ejercicios_matematicos"] = ejercicios
        session["start_time"] = time.time()
        return redirect(url_for("examen_matematico", numero=0))
    # --- FIN NUEVO ---

    texto = ""
    if archivo and archivo.filename:
        if archivo.filename.endswith(".txt"):
            print(f"\n--- PROCESANDO ARCHIVO TXT: {archivo.filename} ---")
            texto = archivo.read().decode("utf-8")
            print(f"Total de caracteres: {len(texto)}")
            print(f"Primeros 500 caracteres: {texto[:500]}...")
            print("--- FIN ARCHIVO TXT ---\n")
        elif archivo.filename.endswith(".pdf"):
            pdf_stream = BytesIO(archivo.read())
            reader = PyPDF2.PdfReader(pdf_stream)
            print(f"\n--- PROCESANDO PDF: {archivo.filename} ---")
            print(f"Total de páginas: {len(reader.pages)}")
            
            texto = ""
            max_pages = min(len(reader.pages), 7)  # 🎯 LÍMITE: Solo las primeras 7 páginas
            print(f"Procesando primeras {max_pages} páginas de {len(reader.pages)} totales")
            
            for i in range(max_pages):
                try:
                    page_text = reader.pages[i].extract_text()
                    if page_text and page_text.strip():
                        texto += f"\n--- PÁGINA {i+1} ---\n{page_text.strip()}\n"
                        print(f"Página {i+1}: {len(page_text)} caracteres extraídos")
                    else:
                        print(f"Página {i+1}: Sin texto extraído (página vacía o imagen)")
                except Exception as e:
                    print(f"Página {i+1}: Error al extraer texto - {str(e)}")
            
            if len(reader.pages) > max_pages:
                print(f"⚠️  NOTA: Solo se procesaron las primeras {max_pages} páginas de {len(reader.pages)}")
                print(f"💡 Para procesar más páginas, considera dividir el PDF en archivos más pequeños")
            
            # Si no se extrajo texto, intentar métodos alternativos
            if not texto.strip():
                print("⚠️  ADVERTENCIA: No se pudo extraer texto del PDF")
                print("💡 Posibles causas:")
                print("   - PDF escaneado (solo imágenes)")
                print("   - PDF con protección DRM")
                print("   - PDF con fuentes especiales")
                print("   - PDF con layout complejo")
                print("💡 Soluciones:")
                print("   - Usar un PDF con texto seleccionable")
                print("   - Convertir el PDF a texto primero")
                print("   - Usar un archivo TXT o DOCX en su lugar")
            
            print(f"\n--- RESUMEN PDF ---")
            print(f"Archivo: {archivo.filename}")
            print(f"Páginas procesadas: {len(reader.pages)}")
            print(f"Total de caracteres extraídos: {len(texto)}")
            if texto.strip():
                print(f"Primeros 500 caracteres: {texto[:500]}...")
            else:
                print("❌ NO SE EXTRAJO TEXTO DEL PDF")
            print("--- FIN RESUMEN PDF ---\n")
        elif archivo.filename.endswith(".docx"):
            print(f"\n--- PROCESANDO ARCHIVO DOCX: {archivo.filename} ---")
            docx_stream = BytesIO(archivo.read())
            doc = docx.Document(docx_stream)
            print(f"Total de párrafos: {len(doc.paragraphs)}")
            
            texto = ""
            max_paragraphs = min(len(doc.paragraphs), 50)  # 🎯 LÍMITE: Solo los primeros 50 párrafos (equivalente a ~7 páginas)
            print(f"Procesando primeros {max_paragraphs} párrafos de {len(doc.paragraphs)} totales")
            
            for i in range(max_paragraphs):
                if doc.paragraphs[i].text.strip():
                    texto += doc.paragraphs[i].text + "\n"
                    print(f"Párrafo {i+1}: {len(doc.paragraphs[i].text)} caracteres")
            
            if len(doc.paragraphs) > max_paragraphs:
                print(f"⚠️  NOTA: Solo se procesaron los primeros {max_paragraphs} párrafos de {len(doc.paragraphs)}")
                print(f"💡 Para procesar más contenido, considera dividir el documento en archivos más pequeños")
            
            print(f"\n--- RESUMEN DOCX ---")
            print(f"Archivo: {archivo.filename}")
            print(f"Párrafos procesados: {len(doc.paragraphs)}")
            print(f"Total de caracteres extraídos: {len(texto)}")
            print(f"Primeros 500 caracteres: {texto[:500]}...")
            print("--- FIN RESUMEN DOCX ---\n")
        print("\n--- TEXTO EXTRAÍDO DEL ARCHIVO (GENERADOR) ---\n", texto, "\n--- FIN TEXTO EXTRAÍDO ---\n")
        
        # Validar que se extrajo texto del archivo
        if archivo and archivo.filename and not texto.strip():
            if archivo.filename.endswith(".pdf"):
                return render_template("generar.html", mensaje_error="No se pudo extraer texto del PDF. Posibles causas: PDF escaneado, con protección DRM, o con fuentes especiales. Intenta con un PDF que tenga texto seleccionable o usa un archivo TXT/DOCX.")
            else:
                return render_template("generar.html", mensaje_error="No se pudo extraer texto del archivo. Verifica que el archivo contenga texto legible.")
    elif tema:
        texto = f"Tema: {tema}."
    else:
        return "Debe ingresar un tema o subir un archivo."

    if formato == "multiple choice":
        prompt = (
            f"Generá {cantidad} preguntas de examen en formato opción múltiple, todas directamente relacionadas con el siguiente tema, para nivel {nivel}. "
            f"Cada pregunta debe comenzar con 'Enunciado X: ...', incluir {cantidad_opciones} opciones (a, b, c, d" + (", e" if cantidad_opciones == "5" else "") + (", c" if cantidad_opciones == "3" else "") + ") en líneas separadas, asegurando que solo una opción sea correcta y las otras sean plausibles y relacionadas con el tema (no obvias ni irrelevantes). "
            "Al final de cada pregunta, escribí: Respuesta: x. Evitá preguntas demasiado generales o de sentido común."
        )
    elif formato == "verdadero o falso":
        prompt = (
            f"Generá {cantidad} preguntas en formato verdadero o falso, todas directamente relacionadas con el siguiente tema, para nivel {nivel}. "
            "Cada pregunta debe comenzar con 'Enunciado X: Seleccionar verdadero o falso: ...', ser conceptualmente profunda y no trivial, y terminar con 'Respuesta: Verdadero' o 'Respuesta: Falso'. "
            "Evitá afirmaciones obvias o que no requieran conocimiento del tema. "
            + (f"Instrucciones adicionales: {instrucciones_vf}" if instrucciones_vf else "")
        )
    else:
        prompt = (
            f"Generá {cantidad} preguntas de examen abiertas para que el estudiante responda desarrollando, basadas en el siguiente tema, en orden aleatorio, para nivel {nivel}. "
            "Comenzá cada una con 'Enunciado X: ...'. No incluyas opciones ni respuesta. "
            + (f"Instrucciones adicionales: {instrucciones_desarrollo}" if instrucciones_desarrollo else "")
        )

    # LOG: Mostrar el prompt enviado a la IA
    print("\n--- PROMPT ENVIADO A LA IA ---\n", prompt + "\n\n" + texto[:3000], "\n--- FIN PROMPT ---\n")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sos un generador de exámenes"},
                {"role": "user", "content": prompt + "\n\n" + texto[:3000]}
            ],
            max_tokens=3000,
            timeout=60
        )
        preguntas_raw = response.choices[0].message.content

        # Log para depuración: ver qué devuelve la IA
        print("\n\n--- RESPUESTA IA RAW ---\n", preguntas_raw, "\n--- FIN RESPUESTA ---\n\n")

        if preguntas_raw:
            # Dividir por líneas y procesar manualmente
            lineas = preguntas_raw.strip().split('\n')
            bloques = []
            bloque_actual = []
            en_pregunta = False
            
            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                
                # Detectar inicio de nueva pregunta
                if linea.startswith('**Enunciado') or linea.startswith('Enunciado'):
                    if bloque_actual:
                        bloques.append('\n'.join(bloque_actual))
                        bloque_actual = []
                    en_pregunta = True
                    bloque_actual.append(linea)
                elif en_pregunta:
                    bloque_actual.append(linea)
                    # Detectar fin de pregunta (cuando encontramos Respuesta:)
                    if linea.startswith('Respuesta:'):
                        en_pregunta = False
            
            # Agregar el último bloque
            if bloque_actual:
                bloques.append('\n'.join(bloque_actual))
            
            print(f"\n--- BLOQUES ENCONTRADOS: {len(bloques)} ---\n")
            for i, bloque in enumerate(bloques):
                print(f"Bloque {i+1}: {bloque[:100]}...")
        else:
            bloques = []
            print("\n--- NO SE ENCONTRARON BLOQUES ---\n")
        
        preguntas = []
        for bloque in bloques:
            lineas = bloque.strip().split("\n")
            enunciado = next((l for l in lineas if l.lower().startswith("enunciado")), lineas[0])
            opciones = []
            respuesta = "indefinida"
            # tipo = "desarrollo"  # El tipo ahora se fuerza según el formato seleccionado

            # Determinar qué opciones buscar según la cantidad configurada
            opciones_buscar = []
            if cantidad_opciones == "3":
                opciones_buscar = ["a)", "b)", "c)"]
            elif cantidad_opciones == "5":
                opciones_buscar = ["a)", "b)", "c)", "d)", "e)"]
            else:  # 4 opciones por defecto
                opciones_buscar = ["a)", "b)", "c)", "d)"]

            for l in lineas:
                l_strip = l.strip().lower()
                if l_strip.startswith("respuesta"):
                    raw_resp = l.split(":")[-1].strip().lower().rstrip('.')  # Remover punto al final
                    if raw_resp in ["verdadero", "falso"]:
                        respuesta = raw_resp
                    elif raw_resp in ["a", "b", "c", "d", "e"]:
                        respuesta = raw_resp
                if any(l_strip.startswith(op) for op in opciones_buscar):
                    opciones.append(l.strip())

            # Forzar el tipo según la selección del usuario
            if formato == "multiple choice":
                tipo = "multiple"
            elif formato == "verdadero o falso":
                tipo = "vf"
            else:
                tipo = "desarrollo"

            if tipo in ["multiple", "vf"] and respuesta == "indefinida":
                print(f"\n--- PREGUNTA DESCARTADA: {enunciado[:50]}... ---\n")
                continue

            preguntas.append({"enunciado": enunciado, "opciones": opciones, "respuesta": respuesta, "tipo": tipo, "tema": "General"})
            print(f"\n--- PREGUNTA AGREGADA: {enunciado[:50]}... (tipo: {tipo}, respuesta: {respuesta}) ---\n")

        # Validar que haya preguntas y que todos los enunciados sean válidos
        if not preguntas or any(not p["enunciado"].strip() for p in preguntas):
            mensaje_error = "No se pudieron generar preguntas válidas. Verificá el texto, el formato o intentá nuevamente."
            print(f"\n--- ERROR: {mensaje_error} ---\n")
            return render_template("generar.html", mensaje_error=mensaje_error)

        print(f"\n--- PREGUNTAS FINALES: {len(preguntas)} ---\n")
        session["preguntas"] = preguntas
        session["respuestas"] = ["" for _ in preguntas]
        session["start_time"] = time.time()
        session["pregunta_times"] = []
        session["last_question_time"] = time.time()

    except Exception as e:
        print(f"\n--- EXCEPCIÓN: {str(e)} ---\n")
        import traceback
        traceback.print_exc()
        
        # Manejo específico para timeouts
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            return render_template("generar.html", mensaje_error="La generación tardó demasiado tiempo en Heroku. Por favor, intenta con un archivo más pequeño, menos preguntas, o usa la versión local.")
        else:
            return render_template("generar.html", mensaje_error=f"Error al generar preguntas: {str(e)}. Por favor, intenta nuevamente.")

    return redirect(url_for('pregunta', numero=0))

@app.route("/pregunta/<int:numero>", methods=["GET", "POST"])
def pregunta(numero):
    preguntas = session.get("preguntas", [])
    respuestas = session.get("respuestas", [])

    if numero >= len(preguntas):
        return redirect(url_for('resultado'))

    if request.method == "POST":
        respuesta_usuario = request.form.get("respuesta", "")
        respuestas[numero] = respuesta_usuario
        session["respuestas"] = respuestas

        now = time.time()
        duracion = now - session["last_question_time"]
        session["pregunta_times"].append(round(duracion, 2))
        session["last_question_time"] = now

        return redirect(url_for('pregunta', numero=numero + 1))

    pregunta = preguntas[numero]
    respuesta_actual = respuestas[numero]
    return render_template("examen.html", pregunta=pregunta, numero=numero + 1, total=len(preguntas), actual=numero, respuesta_actual=respuesta_actual)

@app.route("/resultado")
def resultado():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    preguntas = session.get("preguntas", [])
    respuestas = session.get("respuestas", [])
    tiempos = session.get("pregunta_times", [])

    feedbacks = []
    correctas = 0
    parciales = 0
    incorrectas = 0
    temas_fallidos = {}
    preguntas_falladas = []

    respuestas_texto_usuario = []
    respuestas_texto_correcta = []
    for i in range(len(preguntas)):
        pregunta = preguntas[i]
        respuesta_usuario = respuestas[i]
        texto_usuario = ""
        texto_correcta = ""
        if pregunta["tipo"] == "multiple":
            for op in pregunta["opciones"]:
                if respuesta_usuario and op.lower().startswith(f"{respuesta_usuario})"):
                    texto_usuario = op[2:].strip()
                if op.lower().startswith(f"{pregunta['respuesta']})"):
                    texto_correcta = op[2:].strip()
        respuestas_texto_usuario.append(texto_usuario)
        respuestas_texto_correcta.append(texto_correcta)

    for i in range(len(preguntas)):
        pregunta = preguntas[i]
        respuesta_usuario = respuestas[i]
        feedback = ""
        explicacion_ia = ""

        if pregunta["tipo"] in ["multiple", "vf"]:
            correcta = pregunta["respuesta"]
            texto_correcta = ""
            texto_usuario = ""
            if pregunta["tipo"] == "multiple":
                for op in pregunta["opciones"]:
                    if op.lower().startswith(f"{correcta})"):
                        texto_correcta = op[2:].strip()
                    if respuesta_usuario and op.lower().startswith(f"{respuesta_usuario})"):
                        texto_usuario = op[2:].strip()
            if respuesta_usuario == correcta:
                feedback = f"✔️ CORRECTA"
                correctas += 1
            else:
                # --- FEEDBACK IA BREVE ---
                try:
                    prompt_ia = (
                        f"Sos un profesor que explica brevemente por qué una respuesta es correcta en un examen. "
                        f"Esta es la pregunta de examen: {pregunta['enunciado']}\n"
                        f"El alumno respondió: {respuesta_usuario}\n"
                        f"La respuesta correcta es: {correcta}\n"
                        f"Explicá en 1-2 frases, de forma breve y clara, por qué la respuesta correcta es la que corresponde. No repitas el enunciado completo."
                    )
                    explicacion_ia = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Sos un profesor que explica brevemente por qué una respuesta es correcta en un examen."},
                            {"role": "user", "content": prompt_ia}
                        ],
                        max_tokens=120,
                        timeout=30
                    ).choices[0].message.content.strip()
                except Exception as e:
                    explicacion_ia = "(No se pudo generar explicación IA)"
                if pregunta["tipo"] == "multiple":
                    feedback = f"❌ INCORRECTA.\nTu respuesta fue '{respuesta_usuario}': \"{texto_usuario}\"\nLa correcta era '{correcta}': \"{texto_correcta}\"\n<b>Por qué: </b>{explicacion_ia}"
                else:
                    feedback = f"❌ INCORRECTA. Tu respuesta fue '{respuesta_usuario}', la correcta era '{correcta}'.\n<b>Por qué: </b>{explicacion_ia}"
                incorrectas += 1
                temas_fallidos[pregunta["tema"]] = temas_fallidos.get(pregunta["tema"], 0) + 1
                preguntas_falladas.append({
                    "enunciado": pregunta["enunciado"],
                    "respuesta_usuario": respuesta_usuario,
                    "respuesta_correcta": correcta
                })
        else:
            prompt = (
                f"Pregunta: {pregunta['enunciado']}\n"
                f"Respuesta del alumno: {respuesta_usuario}\n"
                "Evaluá si la respuesta es correcta, incorrecta o parcialmente correcta y explicá brevemente por qué. "
                "Al final, decí solo CORRECTA, INCORRECTA o PARCIALMENTE CORRECTA."
            )
            try:
                feedback_raw = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Sos un corrector de exámenes"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    timeout=45
                ).choices[0].message.content

                if feedback_raw:
                    f_lower = feedback_raw.lower()
                else:
                    f_lower = ""

                if "parcialmente correcta" in f_lower:
                    feedback = f"⚠️ PARCIALMENTE CORRECTA\n{feedback_raw}"
                    parciales += 1
                    temas_fallidos[pregunta["tema"]] = temas_fallidos.get(pregunta["tema"], 0) + 1
                    preguntas_falladas.append({
                        "enunciado": pregunta["enunciado"],
                        "respuesta_usuario": respuesta_usuario,
                        "respuesta_correcta": "(respuesta abierta)"
                    })
                elif "incorrecta" in f_lower:
                    feedback = f"❌ INCORRECTA\n{feedback_raw}"
                    incorrectas += 1
                    temas_fallidos[pregunta["tema"]] = temas_fallidos.get(pregunta["tema"], 0) + 1
                    preguntas_falladas.append({
                        "enunciado": pregunta["enunciado"],
                        "respuesta_usuario": respuesta_usuario,
                        "respuesta_correcta": "(respuesta abierta)"
                    })
                elif "correcta" in f_lower:
                    feedback = f"✔️ CORRECTA\n{feedback_raw}"
                    correctas += 1
                else:
                    feedback = f"⚠️ No se pudo clasificar la respuesta\n{feedback_raw}"
            except Exception as e:
                feedback = f"Error al corregir: {str(e)}"

        feedbacks.append(feedback)

    total = len(preguntas)
    nota = round((correctas + parciales * 0.5) / total * 10, 2)

    # --- FEEDBACK GENERAL IA ---
    if preguntas_falladas:
        try:
            prompt_general = (
                "Sos un tutor experto en ayudar a estudiantes a mejorar en exámenes. "
                "Te paso una lista de preguntas que el estudiante respondió incorrectamente o parcialmente, junto con su respuesta y la respuesta correcta. "
                "En base a estos errores, respondé en segunda persona y comenzá tu respuesta con 'Te recomendamos enfocarte en...'. "
                "Sé concreto, breve (2-3 frases) y no repitas el enunciado de las preguntas.\n\nPreguntas falladas:\n"
            )
            for pf in preguntas_falladas:
                prompt_general += f"- Enunciado: {pf['enunciado']}\n  Respuesta del alumno: {pf['respuesta_usuario']}\n  Respuesta correcta: {pf['respuesta_correcta']}\n"
            feedback_general = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sos un tutor experto en ayudar a estudiantes a mejorar en exámenes."},
                    {"role": "user", "content": prompt_general}
                ],
                max_tokens=200,
                timeout=45
            ).choices[0].message.content.strip()
        except Exception as e:
            feedback_general = "(No se pudo generar feedback personalizado)"
    else:
        feedback_general = "¡Excelente! No se detectaron temas con errores frecuentes."

    resumen = {
        "correctas": correctas,
        "parciales": parciales,
        "incorrectas": incorrectas,
        "total": total,
        "nota": nota,
        "tiempo_total": round(time.time() - session["start_time"], 2),
        "tiempos_por_pregunta": tiempos,
        "feedback_general": feedback_general
    }

    # GUARDAR EN BASE DE DATOS SUPABASE
    if is_authenticated() and supabase:
        try:
            current_user = get_current_user()
            print(f"\n🔍 INTENTANDO GUARDAR EXAMEN EN SUPABASE...")
            print(f"Usuario: {current_user['email']} (ID: {current_user['id']})")
            print(f"Nota: {nota}/10")
            print(f"Tiempo: {resumen['tiempo_total']}s")
            
            # Verificar que las tablas existan
            try:
                # Verificar tabla examenes
                examenes_check = supabase.table('examenes').select('id').limit(1).execute()
                print(f"✅ Tabla 'examenes' existe")
                
                # Verificar tabla preguntas_examen
                preguntas_check = supabase.table('preguntas_examen').select('id').limit(1).execute()
                print(f"✅ Tabla 'preguntas_examen' existe")
                
                # Verificar tabla usuarios
                usuarios_check = supabase.table('usuarios').select('id').eq('id', current_user['id']).execute()
                print(f"✅ Usuario encontrado en tabla 'usuarios'")
                
            except Exception as e:
                print(f"❌ Error verificando tablas: {e}")
                return render_template("resultado_abierto.html", respuestas=respuestas, preguntas=preguntas, feedbacks=feedbacks, resumen=resumen, respuestas_texto_usuario=respuestas_texto_usuario, respuestas_texto_correcta=respuestas_texto_correcta)
            
            # Guardar examen principal
            examen_data = {
                'usuario_id': current_user['id'],
                'titulo': f'Examen de {preguntas[0].get("tema", "General")}',
                'materia': preguntas[0].get("tema", "General"),
                'fecha_creacion': datetime.utcnow().isoformat(),
                'fecha_rendido': datetime.utcnow().isoformat(),
                'preguntas': json.dumps([p['enunciado'] for p in preguntas]),
                'respuestas': json.dumps(respuestas),
                'nota': nota,
                'tiempo_duracion': int(float(resumen["tiempo_total"])),
                'estado': 'rendido',
                'tiempo_total_segundos': int(float(resumen["tiempo_total"])),
                # Agregar métricas detalladas
                'correctas': correctas,
                'parciales': parciales,
                'incorrectas': incorrectas,
                'total_preguntas': total,
                # Agregar feedback general
                'feedback_general': feedback_general
            }
            
            print(f"📊 Datos del examen: {examen_data}")
            
            examen_response = supabase.table('examenes').insert(examen_data).execute()
            
            if examen_response.data:
                examen_id = examen_response.data[0]['id']
                print(f"✅ Examen guardado con ID: {examen_id}")
                
                # Guardar cada pregunta individual
                print(f"📝 Guardando {len(preguntas)} preguntas...")
                for i, pregunta in enumerate(preguntas):
                    pregunta_data = {
                        'examen_id': examen_id,
                        'enunciado': pregunta['enunciado'],
                        'opciones': json.dumps(pregunta.get('opciones', [])),
                        'respuesta_usuario': respuestas[i],
                        'respuesta_correcta': pregunta['respuesta'],
                        'tipo': pregunta['tipo'],
                        'tema': pregunta.get('tema', 'General'),
                        'orden': i + 1
                    }
                    
                    print(f"  Pregunta {i+1}: {pregunta['enunciado'][:50]}...")
                    pregunta_response = supabase.table('preguntas_examen').insert(pregunta_data).execute()
                    
                    if pregunta_response.data:
                        print(f"    ✅ Pregunta {i+1} guardada")
                    else:
                        print(f"    ❌ Error guardando pregunta {i+1}")
                
                # Actualizar estadísticas del usuario
                try:
                    # Obtener el usuario actual
                    user_response = supabase.table('usuarios').select('total_examenes_rendidos, correctas_total, parciales_total, incorrectas_total').eq('id', current_user['id']).execute()
                    if user_response.data:
                        user_data = user_response.data[0]
                        total_actual = user_data.get('total_examenes_rendidos', 0)
                        correctas_actual = user_data.get('correctas_total', 0)
                        parciales_actual = user_data.get('parciales_total', 0)
                        incorrectas_actual = user_data.get('incorrectas_total', 0)
                        
                        nuevo_total = total_actual + 1
                        nuevo_correctas = correctas_actual + correctas
                        nuevo_parciales = parciales_actual + parciales
                        nuevo_incorrectas = incorrectas_actual + incorrectas
                        
                        # Actualizar el contador
                        supabase.table('usuarios').update({
                            'total_examenes_rendidos': nuevo_total,
                            'correctas_total': nuevo_correctas,
                            'parciales_total': nuevo_parciales,
                            'incorrectas_total': nuevo_incorrectas,
                            'ultima_actividad': datetime.utcnow().isoformat()
                        }).eq('id', current_user['id']).execute()
                        
                        print(f"✅ Estadísticas actualizadas: {nuevo_total} exámenes, {nuevo_correctas} correctas, {nuevo_parciales} parciales, {nuevo_incorrectas} incorrectas")
                except Exception as e:
                    print(f"⚠️ Error actualizando estadísticas: {e}")
                
                # Guardar estadísticas diarias
                try:
                    fecha_hoy = datetime.utcnow().date().isoformat()
                    
                    # Verificar si ya existen estadísticas para hoy
                    stats_response = supabase.table('estadisticas_usuarios').select('*').eq('usuario_id', current_user['id']).eq('fecha_estadistica', fecha_hoy).execute()
                    
                    if stats_response.data:
                        # Actualizar estadísticas existentes
                        stats_id = stats_response.data[0]['id']
                        supabase.table('estadisticas_usuarios').update({
                            'examenes_rendidos_hoy': stats_response.data[0].get('examenes_rendidos_hoy', 0) + 1,
                            'preguntas_correctas_hoy': stats_response.data[0].get('preguntas_correctas_hoy', 0) + correctas,
                            'preguntas_incorrectas_hoy': stats_response.data[0].get('preguntas_incorrectas_hoy', 0) + incorrectas,
                            'tiempo_total_estudio_hoy': stats_response.data[0].get('tiempo_total_estudio_hoy', 0) + int(float(resumen["tiempo_total"])),
                            'materias_estudiadas_hoy': [preguntas[0].get("tema", "General")]
                        }).eq('id', stats_id).execute()
                    else:
                        # Crear nuevas estadísticas para hoy
                        supabase.table('estadisticas_usuarios').insert({
                            'usuario_id': current_user['id'],
                            'fecha_estadistica': fecha_hoy,
                            'examenes_rendidos_hoy': 1,
                            'preguntas_correctas_hoy': correctas,
                            'preguntas_incorrectas_hoy': incorrectas,
                            'tiempo_total_estudio_hoy': int(float(resumen["tiempo_total"])),
                            'materias_estudiadas_hoy': [preguntas[0].get("tema", "General")]
                        }).execute()
                    
                    print(f"✅ Estadísticas diarias guardadas para {fecha_hoy}")
                except Exception as e:
                    print(f"⚠️ Error guardando estadísticas diarias: {e}")
                
                print(f"✅ Examen guardado exitosamente en Supabase para usuario {current_user['email']}")
                
        except Exception as e:
            print(f"❌ Error al guardar examen en Supabase: {e}")
            # Continuar sin guardar

    # OPCIONAL: seguir guardando en JSON para legacy
    with open("resultados.json", "a") as f:
        f.write(json.dumps(resumen) + "\n")

    return render_template("resultado_abierto.html", respuestas=respuestas, preguntas=preguntas, feedbacks=feedbacks, resumen=resumen, respuestas_texto_usuario=respuestas_texto_usuario, respuestas_texto_correcta=respuestas_texto_correcta)

@app.route("/cuestionario")
def cuestionario():
    # Verificar que hay preguntas en la sesión
    preguntas = session.get("preguntas", [])
    if not preguntas:
        flash("No hay un examen disponible para repetir. Genera un nuevo examen primero.", "error")
        return redirect(url_for("generar"))
    
    # Reiniciar respuestas y tiempos pero mantener las mismas preguntas
    session["respuestas"] = ["" for _ in preguntas]
    session["pregunta_times"] = []
    session["start_time"] = time.time()
    session["last_question_time"] = time.time()
    
    return redirect(url_for("pregunta", numero=0))

@app.route("/reiniciar", methods=["POST"])
def reiniciar():
    preguntas = session.get("preguntas", [])
    session["respuestas"] = ["" for _ in preguntas]
    session["pregunta_times"] = []
    session["start_time"] = time.time()
    session["last_question_time"] = time.time()
    return redirect(url_for("pregunta", numero=0))

@app.route("/historial")
def historial():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    try:
        if supabase:
            # Obtener exámenes del usuario desde Supabase
            current_user = get_current_user()
            response = supabase.table('examenes').select('*').eq('usuario_id', current_user['id']).order('fecha_rendido', desc=True).execute()
            
            if response.data:
                examenes = []
                for examen in response.data:
                    # Formatear fecha para mostrar
                    fecha = datetime.fromisoformat(examen['fecha_rendido'].replace('Z', '+00:00'))
                    examenes.append({
                        'id': examen['id'],
                        'fecha': fecha,
                        'nota': examen['nota'],
                        'materia': examen['materia'],
                        'tiempo_total': examen['tiempo_duracion'],
                        'estado': examen['estado'],
                        # Agregar métricas detalladas
                        'correctas': examen.get('correctas', 0),
                        'parciales': examen.get('parciales', 0),
                        'incorrectas': examen.get('incorrectas', 0)
                    })
                return render_template("historial.html", examenes=examenes)
            else:
                flash("No tienes exámenes rendidos aún. ¡Genera tu primer examen!")
                return redirect(url_for('generar'))
                
    except Exception as e:
        print(f"Error obteniendo historial: {e}")
        flash("Error al cargar el historial. Intenta nuevamente.")
        return redirect(url_for('generar'))

@app.route("/examen/<examen_id>")
def detalle_examen(examen_id):
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    try:
        if supabase:
            # Obtener examen desde Supabase
            current_user = get_current_user()
            examen_response = supabase.table('examenes').select('*').eq('id', examen_id).eq('usuario_id', current_user['id']).execute()
            
            if examen_response.data:
                examen = examen_response.data[0]
                
                # Obtener preguntas del examen
                preguntas_response = supabase.table('preguntas_examen').select('*').eq('examen_id', examen_id).order('orden').execute()
                
                if preguntas_response.data:
                    preguntas = []
                    for pregunta in preguntas_response.data:
                        # Decodificar opciones JSON
                        opciones = []
                        if pregunta.get('opciones'):
                            try:
                                opciones = json.loads(pregunta['opciones'])
                            except:
                                opciones = []
                        
                        # Determinar el feedback basado en la respuesta
                        feedback = ""
                        if pregunta.get('respuesta_usuario') == pregunta.get('respuesta_correcta'):
                            feedback = "✔️ CORRECTA"
                        else:
                            feedback = "❌ INCORRECTA"
                        
                        preguntas.append({
                            'enunciado': pregunta['enunciado'],
                            'opciones': opciones,
                            'opciones_decoded': opciones,  # Para el template
                            'respuesta_usuario': pregunta['respuesta_usuario'],
                            'respuesta_correcta': pregunta['respuesta_correcta'],
                            'tipo': pregunta['tipo'],
                            'tema': pregunta['tema'],
                            'feedback': feedback
                        })
                    
                    # Formatear examen para el template
                    examen_formateado = {
                        'id': examen['id'],
                        'fecha': datetime.fromisoformat(examen['fecha_rendido'].replace('Z', '+00:00')),
                        'nota': examen['nota'],
                        'materia': examen['materia'],
                        'tiempo_total': examen['tiempo_duracion'],
                        # Agregar métricas detalladas
                        'correctas': examen.get('correctas', 0),
                        'parciales': examen.get('parciales', 0),
                        'incorrectas': examen.get('incorrectas', 0),
                        'feedback_general': examen.get('feedback_general', 'Sin feedback disponible')
                    }
                    
                    return render_template("detalle_examen.html", examen=examen_formateado, preguntas=preguntas)
                else:
                    flash("No se encontraron preguntas para este examen.")
                    return redirect(url_for('historial'))
            else:
                flash("Examen no encontrado o no tienes acceso.")
                return redirect(url_for('historial'))
                
    except Exception as e:
        print(f"Error obteniendo detalle del examen: {e}")
        flash("Error al cargar el examen. Intenta nuevamente.")
        return redirect(url_for('historial'))

@app.route("/wolfram", methods=["GET", "POST"])
def wolfram_query():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    resultado = None
    imagen_url = None
    error = None
    pods = []
    if request.method == "POST":
        operacion = request.form.get("operacion", "")
        expresion = request.form.get("expresion", "")
        consulta = expresion.strip()
        # Si el usuario eligió una operación, armar la consulta
        if operacion and operacion != "":
            if operacion == "derivative":
                consulta = f"derivative of {expresion}"
            elif operacion == "integral":
                consulta = f"integrate {expresion}"
            elif operacion == "solve":
                consulta = f"solve {expresion}"
            elif operacion == "limit":
                consulta = f"limit {expresion}"
            elif operacion == "simplify":
                consulta = f"simplify {expresion}"
            elif operacion == "expand":
                consulta = f"expand {expresion}"
            elif operacion == "factor":
                consulta = f"factor {expresion}"
            elif operacion == "plot":
                consulta = f"plot {expresion}"
        # Si la consulta parece una frase, traducir con IA
        elif len(expresion.split()) > 4:
            try:
                prompt_ia = (
                    "Convertí la siguiente frase a una consulta matemática en inglés para Wolfram Alpha. "
                    "No expliques, solo devolvé la consulta lista para enviar.\nFrase: " + expresion
                )
                consulta = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Sos un traductor de frases matemáticas a consultas para Wolfram Alpha."},
                        {"role": "user", "content": prompt_ia}
                    ],
                    max_tokens=60,
                    timeout=30
                ).choices[0].message.content.strip()
            except Exception as e:
                error = f"No se pudo traducir la frase a consulta matemática: {str(e)}"
        try:
            url = "https://api.wolframalpha.com/v2/query"
            params = {
                "input": consulta,
                "appid": app_id,
                "format": "image,plaintext"
            }
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                error = f"Error HTTP: {resp.status_code}"
            else:
                root = ET.fromstring(resp.text)
                for pod in root.findall(".//pod"):
                    pod_title = pod.attrib.get("title", "")
                    subpod = pod.find("subpod")
                    pod_plaintext = subpod.findtext("plaintext") if subpod is not None else None
                    pod_img = None
                    if subpod is not None:
                        img_tag = subpod.find("img")
                        if img_tag is not None:
                            pod_img = img_tag.attrib.get("src")
                    # Guardar todos los pods relevantes
                    if pod_plaintext or pod_img:
                        pods.append({"title": pod_title, "plaintext": pod_plaintext, "img": pod_img})
                    # Guardar el resultado principal
                    if pod_title.lower() in ["result", "resultado", "solution", "solución"] and not resultado:
                        resultado = pod_plaintext
                        imagen_url = pod_img
                if not resultado and pods:
                    resultado = pods[0]["plaintext"]
                    imagen_url = pods[0]["img"]
                if not resultado:
                    error = "No se encontró una respuesta clara para tu consulta."
        except Exception as e:
            import traceback
            print("Error Wolfram:", e)
            traceback.print_exc()
            error = f"Error al consultar Wolfram Alpha: {str(e)}"
    return render_template("wolfram.html", resultado=resultado, imagen_url=imagen_url, error=error, pods=pods)

@app.route("/examen_matematico/<int:numero>", methods=["GET", "POST"])
def examen_matematico(numero):
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    ejercicios = session.get("ejercicios_matematicos", [])
    if not ejercicios or numero >= len(ejercicios):
        return redirect(url_for("resultado_matematico"))

    if request.method == "POST":
        respuesta = request.form.get("respuesta", "")
        ejercicios[numero]["respuesta_usuario"] = respuesta
        session["ejercicios_matematicos"] = ejercicios
        return redirect(url_for("examen_matematico", numero=numero + 1))

    ejercicio = ejercicios[numero]
    return render_template("examen_matematico.html", ejercicio=ejercicio, numero=numero + 1, total=len(ejercicios), actual=numero)

@app.route("/resultado_matematico")
def resultado_matematico():
    # Verificar autenticación simple
    if not is_authenticated():
        return redirect(url_for('login'))
    ejercicios = session.get("ejercicios_matematicos", [])
    for ejercicio in ejercicios:
        usuario = ejercicio.get("respuesta_usuario", "").strip()
        solucion = ejercicio.get("solucion", "").strip()
        es_correcta = False
        if usuario and solucion:
            try:
                url = "https://api.wolframalpha.com/v2/query"
                # Normalizar respuestas
                usuario_norm = usuario.replace(" ", "").lower()
                solucion_norm = solucion.replace(" ", "").lower()
                # 1. Consulta directa
                consulta_equiv = f"is ({usuario}) = ({solucion})"
                params = {"input": consulta_equiv, "appid": app_id, "format": "plaintext"}
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(resp.text)
                    for pod in root.findall(".//pod"):
                        pod_title = pod.attrib.get("title", "").lower()
                        if pod_title in ["result", "resultado", "solution", "solución"]:
                            subpod = pod.find("subpod")
                            result_text = subpod.findtext("plaintext") if subpod is not None else ""
                            if result_text and "true" in result_text.lower():
                                es_correcta = True
                # 2. Solo parte derecha de la ecuación (si hay '=')
                if not es_correcta and '=' in solucion:
                    derecha = solucion.split('=')[-1].strip()
                    consulta_equiv2 = f"is ({usuario}) = ({derecha})"
                    params2 = {"input": consulta_equiv2, "appid": app_id, "format": "plaintext"}
                    resp2 = requests.get(url, params=params2, timeout=30)
                    if resp2.status_code == 200:
                        root2 = ET.fromstring(resp2.text)
                        for pod in root2.findall(".//pod"):
                            pod_title = pod.attrib.get("title", "").lower()
                            if pod_title in ["result", "resultado", "solution", "solución"]:
                                subpod = pod.find("subpod")
                                result_text = subpod.findtext("plaintext") if subpod is not None else ""
                                if result_text and "true" in result_text.lower():
                                    es_correcta = True
                # 3. Normalizar y comparar texto plano (fallback)
                if not es_correcta and usuario_norm == solucion_norm:
                    es_correcta = True
                ejercicio["es_correcta"] = es_correcta
                print(f"[WOLFRAM] Ejercicio: {ejercicio.get('enunciado','')}")
                print(f"[WOLFRAM] Resultado correcto (texto plano): {solucion}")
            except Exception as e:
                ejercicio["es_correcta"] = False
        else:
            ejercicio["es_correcta"] = False
    return render_template("resultado_matematico.html", ejercicios=ejercicios)

@app.route('/como-funciona')
def como_funciona():
    return render_template('como_funciona.html')

@app.route("/planificacion", methods=["GET", "POST"])
def planificacion():
    if request.method == "POST":
        fecha_examen = request.form.get("fecha_examen")
        dias_no = request.form.get("dias_no", "")
        tiempo_dia = request.form.get("tiempo_dia")
        aclaraciones = request.form.get("aclaraciones", "")
        resumen = request.form.get("resumen", "")
        archivo = request.files.get("archivo")
        texto_resumen = resumen.strip()
        # Procesar archivo si existe (copiado exactamente del generador de exámenes)
        if archivo and archivo.filename:
            if archivo.filename.endswith(".txt"):
                texto_resumen = archivo.read().decode("utf-8")
            elif archivo.filename.endswith(".pdf"):
                from io import BytesIO
                import PyPDF2
                pdf_stream = BytesIO(archivo.read())
                reader = PyPDF2.PdfReader(pdf_stream)
                texto_resumen = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            elif archivo.filename.endswith(".docx"):
                from io import BytesIO
                import docx
                docx_stream = BytesIO(archivo.read())
                doc = docx.Document(docx_stream)
                texto_resumen = "\n".join([p.text for p in doc.paragraphs])
        print("\n--- TEXTO EXTRAÍDO DEL ARCHIVO (PLANIFICACIÓN) ---\n", texto_resumen, "\n--- FIN TEXTO EXTRAÍDO ---\n")
        # Armar prompt para la IA
        from datetime import date
        fecha_actual = date.today().strftime('%Y-%m-%d')
        prompt = (
            f"Sos un planificador de estudio. El usuario tiene un examen el día {fecha_examen}. "
            f"No puede estudiar los días: {dias_no}. Puede dedicar {tiempo_dia} horas por día. "
            f"Aclaraciones: {aclaraciones}. Temario/resumen: {texto_resumen}\n"
            f"El primer día del plan debe ser la fecha de hoy: {fecha_actual}. "
            "ES OBLIGATORIO que todos los temas, unidades o títulos del resumen estén incluidos en el plan, aunque implique agrupar varios temas en un mismo día. "
            "Si hay más temas que días, agrupá todos los que hagan falta en un mismo día, pero NO DEJES NINGÚN TEMA FUERA. "
            "En cada actividad, usá el formato: 'Tema principal | subtema1, subtema2, subtema3' (usá el símbolo | para separar el tema principal de los subtemas, y comas para separar los subtemas). "
            "En cada actividad, usá la palabra 'Estudiar' y mencioná el nombre real de la unidad o tema y sus componentes principales. "
            "Si hay un día con mucho contenido, agregá un mensaje motivacional personalizado como: 'Día difícil: estudiar ... ¡Tú puedes!'. "
            "Si corresponde, agregá repasos o autoevaluaciones antes del examen. "
            "Respondé SOLO en formato JSON, sin explicaciones ni texto adicional. El JSON debe ser una lista de objetos con 'fecha' (YYYY-MM-DD) y 'actividad'.\n"
            "Ejemplo de formato:\n"
            "[\n  {\"fecha\": \"2025-07-21\", \"actividad\": \"Estudiar Gestión de Costos | planificación, estimación, presupuesto, control, KPI\"},\n  {\"fecha\": \"2025-07-22\", \"actividad\": \"Día difícil: Estudiar Gestión de Adquisiciones | tipos de contrato, criterios de selección, proceso de compras. ¡Tú puedes!\"},\n  {\"fecha\": \"2025-07-23\", \"actividad\": \"Repaso general de todos los temas y autoevaluación\"}\n]"
        )
        # Consultar a OpenAI
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sos un planificador de estudio experto."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                timeout=90
            )
            plan_json = response.choices[0].message.content.strip()
        except Exception as e:
            plan_json = f"[{{'fecha':'error','actividad':'Error al generar planificación: {str(e)}'}}]"
        # Extraer temas/unidades del resumen (líneas no vacías con más de 10 caracteres)
        import json, re
        from datetime import datetime, timedelta, date
        explicacion_ia = None
        plan = None
        
        # Intentar parsear directamente el JSON
        try:
            plan = json.loads(plan_json)
            print("\n--- PLAN JSON GENERADO POR LA IA ---\n", json.dumps(plan, ensure_ascii=False, indent=2), "\n--- FIN PLAN JSON ---\n")
            explicacion_ia = None  # Si se puede parsear como JSON, no hay explicación
        except json.JSONDecodeError:
            # Si no es JSON válido, intentar extraer JSON con regex
            # Primero intentar extraer JSON de markdown (```json ... ```)
            markdown_match = re.search(r'```json\s*([\s\S]*?)\s*```', plan_json)
            if markdown_match:
                json_str = markdown_match.group(1)
                try:
                    plan = json.loads(json_str)
                    print("\n--- PLAN JSON GENERADO POR LA IA ---\n", json.dumps(plan, ensure_ascii=False, indent=2), "\n--- FIN PLAN JSON ---\n")
                    explicacion_ia = None
                except Exception:
                    plan = None
                    explicacion_ia = plan_json
            else:
                # Intentar extraer JSON normal con regex
                match = re.search(r'\[\s*{[\s\S]*?}\s*\]', plan_json)
                if match:
                    json_str = match.group(0)
                    try:
                        plan = json.loads(json_str)
                        print("\n--- PLAN JSON GENERADO POR LA IA ---\n", json.dumps(plan, ensure_ascii=False, indent=2), "\n--- FIN PLAN JSON ---\n")
                        # Si hay texto antes del JSON, lo guardo como explicación
                        if plan_json.strip() != json_str.strip():
                            explicacion_ia = plan_json.replace(json_str, '').strip()
                        else:
                            explicacion_ia = None
                    except Exception:
                        plan = None
                        explicacion_ia = plan_json
                else:
                    # Si no hay JSON, mostrar como texto plano
                    explicacion_ia = plan_json
                    plan = None
        
        # Preparar datos para el calendario visual (igual que antes)
        days_list = []
        actividades_por_fecha = {}
        if plan and isinstance(plan, list) and len(plan) > 0 and 'fecha' in plan[0]:
            # (Eliminado el ajuste automático de fechas)
            pass # No hay ajuste automático de fechas aquí
        
        # Procesar cada actividad para separar tema principal y subtemas (split inteligente)
        def split_subtemas(text):
            subtemas = []
            buffer = ''
            paren = 0
            for c in text:
                if c == '(': paren += 1
                elif c == ')': paren -= 1
                if c == ',' and paren == 0:
                    if buffer.strip():
                        subtemas.append(buffer.strip())
                    buffer = ''
                else:
                    buffer += c
            if buffer.strip():
                subtemas.append(buffer.strip())
            return subtemas
        
        if plan and isinstance(plan, list):
            for item in plan:
                actividad = item.get('actividad', '')
                if '|' in actividad:
                    tema, subs = actividad.split('|', 1)
                    item['tema_principal'] = tema.strip()
                    item['subtemas'] = split_subtemas(subs.strip())
                else:
                    item['tema_principal'] = actividad.strip()
                    item['subtemas'] = []
        
        # Preparar datos para el calendario visual (solo fechas reales del plan, ordenadas)
        if plan and isinstance(plan, list) and len(plan) > 0 and 'fecha' in plan[0]:
            actividades_por_fecha = {item['fecha']: item['actividad'] for item in plan}
        
        fechas_ordenadas = []
        if plan and isinstance(plan, list) and len(plan) > 0 and 'fecha' in plan[0]:
            fechas_ordenadas = [
                (datetime.strptime(item['fecha'], '%Y-%m-%d'), item['fecha'], actividades_por_fecha[item['fecha']])
                for item in plan if item['fecha'] in actividades_por_fecha
            ]
            fechas_ordenadas.sort(key=lambda x: x[0])
            print("\n--- FECHAS ORDENADAS PARA TIMELINE ---\n", fechas_ordenadas, "\n--- FIN FECHAS ORDENADAS ---\n")
        
        # Debug: imprimir valores que se pasan al template
        print("\n--- VALORES PARA TEMPLATE ---")
        print(f"plan: {plan}")
        print(f"explicacion_ia: {explicacion_ia}")
        print(f"plan_json: {plan_json[:200]}...")
        print("--- FIN VALORES ---\n")
        
        return render_template("planificacion_resultado.html", plan=plan, plan_json=plan_json, days_list=days_list, actividades_por_fecha=actividades_por_fecha, explicacion_ia=explicacion_ia, fechas_ordenadas=fechas_ordenadas)
    
    return render_template("planificacion.html")

@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_interno(e):
    return render_template('500.html'), 500

@app.route("/sitemap.xml")
def sitemap():
    """Generar sitemap.xml para SEO"""
    from datetime import datetime
    
    # URLs principales del sitio
    urls = [
        {
            'loc': url_for('index', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'weekly',
            'priority': '1.0'
        },
        {
            'loc': url_for('login', _external=True),
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
            'changefreq': 'monthly',
            'priority': '0.8'
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

# =====================================================
# SISTEMA SIMPLE DE AUTENTICACIÓN CON SUPABASE AUTH
# =====================================================

def is_authenticated():
    """Verificar si el usuario está autenticado"""
    return 'user_id' in session and 'user_email' in session

def get_current_user():
    """Obtener datos del usuario actual desde la sesión"""
    if is_authenticated():
        return {
            'id': session.get('user_id'),
            'email': session.get('user_email'),
            'nombre': session.get('user_nombre')
        }
    return None

if __name__ == '__main__':
    # Configuración para desarrollo
    debug = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=debug)