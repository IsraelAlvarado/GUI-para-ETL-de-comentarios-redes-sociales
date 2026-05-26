"""
components.py — Design system compartido para ETL Sentiment App.
Contiene: paleta, estilos, helpers y widgets reutilizables.
"""
import matplotlib
matplotlib.use("QtAgg")  # Debe llamarse antes de importar FigureCanvas

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QSizePolicy, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# ── Paleta ────────────────────────────────────────────────────────────────────
BG_MAIN    = "#0f1923"
BG_PANEL   = "#111f2e"
BG_CARD    = "#162233"
ACCENT     = "#00d4aa"
ACCENT2    = "#0099ff"
SIDEBAR_BG = "#0d1a27"
TEXT_MAIN  = "#e8f4f8"
TEXT_DIM   = "#7a9ab0"
BORDER     = "#1e3448"
DANGER     = "#ff5f6d"
SUCCESS    = "#00d4aa"
WARNING    = "#ffc107"
MUTED      = "#1e3448"

CAT_COLORS = {
    "Muy Positivo":      "#00d4aa",
    "Positivo Objetivo": "#4dc9a0",
    "Positivo":          "#7ecfa8",
    "Neutral":           "#7a9ab0",
    "Neutral Subjetivo": "#9ab0c4",
    "Negativo":          "#ff8c7a",
    "Negativo Objetivo": "#ff6b55",
    "Muy Negativo":      "#ff5f6d",
}

# ── Estilos ───────────────────────────────────────────────────────────────────
STYLE_INPUT = f"""
    QLineEdit {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 8px;
        padding: 10px 14px; font-size: 13px;
    }}
    QLineEdit:focus {{ border: 1.5px solid {ACCENT}; }}
"""
STYLE_COMBO = f"""
    QComboBox {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 8px;
        padding: 8px 12px; font-size: 12px; min-height: 36px;
    }}
    QComboBox:focus {{ border: 1.5px solid {ACCENT}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1px solid {BORDER}; selection-background-color: #1a3050;
    }}
"""
STYLE_BTN_PRIMARY = f"""
    QPushButton {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 {ACCENT2});
        color: #0a1520; border: none; border-radius: 8px;
        padding: 10px 24px; font-size: 13px; font-weight: 700;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT2},stop:1 {ACCENT});
    }}
    QPushButton:disabled {{ background: {MUTED}; color: {TEXT_DIM}; }}
"""
STYLE_BTN_GHOST = f"""
    QPushButton {{
        background-color: transparent; color: {ACCENT};
        border: 1px solid {ACCENT}; border-radius: 8px;
        padding: 7px 18px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: #0d2a3a; }}
    QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {MUTED}; }}
"""
STYLE_BTN_DANGER = f"""
    QPushButton {{
        background-color: transparent; color: {DANGER};
        border: 1px solid {DANGER}; border-radius: 8px;
        padding: 7px 18px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {DANGER}; color: white; }}
    QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {MUTED}; }}
"""
STYLE_BTN_FILE = f"""
    QPushButton {{
        background-color: #0d1e2e; color: {ACCENT2};
        border: 1px dashed {ACCENT2}; border-radius: 8px;
        padding: 10px 20px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background-color: #0d2a3a; border-style: solid; }}
"""
STYLE_PROGRESS = f"""
    QProgressBar {{
        background-color: #0d1e2e; border: 1px solid {BORDER};
        border-radius: 6px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 {ACCENT2});
        border-radius: 6px;
    }}
"""
STYLE_TABLE = f"""
    QTableWidget {{
        background-color: {BG_CARD}; color: {TEXT_MAIN};
        border: none; gridline-color: {BORDER}; font-size: 12px;
    }}
    QHeaderView::section {{
        background-color: {SIDEBAR_BG}; color: {ACCENT};
        border: none; border-bottom: 1px solid {BORDER};
        padding: 8px; font-size: 11px; font-weight: 700; letter-spacing: 1px;
    }}
    QTableWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {BORDER}; }}
    QTableWidget::item:selected {{ background-color: #1a3050; color: {TEXT_MAIN}; }}
    QScrollBar:vertical {{ background: {BG_CARD}; width: 8px; border-radius: 4px; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; }}
"""
STYLE_BTN_SIDEBAR = f"""
    QPushButton {{
        background-color: transparent; color: {TEXT_DIM};
        border: none; border-radius: 8px; padding: 12px 16px;
        text-align: left; font-size: 13px; font-weight: 500;
    }}
    QPushButton:hover {{ background-color: #1a2e42; color: {TEXT_MAIN}; }}
    QPushButton:checked {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0d2a3f,stop:1 #0d2237);
        color: {ACCENT}; border-left: 3px solid {ACCENT};
    }}
    QPushButton:disabled {{ color: #2a4a60; }}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def shadow(widget, blur: int = 30, offset_y: int = 6, alpha: int = 100):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, offset_y)
    s.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(s)


def h_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(f"color: {BORDER};")
    return sep


def section_label(text: str, color: str = ACCENT) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
    )
    return lbl


def dim_label(text: str, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: {size}px;")
    return lbl


# ── Metric chip (pequeño, dentro de tarjetas) ─────────────────────────────────
def metric_chip(label: str, value: str, color: str) -> QWidget:
    w = QFrame()
    w.setStyleSheet("background-color: #0d1e2e; border-radius: 6px;")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(10, 6, 10, 6)
    lay.setSpacing(2)
    lv = QLabel(value)
    lv.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 700;")
    ll = QLabel(label.upper())
    ll.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
    lay.addWidget(lv)
    lay.addWidget(ll)
    return w


# ── StatCard (grande, para la fila de KPIs del dashboard) ────────────────────
class StatCard(QFrame):
    def __init__(self, label: str, value: str = "—", color: str = ACCENT):
        super().__init__()
        self._color = color
        self.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-radius: 10px; }}"
        )
        shadow(self, blur=16, offset_y=3, alpha=70)
        self.setFixedHeight(76)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(3)

        self._val  = QLabel(value)
        self._val.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 800;"
        )
        self._name = QLabel(label.upper())
        self._name.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px;"
        )
        lay.addWidget(self._val)
        lay.addWidget(self._name)

    def update(self, value: str, label: str | None = None):
        self._val.setText(value)
        if label:
            self._name.setText(label.upper())


# ── ChartCanvas ───────────────────────────────────────────────────────────────
class ChartCanvas(FigureCanvas):
    def __init__(self, width: int = 5, height: int = 3):
        fig = Figure(figsize=(width, height), facecolor="#162233",
                     constrained_layout=True)
        super().__init__(fig)
        self.fig = fig
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def clear(self):
        self.fig.clear()

    def ax(self, **kwargs):
        a = self.fig.add_subplot(111, **kwargs)
        a.set_facecolor("#0d1e2e")
        a.tick_params(colors="#7a9ab0", labelsize=9)
        for spine in a.spines.values():
            spine.set_edgecolor("#1e3448")
        return a


# ── SidebarButton ─────────────────────────────────────────────────────────────
class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(True)
        self.setStyleSheet(STYLE_BTN_SIDEBAR)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(46)