-- =====================================================
-- TABLA PARA GUARDAR PLANIFICACIONES DE ESTUDIO
-- =====================================================

-- Crear tabla de planificaciones
CREATE TABLE IF NOT EXISTS planificaciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_examen DATE NOT NULL,
    dias_no_disponibles TEXT[], -- Array de fechas en formato YYYY-MM-DD
    tiempo_por_dia DECIMAL(3,1) NOT NULL, -- Horas por día
    aclaraciones TEXT,
    plan_json JSONB NOT NULL, -- Plan completo en formato JSON
    explicacion_ia TEXT,
    activa BOOLEAN DEFAULT TRUE, -- Si la planificación está activa
    ultima_actividad TIMESTAMP DEFAULT NOW()
);

-- Crear índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_planificaciones_usuario_id ON planificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_planificaciones_fecha_examen ON planificaciones(fecha_examen);
CREATE INDEX IF NOT EXISTS idx_planificaciones_activa ON planificaciones(activa);

-- Crear política RLS para seguridad
ALTER TABLE planificaciones ENABLE ROW LEVEL SECURITY;

-- Política: usuarios solo pueden ver sus propias planificaciones
CREATE POLICY "Usuarios pueden ver solo sus propias planificaciones" ON planificaciones
    FOR ALL USING (auth.uid() = usuario_id);

-- Comentarios de la tabla
COMMENT ON TABLE planificaciones IS 'Almacena las planificaciones de estudio de los usuarios';
COMMENT ON COLUMN planificaciones.plan_json IS 'Plan completo en formato JSON con fechas y actividades';
COMMENT ON COLUMN planificaciones.dias_no_disponibles IS 'Array de fechas donde el usuario no puede estudiar';
COMMENT ON COLUMN planificaciones.tiempo_por_dia IS 'Horas de estudio por día';
COMMENT ON COLUMN planificaciones.activa IS 'Indica si la planificación está vigente';
