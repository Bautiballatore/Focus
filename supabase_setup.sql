-- Script para crear las tablas en Supabase
-- Ejecutar esto directamente en el SQL Editor de Supabase

-- 1. Tabla de usuarios (con toda la info que necesitas)
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
    activo BOOLEAN DEFAULT TRUE
);

-- 2. Tabla de exámenes
CREATE TABLE IF NOT EXISTS examenes (
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
    tiempo_total_segundos INTEGER DEFAULT 0
);

-- 3. Tabla de preguntas
CREATE TABLE IF NOT EXISTS preguntas_examen (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    examen_id UUID REFERENCES examenes(id),
    enunciado TEXT NOT NULL,
    opciones JSONB,
    respuesta_correcta VARCHAR,
    tipo VARCHAR NOT NULL,
    tema VARCHAR,
    orden INTEGER
);

-- 4. Tabla de estadísticas diarias
CREATE TABLE IF NOT EXISTS estadisticas_usuarios (
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

-- 5. Tabla de logs de actividad
CREATE TABLE IF NOT EXISTS logs_actividad (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES usuarios(id),
    fecha_actividad TIMESTAMP DEFAULT NOW(),
    tipo_actividad VARCHAR NOT NULL,
    detalles JSONB,
    ip_address VARCHAR,
    user_agent TEXT
);

-- 6. Crear índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_examenes_usuario_id ON examenes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_examenes_fecha ON examenes(fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_logs_usuario_fecha ON logs_actividad(usuario_id, fecha_actividad);

-- 7. Insertar datos de ejemplo (opcional)
INSERT INTO usuarios (email, nombre, password_hash, como_nos_conociste, plataforma_uso) 
VALUES 
    ('usuario1@test.com', 'Usuario Test 1', 'hash123', 'Redes sociales', 'Web'),
    ('usuario2@test.com', 'Usuario Test 2', 'hash456', 'Recomendación', 'Móvil')
ON CONFLICT (email) DO NOTHING;

-- 8. Consultas útiles para el admin (guardar como vistas)
-- Vista: Resumen general de usuarios
CREATE OR REPLACE VIEW vista_resumen_usuarios AS
SELECT 
    COUNT(*) as total_usuarios,
    COUNT(CASE WHEN fecha_registro >= CURRENT_DATE THEN 1 END) as usuarios_hoy,
    COUNT(CASE WHEN activo THEN 1 END) as usuarios_activos,
    AVG(total_examenes_rendidos) as promedio_examenes_por_usuario
FROM usuarios;

-- Vista: Estadísticas de exámenes
CREATE OR REPLACE VIEW vista_estadisticas_examenes AS
SELECT 
    COUNT(*) as total_examenes,
    COUNT(CASE WHEN estado = 'rendido' THEN 1 END) as examenes_rendidos,
    AVG(nota) as nota_promedio,
    SUM(tiempo_total_segundos) / 3600 as tiempo_total_horas
FROM examenes;

-- Vista: Actividad reciente
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

-- Mensaje de confirmación
SELECT '✅ Tablas creadas exitosamente en Supabase!' as mensaje;
