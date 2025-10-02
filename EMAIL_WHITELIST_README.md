# Sistema de Limitación de Emails

Este sistema permite controlar qué emails pueden registrarse en la plataforma mediante una lista simple en el código.

## 🚀 Cómo Funciona

1. **Lista de Emails**: Los emails permitidos se definen en la variable `ALLOWED_EMAILS` en `app.py`
2. **Verificación**: Antes de permitir el registro, se verifica si el email está en la lista
3. **Mensaje de Error**: Si el email no está permitido, se muestra un mensaje claro al usuario

## 📝 Configuración

### Agregar Emails Permitidos

Edita la variable `ALLOWED_EMAILS` en `app.py`:

```python
ALLOWED_EMAILS = [
    "admin@focusstudio.com",
    "test@focusstudio.com", 
    "demo@focusstudio.com",
    "usuario1@ejemplo.com",
    "usuario2@ejemplo.com",
    "estudiante@universidad.edu",
    "profesor@universidad.edu",
    # Agrega aquí los emails que quieras permitir
    "nuevo@email.com",
]
```

### Usar la Interfaz de Administración

1. Inicia sesión con el email `admin@focusstudio.com`
2. Ve a `/admin/emails` en tu navegador
3. Desde ahí puedes:
   - Ver todos los emails permitidos
   - Agregar nuevos emails
   - Remover emails existentes

## 🔧 Funciones Disponibles

### `is_email_allowed(email)`
Verifica si un email está en la lista de emails permitidos.

### `add_allowed_email(email)`
Agrega un email a la lista de emails permitidos.

### `remove_allowed_email(email)`
Remueve un email de la lista de emails permitidos.

## 🛡️ Seguridad

- Solo el administrador (`admin@focusstudio.com`) puede acceder a la interfaz de administración
- Los emails se comparan en minúsculas para evitar duplicados
- Los cambios se aplican inmediatamente sin necesidad de reiniciar el servidor

## 📋 Ejemplo de Uso

```python
# Verificar si un email está permitido
if is_email_allowed("usuario@ejemplo.com"):
    print("Email permitido")
else:
    print("Email no permitido")

# Agregar un nuevo email
add_allowed_email("nuevo@ejemplo.com")

# Remover un email
remove_allowed_email("viejo@ejemplo.com")
```

## ⚠️ Notas Importantes

- Los cambios en la lista `ALLOWED_EMAILS` requieren reiniciar el servidor
- Los cambios desde la interfaz web se aplican inmediatamente
- La lista se mantiene en memoria durante la ejecución del servidor
- Para cambios permanentes, edita directamente el código

## 🎯 Ventajas de esta Implementación

1. **Simplicidad**: No requiere base de datos adicional
2. **Rapidez**: Verificación instantánea
3. **Control Total**: Lista completamente personalizable
4. **Fácil Mantenimiento**: Cambios directos en el código
5. **Interfaz Web**: Administración sin tocar código

## 🔄 Flujo de Registro

1. Usuario intenta registrarse
2. Sistema verifica si el email está en `ALLOWED_EMAILS`
3. Si está permitido: procede con el registro normal
4. Si no está permitido: muestra mensaje de error y bloquea el registro
