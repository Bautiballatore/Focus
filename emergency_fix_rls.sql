-- SOLUCIÓN DE EMERGENCIA para el error RLS
-- Ejecutar en Supabase SQL Editor

-- OPCIÓN 1: Deshabilitar RLS temporalmente (más rápido para probar)
ALTER TABLE planificaciones DISABLE ROW LEVEL SECURITY;

-- OPCIÓN 2: Si prefieres mantener RLS, crear una política permisiva temporal
-- ALTER TABLE planificaciones ENABLE ROW LEVEL SECURITY;
-- DROP POLICY IF EXISTS "Temporary permissive policy" ON planificaciones;
-- CREATE POLICY "Temporary permissive policy" 
-- ON planificaciones 
-- FOR ALL 
-- USING (true) 
-- WITH CHECK (true);

-- Verificar el estado
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE tablename = 'planificaciones';
