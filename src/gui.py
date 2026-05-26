from PySide6.QtWidgets import QMainWindow, QStackedWidget
from src.views.login_view import LoginWidget
from src.views.dashboard_view import AppLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ── Credenciales válidas: usuario → contraseña ────────────────────────────────
_VALID_CREDENTIALS = {
    "admin": "root",
    "user":  "root",
}

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("ETL Sentiment App")
        self.resize(900, 580)
        self.setMinimumSize(700, 450)

        self.main_stack = QStackedWidget()
        self.setCentralWidget(self.main_stack)

        # Índice 0 → Login
        self.login_page = LoginWidget(self.handle_login)
        self.main_stack.addWidget(self.login_page)

    # ── FIX: recibe y valida la contraseña ────────────────────────────────────
    def handle_login(self, username: str, password: str):
        expected = _VALID_CREDENTIALS.get(username)
        if expected is not None and password == expected:
            if self.main_stack.count() > 1:
                old = self.main_stack.widget(1)
                self.main_stack.removeWidget(old)
                old.deleteLater()

            app_layout = AppLayout(
                role=username,
                db_manager=self.db,
                logout_callback=self.handle_logout,
            )
            self.main_stack.addWidget(app_layout)
            self.main_stack.setCurrentIndex(1)
        else:
            self.login_page.mostrar_error("Usuario o contraseña incorrectos.")

    def handle_logout(self):
        self.main_stack.setCurrentIndex(0)
        self.login_page.limpiar_campos()
        if self.main_stack.count() > 1:
            old = self.main_stack.widget(1)
            self.main_stack.removeWidget(old)
            old.deleteLater()