"""
settings_view.py — Configuración de la aplicación.
  - Estado de conexión MongoDB
  - Parámetros del pipeline
  - Zona de peligro (limpiar colección, reconectar)
"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSpinBox, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from .components import (
    BG_CARD, BG_PANEL, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
    BORDER, DANGER, SUCCESS, WARNING,
    STYLE_BTN_PRIMARY, STYLE_BTN_GHOST, STYLE_BTN_DANGER,
    shadow, h_separator, section_label, dim_label,
)

_STYLE_VALUE = f"""
    QLabel {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1px solid {BORDER}; border-radius: 6px;
        padding: 8px 12px; font-size: 12px; font-family: monospace;
    }}
"""
_STYLE_SPINBOX = f"""
    QSpinBox {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 6px;
        padding: 6px 10px; font-size: 12px; min-height: 32px;
    }}
    QSpinBox:focus {{ border-color: {ACCENT}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; }}
"""


class _PingWorker(QThread):
    result = Signal(bool, str)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        try:
            ok = self.db.test_connection()
            count = self.db.get_count() if ok else 0
            self.result.emit(ok, str(count))
        except Exception as e:
            self.result.emit(False, str(e))


class SettingsView(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db     = db
        self._ping  = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner  = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 24)

        # Encabezado
        h = QLabel("⚙  Configuración")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        layout.addWidget(h)
        layout.addWidget(dim_label("Conexión, pipeline y opciones de la aplicación."))
        layout.addWidget(h_separator())

        # ── Sección: Conexión ─────────────────────────────────────────────────
        layout.addWidget(section_label("CONEXIÓN  /  MONGODB"))
        layout.addWidget(self._connection_card())
        layout.addWidget(h_separator())

        # ── Sección: Pipeline ─────────────────────────────────────────────────
        layout.addWidget(section_label("PARÁMETROS DEL PIPELINE"))
        layout.addWidget(self._pipeline_card())
        layout.addWidget(h_separator())

        # ── Sección: Zona de peligro ──────────────────────────────────────────
        layout.addWidget(section_label("ZONA DE PELIGRO", DANGER))
        layout.addWidget(self._danger_card())

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── Tarjeta: Conexión ─────────────────────────────────────────────────────
    def _connection_card(self) -> QFrame:
        card = self._card()
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        # URI enmascarada
        uri  = getattr(self.db, "uri", "")
        masked = self._mask_uri(uri)

        row1 = self._kv_row("URI de conexión", masked)
        row2 = self._kv_row("Base de datos",   getattr(self.db.db, "name", "—"))
        row3 = self._kv_row("Colección",        self.db.collection.name)
        lay.addLayout(row1)
        lay.addLayout(row2)
        lay.addLayout(row3)

        # Estado de conexión
        status_row = QHBoxLayout()
        self.lbl_conn_status = QLabel("●  No verificado")
        self.lbl_conn_status.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        self.lbl_doc_count = QLabel("")
        self.lbl_doc_count.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        btn_ping = QPushButton("🔌  Verificar conexión")
        btn_ping.setStyleSheet(STYLE_BTN_GHOST)
        btn_ping.setCursor(Qt.PointingHandCursor)
        btn_ping.setMinimumHeight(36)
        btn_ping.clicked.connect(self._ping_connection)
        status_row.addWidget(self.lbl_conn_status)
        status_row.addWidget(self.lbl_doc_count)
        status_row.addStretch()
        status_row.addWidget(btn_ping)
        lay.addLayout(status_row)
        return card

    # ── Tarjeta: Pipeline ─────────────────────────────────────────────────────
    def _pipeline_card(self) -> QFrame:
        card = self._card()
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        # Límite de registros en dashboard
        row_limit = QHBoxLayout()
        lbl = QLabel("Registros máximos en Dashboard:")
        lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(10, 5000)
        self.spin_limit.setValue(200)
        self.spin_limit.setSingleStep(50)
        self.spin_limit.setStyleSheet(_STYLE_SPINBOX)
        self.spin_limit.setFixedWidth(100)
        row_limit.addWidget(lbl)
        row_limit.addStretch()
        row_limit.addWidget(self.spin_limit)
        lay.addLayout(row_limit)

        # Longitud máxima de texto para procesar
        row_maxlen = QHBoxLayout()
        lbl2 = QLabel("Longitud máxima de texto a procesar (chars):")
        lbl2.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        self.spin_maxlen = QSpinBox()
        self.spin_maxlen.setRange(100, 50000)
        self.spin_maxlen.setValue(5000)
        self.spin_maxlen.setSingleStep(500)
        self.spin_maxlen.setStyleSheet(_STYLE_SPINBOX)
        self.spin_maxlen.setFixedWidth(100)
        row_maxlen.addWidget(lbl2)
        row_maxlen.addStretch()
        row_maxlen.addWidget(self.spin_maxlen)
        lay.addLayout(row_maxlen)

        btn_save = QPushButton("💾  Guardar preferencias")
        btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
        btn_save.setMinimumHeight(40)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_prefs)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        lay.addLayout(btn_row)
        return card

    # ── Tarjeta: Zona de peligro ──────────────────────────────────────────────
    def _danger_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: #1a0f0f; border: 1px solid {DANGER}44;"
            f" border-radius: 10px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        row1 = QHBoxLayout()
        v1 = QVBoxLayout()

        lbl_title = QLabel("Vaciar colección completa")          # ← referencia directa
        lbl_title.setStyleSheet(f"color:{TEXT_MAIN}; font-size:13px; font-weight:600;")
        v1.addWidget(lbl_title)

        lbl_w = QLabel("Elimina permanentemente TODOS los documentos de la colección.")
        lbl_w.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        v1.addWidget(lbl_w)

        btn_clear = QPushButton("🗑  Vaciar colección")
        btn_clear.setStyleSheet(STYLE_BTN_DANGER)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setMinimumHeight(36)
        btn_clear.clicked.connect(self._clear_collection)
        row1.addLayout(v1, 1)
        row1.addWidget(btn_clear)
        lay.addLayout(row1)
        return card

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _ping_connection(self):
        self.lbl_conn_status.setText("●  Verificando…")
        self.lbl_conn_status.setStyleSheet(f"color:{WARNING}; font-size:12px;")
        self._ping = _PingWorker(self.db)
        self._ping.result.connect(self._on_ping_result)
        self._ping.start()

    def _on_ping_result(self, ok: bool, info: str):
        if ok:
            self.lbl_conn_status.setText("●  Conectado")
            self.lbl_conn_status.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")
            self.lbl_doc_count.setText(f"({info} documentos)")
        else:
            self.lbl_conn_status.setText(f"●  Error: {info[:60]}")
            self.lbl_conn_status.setStyleSheet(f"color:{DANGER}; font-size:12px;")
            self.lbl_doc_count.setText("")

    def _save_prefs(self):
        # En una app real se persistirían en .env o config.json
        QMessageBox.information(
            self, "Preferencias guardadas",
            f"Límite dashboard: {self.spin_limit.value()} registros\n"
            f"Longitud máxima: {self.spin_maxlen.value()} chars\n\n"
            "(Aplican al próximo inicio de sesión.)"
        )

    def _clear_collection(self):
        resp = QMessageBox.question(
            self,
            "Vaciar colección",
            "¿Eliminar TODOS los documentos de la colección?\nEsta acción NO se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        resp2 = QMessageBox.warning(
            self, "Confirmación final",
            "¿Confirmas que deseas vaciar toda la colección?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp2 != QMessageBox.Yes:
            return
        try:
            n = self.db.delete_all()
            QMessageBox.information(self, "Colección vaciada", f"{n} documentos eliminados.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

# ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: 10px; }}"
        )
        shadow(card, blur=16, offset_y=3, alpha=60)
        return card

    @staticmethod
    def _kv_row(label: str, value: str) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label + ":")
        lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        lbl.setFixedWidth(160)
        val = QLabel(value)
        val.setStyleSheet(_STYLE_VALUE)
        val.setWordWrap(False)
        row.addWidget(lbl)
        row.addWidget(val, 1)
        return row

    @staticmethod
    def _mask_uri(uri: str) -> str:
        """Oculta usuario y contraseña de la URI."""
        import re
        return re.sub(r"//[^@]+@", "//***:***@", uri)