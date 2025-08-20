-- =====================================================
-- SCRIPT COMPLETO PARA RECREAR TODAS LAS TABLAS EN SUPABASE
-- =====================================================

-- 1. Eliminar tablas existentes (se perderán los datos)
DROP TABLE IF EXISTS preguntas_examen CASCADE;
DROP TABLE IF EXISTS examenes CASCADE;
DROP TABLE IF EXISTS estadisticas_usuarios CASCADE;
DROP TABLE IF EXISTS logs_actividad CASCADE;

-- 2. Eliminar vistas existentes
DROP VIEW IF EXISTS vista_resumen_usuarios CASCADE;
DROP VIEW IF EXISTS vista_estadisticas_examenes CASCADE;
DROP VIEW IF EXISTS vista_actividad_reciente CASCADE;

-- 3. Crear tabla de usuarios (mantener si ya existe)
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    nombre VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    fecha_registro TIMESTAMP DEFAULT NOW(),
    como_nos_conociste TEXT,
    plataforma_uso TEXT,
    preguntas_completadas INTEGER DEFAULT 0,
    total_examenes_rendidos INTEGER DEFAULT 0,
    ultima_actividad TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE,
    -- Agregar columnas para estadísticas totales
    correctas_total INTEGER DEFAULT 0,
    parciales_total INTEGER DEFAULT 0,
    incorrectas_total INTEGER DEFAULT 0
);

-- 4. Crear tabla de exámenes con estadísticas completas
CREATE TABLE examenes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id),
    titulo VARCHAR NOT NULL,
    materia VARCHAR,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_rendido TIMESTAMP,
    preguntas JSONB,
    respuestas JSONB,
    nota DECIMAL(4,2),
    tiempo_duracion INTEGER,
    estado VARCHAR DEFAULT 'creado',
    tiempo_total_segundos INTEGER DEFAULT 0,
    -- Columnas para estadísticas detalladas
    correctas INTEGER DEFAULT 0,
    parciales INTEGER DEFAULT 0,
    incorrectas INTEGER DEFAULT 0,
    total_preguntas INTEGER DEFAULT 0,
    -- Agregar feedback general
    feedback_general TEXT
);

-- 5. Crear tabla de preguntas con todas las columnas necesarias
CREATE TABLE preguntas_examen (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    examen_id UUID REFERENCES examenes(id),
    enunciado TEXT NOT NULL,
    opciones JSONB,
    respuesta_usuario VARCHAR,
    respuesta_correcta VARCHAR,
    tipo VARCHAR NOT NULL,
    tema VARCHAR,
    orden INTEGER,
    -- Columnas para evaluación
    es_correcta BOOLEAN DEFAULT FALSE,
    es_parcial BOOLEAN DEFAULT FALSE,
    puntaje_obtenido DECIMAL(3,2) DEFAULT 0
);

-- 6. Crear tabla de estadísticas diarias
CREATE TABLE estadisticas_usuarios (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id),
    fecha_estadistica DATE DEFAULT CURRENT_DATE,
    examenes_creados_hoy INTEGER DEFAULT 0,
    examenes_rendidos_hoy INTEGER DEFAULT 0,
    preguntas_correctas_hoy INTEGER DEFAULT 0,
    preguntas_incorrectas_hoy INTEGER DEFAULT 0,
    tiempo_total_estudio_hoy INTEGER DEFAULT 0,
    materias_estudiadas_hoy TEXT[],
    UNIQUE(usuario_id, fecha_estadistica)
);

-- 7. Crear tabla de logs de actividad
CREATE TABLE logs_actividad (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id),
    fecha_actividad TIMESTAMP DEFAULT NOW(),
    tipo_actividad VARCHAR NOT NULL,
    detalles JSONB,
    ip_address VARCHAR,
    user_agent TEXT
);

-- 8. Crear índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_examenes_usuario_id ON examenes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_examenes_fecha ON examenes(fecha_rendido);
CREATE INDEX IF NOT EXISTS idx_preguntas_examen_id ON preguntas_examen(examen_id);
CREATE INDEX IF NOT EXISTS idx_logs_usuario_fecha ON logs_actividad(usuario_id, fecha_actividad);
CREATE INDEX IF NOT EXISTS idx_estadisticas_usuario_fecha ON estadisticas_usuarios(usuario_id, fecha_estadistica);

-- 9. Crear vistas útiles para el admin
CREATE OR REPLACE VIEW vista_resumen_usuarios AS
SELECT 
    COUNT(*) as total_usuarios,
    COUNT(CASE WHEN fecha_registro >= CURRENT_DATE THEN 1 END) as usuarios_hoy,
    COUNT(CASE WHEN activo THEN 1 END) as usuarios_activos,
    AVG(total_examenes_rendidos) as promedio_examenes_por_usuario
FROM usuarios;

CREATE OR REPLACE VIEW vista_estadisticas_examenes AS
SELECT 
    COUNT(*) as total_examenes,
    COUNT(CASE WHEN estado = 'rendido' THEN 1 END) as examenes_rendidos,
    AVG(nota) as nota_promedio,
    SUM(tiempo_total_segundos) / 3600 as tiempo_total_horas,
    SUM(correctas) as total_correctas,
    SUM(parciales) as total_parciales,
    SUM(incorrectas) as total_incorrectas
FROM examenes;

CREATE OR REPLACE VIEW vista_actividad_reciente AS
SELECT 
    u.email,
    u.nombre,
    l.tipo_actividad,
    l.fecha_actividad,
    l.ip_address
FROM logs_actividad l
JOIN usuarios u ON l.usuario_id = u.id
ORDER BY l.fecha_actividad DESC
LIMIT 100;

-- 10. Verificar que todo esté funcionando
SELECT 
    table_name, 
    COUNT(*) as columnas
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name IN ('usuarios', 'examenes', 'preguntas_examen', 'estadisticas_usuarios', 'logs_actividad')
GROUP BY table_name
ORDER BY table_name;

-- 11. Verificar la estructura de examenes
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'examenes' 
ORDER BY ordinal_position;

-- 12. Verificar la estructura de preguntas_examen
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'preguntas_examen' 
ORDER BY ordinal_position;

-- 13. Mensaje de confirmación final
SELECT '✅ Todas las tablas creadas exitosamente con estructura completa!' as mensaje;

-- =====================================================
-- SCRIPT DE MIGRACIÓN PARA TABLAS EXISTENTES
-- =====================================================
-- Si ya tienes tablas existentes, ejecuta estos comandos para agregar las nuevas columnas:

-- Agregar columnas a tabla usuarios existente
ALTER TABLE usuarios 
ADD COLUMN IF NOT EXISTS correctas_total INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS parciales_total INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS incorrectas_total INTEGER DEFAULT 0;

-- Agregar columnas a tabla examenes existente
ALTER TABLE examenes 
ADD COLUMN IF NOT EXISTS correctas INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS parciales INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS incorrectas INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_preguntas INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS feedback_general TEXT;

-- Actualizar registros existentes con valores por defecto
UPDATE examenes 
SET 
    correctas = 0,
    parciales = 0,
    incorrectas = 0,
    total_preguntas = 0
WHERE correctas IS NULL;

-- Mensaje de migración completada
SELECT '✅ Migración de tablas existentes completada!' as mensaje;