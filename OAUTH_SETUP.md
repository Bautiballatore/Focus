# Configuración de OAuth con Google y Supabase

## Implementación Simplificada

Esta implementación usa el enfoque básico y directo de Supabase para OAuth, sin complejidades innecesarias.

### 1. Redirect URL Exacta

**Configuración requerida**:
- En Supabase > Authentication > URL Configuration: `http://127.0.0.1:8080/auth/callback`
- En Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client IDs: `http://127.0.0.1:8080/auth/callback`
- **NO** usar solo `/` o `/callback` - debe ser la URL completa

### 2. Consistencia de Host

**Importante**: Usar **SIEMPRE** `127.0.0.1:8080` en desarrollo (no `localhost`)

### 3. Configuración en Supabase

1. Ir a Supabase Dashboard > Authentication > URL Configuration
2. Site URL: `http://127.0.0.1:8080`
3. Redirect URLs: `http://127.0.0.1:8080/auth/callback`
4. Guardar cambios

### 4. Configuración en Google Cloud Console

1. Ir a Google Cloud Console > APIs & Services > Credentials
2. Editar tu OAuth 2.0 Client ID
3. Authorized redirect URIs: `http://127.0.0.1:8080/auth/callback`
4. Guardar cambios

### 5. Variables de Entorno

Crear archivo `.env` con:
```env
SUPABASE_URL=tu-url-de-supabase
SUPABASE_ANON_KEY=tu-anon-key-de-supabase
GOOGLE_CLIENT_ID=tu-google-client-id
GOOGLE_CLIENT_SECRET=tu-google-client-secret
OAUTH_REDIRECT_BASE=http://127.0.0.1:8080
```

### 6. Flujo de Autenticación

1. Usuario hace clic en "Login con Google"
2. Se redirige a `/auth/google`
3. Supabase genera URL de OAuth con `redirect_to=http://127.0.0.1:8080/auth/callback`
4. Usuario se autentica en Google
5. Google redirige a `/auth/callback` con código de autorización
6. **Simple y directo**: La aplicación usa `supabase.auth.exchange_code_for_session()` para intercambiar el código por una sesión
7. Usuario es redirigido según su estado (preguntas o dashboard)

**Nota**: Esta implementación es simple y directa, sin reintentos innecesarios.

### 7. Verificación de Configuración

Para verificar que todo esté configurado correctamente:

1. **Logs de la aplicación**: Deberías ver:
   ```
   🔄 Redirigiendo a Google OAuth...
   🔍 URL de redirección: [URL de Google]
   ```

2. **Callback recibido**: Deberías ver:
   ```
   🔍 Callback recibido - Code: [código], Error: None
   🔄 Procesando callback de Google OAuth...
   ✅ Usuario obtenido después de OAuth: [email]
   ```

### 8. Solución de Problemas

**Error**: "OAuth no completado - usuario no disponible"
- Verificar que las URLs de redirección coincidan exactamente
- Verificar que no haya mezcla de `localhost` y `127.0.0.1`

**Error**: "'NoneType' object has no attribute 'user'"
- Este error indica que `supabase.auth.get_user()` está devolviendo `None`
- La implementación simplificada usa `exchange_code_for_session()` para resolver esto

**Error**: "Error en la autenticación con Google"
- Verificar configuración en Google Cloud Console
- Verificar que el dominio esté autorizado

**Error**: Cookies no se establecen
- Verificar que `SESSION_COOKIE_SAMESITE` esté en `'Lax'` para desarrollo
- Verificar que no haya restricciones de dominio en cookies


