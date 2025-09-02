-- Crear tabla de carpetas para organizar exámenes
CREATE TABLE IF NOT EXISTS carpetas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    color VARCHAR(7) DEFAULT '#10a37f',
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agregar columna carpeta_id a la tabla examenes existente
ALTER TABLE examenes ADD COLUMN IF NOT EXISTS carpeta_id UUID REFERENCES carpetas(id) ON DELETE SET NULL;

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_carpetas_usuario_id ON carpetas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_examenes_carpeta_id ON examenes(carpeta_id);

-- Habilitar RLS (Row Level Security)
ALTER TABLE carpetas ENABLE ROW LEVEL SECURITY;

-- Política RLS para carpetas: usuarios solo pueden ver sus propias carpetas
CREATE POLICY "Usuarios pueden ver sus propias carpetas" ON carpetas
    FOR ALL USING (auth.uid() = usuario_id);

-- Política RLS para examenes: usuarios pueden ver exámenes en sus carpetas
CREATE POLICY "Usuarios pueden ver exámenes en sus carpetas" ON examenes
    FOR ALL USING (
        auth.uid() = usuario_id OR 
        carpeta_id IN (
            SELECT id FROM carpetas WHERE usuario_id = auth.uid()
        )
    );

-- Función para actualizar fecha_actualizacion automáticamente
CREATE OR REPLACE FUNCTION update_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para actualizar fecha_actualizacion automáticamente
CREATE TRIGGER trigger_update_fecha_actualizacion
    BEFORE UPDATE ON carpetas
    FOR EACH ROW
    EXECUTE FUNCTION update_fecha_actualizacion();

-- Insertar carpeta por defecto para usuarios existentes (opcional)
-- Esta carpeta se puede usar para exámenes sin categorizar
INSERT INTO carpetas (usuario_id, nombre, descripcion, color)
SELECT 
    id as usuario_id,
    'General' as nombre,
    'Carpeta por defecto para exámenes sin categorizar' as descripcion,
    '#6b7280' as color
FROM auth.users
WHERE id NOT IN (SELECT DISTINCT usuario_id FROM carpetas);
