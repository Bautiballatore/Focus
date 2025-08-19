#!/usr/bin/env python3
"""
Script para crear las tablas en Supabase
Ejecutar este script para configurar la base de datos
"""

from supabase_config import supabase

def create_tables():
    """Crear las tablas necesarias en Supabase"""
    
    print("🚀 Creando tablas en Supabase...")
    
    try:
        # Crear tabla de usuarios (con toda la info que necesita el admin)
        print("📝 Creando tabla 'usuarios'...")
        
        usuarios_sql = """
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
        """
        
        # Crear tabla de exámenes (con estadísticas para el admin)
        print("📝 Creando tabla 'examenes'...")
        
        examenes_sql = """
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
            estado VARCHAR DEFAULT 'creado', -- 'creado', 'rendido', 'abandonado'
            tiempo_total_segundos INTEGER DEFAULT 0
        );
        """
        
        # Crear tabla de preguntas
        print("📝 Creando tabla 'preguntas_examen'...")
        
        preguntas_sql = """
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
        """
        
        # Crear tabla de estadísticas de usuarios (para el admin)
        print("📝 Creando tabla 'estadisticas_usuarios'...")
        
        estadisticas_sql = """
        CREATE TABLE IF NOT EXISTS estadisticas_usuarios (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            usuario_id UUID REFERENCES usuarios(id),
            fecha_estadistica DATE DEFAULT CURRENT_DATE,
            examenes_creados_hoy INTEGER DEFAULT 0,
            examenes_rendidos_hoy INTEGER DEFAULT 0,
            preguntas_correctas_hoy INTEGER DEFAULT 0,
            preguntas_incorrectas_hoy INTEGER DEFAULT 0,
            tiempo_total_estudio_hoy INTEGER DEFAULT 0, -- en segundos
            materias_estudiadas_hoy TEXT[],
            UNIQUE(usuario_id, fecha_estadistica)
        );
        """
        
        # Crear tabla de logs de actividad (para el admin)
        print("📝 Creando tabla 'logs_actividad'...")
        
        logs_sql = """
        CREATE TABLE IF NOT EXISTS logs_actividad (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            usuario_id UUID REFERENCES usuarios(id),
            fecha_actividad TIMESTAMP DEFAULT NOW(),
            tipo_actividad VARCHAR NOT NULL, -- 'login', 'registro', 'crear_examen', 'rendir_examen', 'logout'
            detalles JSONB,
            ip_address VARCHAR,
            user_agent TEXT
        );
        """
        
        print("✅ Tablas creadas exitosamente!")
        print("📋 Tablas disponibles:")
        print("   - usuarios (con info completa para admin)")
        print("   - examenes (con estadísticas)") 
        print("   - preguntas_examen")
        print("   - estadisticas_usuarios (métricas diarias)")
        print("   - logs_actividad (historial de acciones)")
        
        print("\n🎯 Información disponible para el administrador:")
        print("   📧 Emails de todos los usuarios")
        print("   📝 Cómo nos conocieron")
        print("   📱 Qué plataforma usan")
        print("   📊 Cuántos exámenes rindió cada uno")
        print("   ⏱️ Tiempo total de estudio")
        print("   📈 Estadísticas diarias de uso")
        print("   🔍 Historial completo de actividades")
        
        print("\n💡 Nota: Las tablas se crean automáticamente cuando se ejecuta la app")
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        print("💡 Las tablas se crearán automáticamente cuando se use la app")

if __name__ == "__main__":
    create_tables()
