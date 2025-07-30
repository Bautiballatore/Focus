#!/usr/bin/env python3
"""
Script para inicializar la base de datos
"""

import os
from app import app, db
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Inicializar la base de datos"""
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("✅ Base de datos inicializada correctamente")
        print("📊 Tablas creadas:")
        for table in db.metadata.tables:
            print(f"   - {table}")

if __name__ == "__main__":
    init_database() 