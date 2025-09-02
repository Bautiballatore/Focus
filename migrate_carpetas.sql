-- Migración para sistema de carpetas
-- Ejecutar en Supabase SQL Editor

-- 1. Crear tabla de carpetas
CREATE TABLE IF NOT EXISTS carpetas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    usuario_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    color VARCHAR(7) DEFAULT '#10a37f',
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Agregar columna carpeta_id a examenes
ALTER TABLE examenes ADD COLUMN IF NOT EXISTS carpeta_id UUID REFERENCES carpetas(id) ON DELETE SET NULL;

-- 3. Crear índices
CREATE INDEX IF NOT EXISTS idx_carpetas_usuario_id ON carpetas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_examenes_carpeta_id ON examenes(carpeta_id);

-- 4. Habilitar RLS
ALTER TABLE carpetas ENABLE ROW LEVEL SECURITY;

-- 5. Políticas RLS
DROP POLICY IF EXISTS "Usuarios pueden ver sus propias carpetas" ON carpetas;
CREATE POLICY "Usuarios pueden ver sus propias carpetas" ON carpetas
    FOR ALL USING (auth.uid() = usuario_id);

-- 6. Crear carpeta por defecto para usuarios existentes
INSERT INTO carpetas (usuario_id, nombre, descripcion, color)
SELECT 
    id as usuario_id,
    'General' as nombre,
    'Carpeta por defecto para exámenes sin categorizar' as descripcion,
    '#6b7280' as color
FROM auth.users
WHERE id NOT IN (SELECT DISTINCT usuario_id FROM carpetas)
ON CONFLICT DO NOTHING;
