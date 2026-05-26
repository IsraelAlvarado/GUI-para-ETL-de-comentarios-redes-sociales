"""
gui.py — Ventana principal de la aplicación.
Gestiona login y el cambio al layout principal.
"""
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from src.views.login_view  import LoginWidget
from src.views.app_layout  import AppLayout

# Credenciales válidas: usuario → contraseña
_CREDENTIALS = {
    "admin": "root",
    "user":  "root",
}


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("ETL Sentiment App")
        self.resize(1000, 640)
        self.setMinimumSize(750, 480)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginWidget(self.handle_login)
        self.stack.addWidget(self.login_page)   # índice 0

    def handle_login(self, username: str, password: str):
        expected = _CREDENTIALS.get(username)
        if expected is not None and password == expected:
            self._clear_app_widget()
            app = AppLayout(
                role=username,
                db=self.db,
                logout_callback=self.handle_logout,
            )
            self.stack.addWidget(app)           # índice 1
            self.stack.setCurrentIndex(1)
        else:
            self.login_page.mostrar_error("Usuario o contraseña incorrectos.")

    def handle_logout(self):
        self.stack.setCurrentIndex(0)
        self.login_page.limpiar_campos()
        self._clear_app_widget()

    def _clear_app_widget(self):
        if self.stack.count() > 1:
            old = self.stack.widget(1)
            self.stack.removeWidget(old)
            old.deleteLater()