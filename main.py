# En ETL/main.py
import sys
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication
from src.gui import MainWindow
from src.database import DatabaseManager # Importar la clase
from src.views.app_layout  import AppLayout

load_dotenv() # Cargar variables del .env

def main():
    app = QApplication(sys.argv)
    db = DatabaseManager(
        user=os.getenv("DB_USER"), 
        password=os.getenv("DB_PASS"), 
        cluster_url=os.getenv("DB_CLUSTER") 
    )

    window = MainWindow(db) # Aquí pasamos la instancia creada
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()