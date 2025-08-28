-- Script para corregir las políticas RLS de la tabla planificaciones
-- Ejecutar en Supabase SQL Editor

-- 1. Primero, verificar que la tabla existe y tiene la estructura correcta
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'planificaciones'
ORDER BY ordinal_position;

-- 2. Verificar las políticas RLS actuales
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'planificaciones';

-- 3. Eliminar políticas existentes que puedan estar causando conflictos
DROP POLICY IF EXISTS "Users can insert their own planificaciones" ON planificaciones;
DROP POLICY IF EXISTS "Users can view their own planificaciones" ON planificaciones;
DROP POLICY IF EXISTS "Users can update their own planificaciones" ON planificaciones;
DROP POLICY IF EXISTS "Users can delete their own planificaciones" ON planificaciones;

-- 4. Crear políticas RLS correctas y seguras

-- Política para INSERT: Usuarios pueden insertar solo sus propias planificaciones
CREATE POLICY "Users can insert their own planificaciones" 
ON planificaciones 
FOR INSERT 
WITH CHECK (
    auth.uid()::uuid = usuario_id::uuid
);

-- Política para SELECT: Usuarios pueden ver solo sus propias planificaciones
CREATE POLICY "Users can view their own planificaciones" 
ON planificaciones 
FOR SELECT 
USING (
    auth.uid()::uuid = usuario_id::uuid
);

-- Política para UPDATE: Usuarios pueden actualizar solo sus propias planificaciones
CREATE POLICY "Users can update their own planificaciones" 
ON planificaciones 
FOR UPDATE 
USING (
    auth.uid()::uuid = usuario_id::uuid
)
WITH CHECK (
    auth.uid()::uuid = usuario_id::uuid
);

-- Política para DELETE: Usuarios pueden eliminar solo sus propias planificaciones
CREATE POLICY "Users can delete their own planificaciones" 
ON planificaciones 
FOR DELETE 
USING (
    auth.uid()::uuid = usuario_id::uuid
);

-- 5. Verificar que RLS esté habilitado
ALTER TABLE planificaciones ENABLE ROW LEVEL SECURITY;

-- 6. Verificar las políticas creadas
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'planificaciones';

-- 7. Test: Verificar que un usuario autenticado puede insertar
-- (Esto se ejecutará automáticamente cuando la aplicación intente insertar)

-- 8. Si hay problemas, podemos crear una política más permisiva temporalmente:
-- DROP POLICY IF EXISTS "Temporary permissive policy" ON planificaciones;
-- CREATE POLICY "Temporary permissive policy" 
-- ON planificaciones 
-- FOR ALL 
-- USING (true) 
-- WITH CHECK (true);

-- 9. Para debugging: verificar el tipo de datos de usuario_id
SELECT 
    column_name,
    data_type,
    udt_name
FROM information_schema.columns 
WHERE table_name = 'planificaciones' 
AND column_name = 'usuario_id';

-- 10. Verificar que auth.uid() devuelve el tipo correcto
SELECT 
    typname,
    typlen,
    typcategory
FROM pg_type 
WHERE oid = (SELECT typtype FROM pg_attribute WHERE attname = 'usuario_id' AND attrelid = 'planificaciones'::regclass);
