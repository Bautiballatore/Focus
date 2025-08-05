#!/usr/bin/env python3
"""
Script para ver todos los usuarios registrados en la base de datos
"""

import os
import sys
from datetime import datetime

# Agregar el directorio actual al path para importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def ver_usuarios():
    """Mostrar todos los usuarios registrados"""
    with app.app_context():
        # Obtener todos los usuarios
        usuarios = User.query.all()
        
        print("=" * 80)
        print("📧 LISTA DE USUARIOS REGISTRADOS")
        print("=" * 80)
        
        if not usuarios:
            print("❌ No hay usuarios registrados en la base de datos")
            return
        
        print(f"📊 Total de usuarios: {len(usuarios)}")
        print()
        
        for i, usuario in enumerate(usuarios, 1):
            print(f"👤 Usuario #{i}")
            print(f"   📧 Email: {usuario.email}")
            print(f"   👤 Nombre: {usuario.nombre}")
            print(f"   📅 Fecha de registro: {usuario.fecha_registro.strftime('%d/%m/%Y %H:%M')}")
            print(f"   🎯 Cómo nos conoció: {usuario.como_nos_conociste or 'No especificado'}")
            print(f"   💡 Uso de la plataforma: {usuario.uso_plataforma or 'No especificado'}")
            print(f"   ✅ Preguntas completadas: {'Sí' if usuario.preguntas_completadas else 'No'}")
            print()
        
        print("=" * 80)
        print("📈 ESTADÍSTICAS:")
        print(f"   • Total de usuarios: {len(usuarios)}")
        
        # Estadísticas por fuente de conocimiento
        fuentes = {}
        for usuario in usuarios:
            fuente = usuario.como_nos_conociste or 'No especificado'
            fuentes[fuente] = fuentes.get(fuente, 0) + 1
        
        print("   • Por fuente de conocimiento:")
        for fuente, cantidad in sorted(fuentes.items(), key=lambda x: x[1], reverse=True):
            print(f"     - {fuente}: {cantidad}")
        
        # Usuarios con preguntas completadas
        con_preguntas = sum(1 for u in usuarios if u.preguntas_completadas)
        print(f"   • Con preguntas completadas: {con_preguntas}/{len(usuarios)} ({con_preguntas/len(usuarios)*100:.1f}%)")
        
        # Usuarios recientes (últimos 7 días)
        ahora = datetime.utcnow()
        recientes = sum(1 for u in usuarios if (ahora - u.fecha_registro).days <= 7)
        print(f"   • Registrados en los últimos 7 días: {recientes}")
        
        print("=" * 80)

if __name__ == "__main__":
    ver_usuarios() 