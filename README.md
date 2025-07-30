# Focus Studio - Generador de Exámenes y Planificación de Estudio

Una aplicación web moderna para generar exámenes personalizados y crear planes de estudio inteligentes usando IA.

## 🚀 Características

- **Generador de Exámenes**: Crea exámenes personalizados con IA
- **Planificación de Estudio**: Genera planes de estudio inteligentes
- **Ejercicios Matemáticos**: Resuelve problemas matemáticos con Wolfram Alpha
- **Sistema de Usuarios**: Registro, login y perfiles personalizados
- **Historial de Exámenes**: Seguimiento de progreso y resultados
- **Interfaz Moderna**: Diseño responsive y animaciones

## 🛠️ Instalación Local

### Prerrequisitos
- Python 3.12+
- pip

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/Bautiballatore/Focus.git
cd Focus
```

2. **Crear entorno virtual**
```bash
python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp env.example .env
# Editar .env con tus API keys
```

5. **Inicializar base de datos**
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

6. **Ejecutar aplicación**
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:8080`

## 🌐 Despliegue en Producción

### Opción 1: Heroku

1. **Instalar Heroku CLI**
2. **Crear aplicación en Heroku**
```bash
heroku create tu-app-name
```

3. **Configurar variables de entorno**
```bash
heroku config:set SECRET_KEY=tu-clave-secreta
heroku config:set OPENAI_API_KEY=tu-api-key
heroku config:set WOLFRAM_APP_ID=tu-wolfram-app-id
heroku config:set FLASK_ENV=production
```

4. **Desplegar**
```bash
git push heroku main
```

### Opción 2: VPS con Nginx + Gunicorn

1. **Instalar dependencias del servidor**
```bash
sudo apt update
sudo apt install python3 python3-pip nginx postgresql
```

2. **Configurar base de datos PostgreSQL**
```bash
sudo -u postgres createdb focus_studio
sudo -u postgres createuser focus_user
```

3. **Configurar Nginx**
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Configurar Gunicorn**
```bash
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

### Opción 3: Docker

1. **Crear Dockerfile**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "wsgi:app"]
```

2. **Construir y ejecutar**
```bash
docker build -t focus-studio .
docker run -p 8080:8080 focus-studio
```

## 🔧 Configuración

### Variables de Entorno Requeridas

- `SECRET_KEY`: Clave secreta para sesiones
- `OPENAI_API_KEY`: API key de OpenAI
- `WOLFRAM_APP_ID`: App ID de Wolfram Alpha
- `DATABASE_URL`: URL de la base de datos (PostgreSQL recomendado para producción)
- `FLASK_ENV`: Entorno (development/production)

### Base de Datos

Para producción, se recomienda usar PostgreSQL en lugar de SQLite:

```bash
# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Crear base de datos
sudo -u postgres createdb focus_studio

# Configurar DATABASE_URL
export DATABASE_URL="postgresql://usuario:password@localhost/focus_studio"
```

## 📁 Estructura del Proyecto

```
Focus/
├── app.py                 # Aplicación principal
├── config.py             # Configuración
├── wsgi.py              # Entry point para producción
├── requirements.txt      # Dependencias Python
├── Procfile             # Configuración Heroku
├── runtime.txt          # Versión de Python
├── Templates/           # Plantillas HTML
├── static/             # Archivos estáticos
└── instance/           # Base de datos SQLite (desarrollo)
```

## 🔒 Seguridad

- Cambia `SECRET_KEY` en producción
- Usa HTTPS en producción
- Configura variables de entorno seguras
- Mantén las dependencias actualizadas

## 📞 Soporte

Para soporte técnico o preguntas, contacta a través de GitHub Issues.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.