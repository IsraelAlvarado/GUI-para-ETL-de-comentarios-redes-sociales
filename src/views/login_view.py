"""
login_view.py — Pantalla de inicio de sesión.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

BG_LEFT   = "#0f1923"
BG_RIGHT  = "#1a2a3a"
ACCENT    = "#00d4aa"
ACCENT2   = "#0099ff"
TEXT_MAIN = "#e8f4f8"
TEXT_DIM  = "#7a9ab0"
CARD_BG   = "#162233"
BORDER    = "#1e3448"
ERR_COLOR = "#ff5f6d"

_STYLE_BASE  = f"QWidget {{ background-color: transparent; color: {TEXT_MAIN}; font-family: 'Segoe UI', 'Ubuntu', sans-serif; }}"
_STYLE_INPUT = f"""
    QLineEdit {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 8px;
        padding: 10px 14px; font-size: 14px;
    }}
    QLineEdit:focus {{ border: 1.5px solid {ACCENT}; }}
"""
_STYLE_BTN = f"""
    QPushButton {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 {ACCENT2});
        color: #0a1520; border: none; border-radius: 8px;
        padding: 11px; font-size: 14px; font-weight: 700; letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT2},stop:1 {ACCENT});
    }}
    QPushButton:pressed {{ padding: 12px 11px 10px 11px; }}
"""


class _InputField(QWidget):
    def __init__(self, label: str, placeholder: str, echo=QLineEdit.Normal):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(lbl)

        self.field = QLineEdit()
        self.field.setPlaceholderText(placeholder)
        self.field.setEchoMode(echo)
        self.field.setStyleSheet(_STYLE_INPUT)
        self.field.setMinimumHeight(42)
        layout.addWidget(self.field)

    def text(self) -> str:
        return self.field.text().strip()

    def clear(self):
        self.field.clear()


class LoginWidget(QWidget):
    def __init__(self, on_login_callback):
        super().__init__()
        self.on_login = on_login_callback
        self.setStyleSheet(_STYLE_BASE)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._left_panel(), 1)
        root.addWidget(self._right_panel(), 1)

    def _left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {BG_LEFT};")
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel("◈")
        icon.setStyleSheet(f"color: {ACCENT}; font-size: 52px;")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("ETL\nSentiment")
        title.setStyleSheet(
            f"color: {TEXT_MAIN}; font-size: 34px; font-weight: 800;"
            f" letter-spacing: 3px; line-height: 1.2;"
        )
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Análisis de sentimientos\nconectado a MongoDB")
        sub.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; line-height: 1.6;")
        sub.setAlignment(Qt.AlignCenter)

        divider = QFrame()
        divider.setFixedSize(40, 2)
        divider.setStyleSheet(f"background-color: {ACCENT};")

        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(divider, alignment=Qt.AlignCenter)
        layout.addWidget(sub)
        layout.addStretch()

        version = QLabel("v1.1.0")
        version.setStyleSheet(f"color: {BORDER}; font-size: 10px;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        layout.addSpacing(16)
        return panel

    def _right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {BG_RIGHT};")
        outer = QVBoxLayout(panel)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; }}"
        )
        card.setFixedWidth(360)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(36, 40, 36, 40)
        lay.setSpacing(20)

        heading = QLabel("Bienvenido")
        heading.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 22px; font-weight: 700;")
        hint = QLabel("Ingresa tus credenciales para continuar")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        hint.setWordWrap(True)

        lay.addWidget(heading)
        lay.addWidget(hint)
        lay.addSpacing(4)

        self._user_field = _InputField("USUARIO",    "admin  /  user")
        self._pass_field = _InputField("CONTRASEÑA", "••••••••", QLineEdit.Password)
        lay.addWidget(self._user_field)
        lay.addWidget(self._pass_field)

        self._lbl_error = QLabel("")
        self._lbl_error.setStyleSheet(f"color: {ERR_COLOR}; font-size: 12px;")
        self._lbl_error.setAlignment(Qt.AlignCenter)
        self._lbl_error.setWordWrap(True)
        self._lbl_error.hide()
        lay.addWidget(self._lbl_error)

        btn = QPushButton("INICIAR SESIÓN")
        btn.setStyleSheet(_STYLE_BTN)
        btn.setMinimumHeight(46)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._on_click)
        self._user_field.field.returnPressed.connect(self._on_click)
        self._pass_field.field.returnPressed.connect(self._on_click)
        lay.addWidget(btn)

        outer.addWidget(card)
        return panel

    def _on_click(self):
        self._lbl_error.hide()
        self.on_login(self._user_field.text(), self._pass_field.text())

    def mostrar_error(self, msg: str):
        self._lbl_error.setText(msg)
        self._lbl_error.show()

    def limpiar_campos(self):
        self._user_field.clear()
        self._pass_field.clear()
        self._lbl_error.hide()