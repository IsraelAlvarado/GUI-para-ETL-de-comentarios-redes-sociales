"""
app_layout.py — Layout principal post-login.
Sidebar de navegación con 4 secciones:
  ⚡ Analizar    (admin)
  📊 Dashboard
  📡 Extraer
  ⚙  Configuración
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import Qt

from .components import (
    BG_MAIN, BG_PANEL, SIDEBAR_BG, TEXT_MAIN, TEXT_DIM, ACCENT,
    BORDER, DANGER,
    STYLE_BTN_DANGER, shadow,
    SidebarButton,
)
from .analisis_view   import AnalisisView
from .dashboard_view  import DashboardView
from .extractor_view  import ExtractorView
from .settings_view   import SettingsView


class AppLayout(QWidget):
    def __init__(self, role: str, db, logout_callback):
        super().__init__()
        self.db     = db
        self.logout = logout_callback
        self.setStyleSheet(f"background-color: {BG_MAIN};")
        self._build(role)

    def _build(self, role: str):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sb_widget = QWidget()
        sb_widget.setFixedWidth(200)
        sb_widget.setStyleSheet(
            f"background-color: {SIDEBAR_BG}; border-right: 1px solid {BORDER};"
        )
        sb = QVBoxLayout(sb_widget)
        sb.setContentsMargins(12, 24, 12, 16)
        sb.setSpacing(6)

        logo = QLabel("◈  ETL App")
        logo.setStyleSheet(
            f"color: {ACCENT}; font-size: 15px; font-weight: 800; letter-spacing: 1px;"
        )
        logo.setContentsMargins(8, 0, 0, 8)
        sb.addWidget(logo)

        role_color = ACCENT if role == "admin" else TEXT_DIM
        role_bg    = "#0d2a1f" if role == "admin" else "#0d1e2e"
        chip = QLabel(f"{'👑 Admin' if role == 'admin' else '👤 User'}")
        chip.setStyleSheet(
            f"background-color: {role_bg}; color: {role_color};"
            f" border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600;"
        )
        chip.setFixedHeight(28)
        sb.addWidget(chip)
        sb.addSpacing(12)

        # Botones de navegación
        self.btn_analizar  = SidebarButton("⚡", "Analizar")
        self.btn_dashboard = SidebarButton("📊", "Dashboard")
        self.btn_extraer   = SidebarButton("📡", "Extraer")
        self.btn_config    = SidebarButton("⚙", "Configuración")

        if role != "admin":
            self.btn_analizar.setEnabled(False)
            self.btn_analizar.setToolTip("Solo administradores pueden ejecutar el pipeline ETL.")

        for btn in (self.btn_analizar, self.btn_dashboard, self.btn_extraer, self.btn_config):
            sb.addWidget(btn)

        sb.addStretch()

        btn_logout = QPushButton("⏻  Cerrar sesión")
        btn_logout.setStyleSheet(STYLE_BTN_DANGER)
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setMinimumHeight(38)
        btn_logout.clicked.connect(self.logout)
        sb.addWidget(btn_logout)

        # ── Stack de vistas ───────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_PANEL};")

        # Índice 0 — Analizar
        if role == "admin":
            self.stack.addWidget(AnalisisView(self.db))
        else:
            lbl = QLabel("⚠  Solo administradores\npueden ejecutar el pipeline ETL.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px;")
            self.stack.addWidget(lbl)

        # Índice 1 — Dashboard
        self.stack.addWidget(DashboardView(self.db))

        # Índice 2 — Extraer
        self.stack.addWidget(ExtractorView(self.db))

        # Índice 3 — Configuración
        self.stack.addWidget(SettingsView(self.db))

        # Conexión de botones
        self._nav_buttons = [
            self.btn_analizar,
            self.btn_dashboard,
            self.btn_extraer,
            self.btn_config,
        ]
        for idx, btn in enumerate(self._nav_buttons):
            btn.clicked.connect(lambda _, i=idx, b=btn: self._switch(i, b))

        # Vista por defecto
        default = 1 if role != "admin" else 0
        self._switch(default, self._nav_buttons[default])

        root.addWidget(sb_widget)
        root.addWidget(self.stack, 1)

    def _switch(self, index: int, active: SidebarButton):
        self.stack.setCurrentIndex(index)
        for btn in self._nav_buttons:
            btn.setChecked(btn is active)