-- Agregar campo titulo a la tabla examenes
ALTER TABLE examenes ADD COLUMN titulo VARCHAR(255) DEFAULT 'Examen de General';

-- Crear índice para búsquedas por título
CREATE INDEX idx_examenes_titulo ON examenes(titulo);

-- Actualizar registros existentes si es necesario
UPDATE examenes SET titulo = 'Examen de General' WHERE titulo IS NULL;

-- Comentario sobre el campo
COMMENT ON COLUMN examenes.titulo IS 'Título personalizado del examen ingresado por el usuario';
