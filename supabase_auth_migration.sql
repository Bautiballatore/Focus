-- =====================================================
-- MIGRACIÓN A SUPABASE AUTH
-- =====================================================

-- 1. Habilitar RLS (Row Level Security) en todas las tablas
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE examenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE preguntas_examen ENABLE ROW LEVEL SECURITY;
ALTER TABLE estadisticas_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs_actividad ENABLE ROW LEVEL SECURITY;

-- 2. Crear políticas de seguridad para usuarios
CREATE POLICY "Usuarios pueden ver solo su propio perfil" ON usuarios
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Usuarios pueden actualizar solo su propio perfil" ON usuarios
    FOR UPDATE USING (auth.uid()::text = id::text);

-- 3. Crear políticas de seguridad para exámenes
CREATE POLICY "Usuarios pueden ver solo sus propios exámenes" ON examenes
    FOR SELECT USING (auth.uid()::text = usuario_id::text);

CREATE POLICY "Usuarios pueden insertar solo sus propios exámenes" ON examenes
    FOR INSERT WITH CHECK (auth.uid()::text = usuario_id::text);

CREATE POLICY "Usuarios pueden actualizar solo sus propios exámenes" ON examenes
    FOR UPDATE USING (auth.uid()::text = usuario_id::text);

-- 4. Crear políticas de seguridad para preguntas
CREATE POLICY "Usuarios pueden ver solo preguntas de sus exámenes" ON preguntas_examen
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM examenes 
            WHERE examenes.id = preguntas_examen.examen_id 
            AND examenes.usuario_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Usuarios pueden insertar solo preguntas en sus exámenes" ON preguntas_examen
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM examenes 
            WHERE examenes.id = preguntas_examen.examen_id 
            AND examenes.usuario_id::text = auth.uid()::text
        )
    );

-- 5. Crear políticas de seguridad para estadísticas
CREATE POLICY "Usuarios pueden ver solo sus propias estadísticas" ON estadisticas_usuarios
    FOR SELECT USING (auth.uid()::text = usuario_id::text);

CREATE POLICY "Usuarios pueden insertar solo sus propias estadísticas" ON estadisticas_usuarios
    FOR INSERT WITH CHECK (auth.uid()::text = usuario_id::text);

CREATE POLICY "Usuarios pueden actualizar solo sus propias estadísticas" ON estadisticas_usuarios
    FOR UPDATE USING (auth.uid()::text = usuario_id::text);

-- 6. Crear políticas de seguridad para logs
CREATE POLICY "Usuarios pueden ver solo sus propios logs" ON logs_actividad
    FOR SELECT USING (auth.uid()::text = usuario_id::text);

CREATE POLICY "Usuarios pueden insertar solo sus propios logs" ON logs_actividad
    FOR INSERT WITH CHECK (auth.uid()::text = usuario_id::text);

-- 7. Crear función para sincronizar usuarios de Auth con tabla usuarios
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.usuarios (id, email, nombre, fecha_registro, activo)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nombre', split_part(NEW.email, '@', 1)),
        NEW.created_at,
        true
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 8. Crear trigger para sincronizar usuarios automáticamente
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 9. Configurar configuración de Auth
-- Nota: Esto se hace desde el dashboard de Supabase, no desde SQL

-- 10. Mensaje de confirmación
SELECT '✅ Migración a Supabase Auth completada!' as mensaje;
SELECT '🔐 RLS habilitado en todas las tablas' as seguridad;
SELECT '📋 Políticas de seguridad creadas' as politicas;
SELECT '🔄 Trigger de sincronización configurado' as sincronizacion;
