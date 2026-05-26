import pandas as pd
from datetime import datetime
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QStackedWidget, QProgressBar, QFrame, QSizePolicy,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QGraphicsDropShadowEffect, QSplitter, QMessageBox, QFileDialog,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from src.etl_engine import ETLEngine

# ── Paleta ────────────────────────────────────────────────────────────────────
BG_MAIN    = "#0f1923"; BG_PANEL   = "#111f2e"; BG_CARD    = "#162233"
ACCENT     = "#00d4aa"; ACCENT2    = "#0099ff"; SIDEBAR_BG = "#0d1a27"
TEXT_MAIN  = "#e8f4f8"; TEXT_DIM   = "#7a9ab0"; BORDER     = "#1e3448"
DANGER     = "#ff5f6d"; SUCCESS    = "#00d4aa"; WARNING    = "#ffc107"
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

# ── Helpers de estilo ─────────────────────────────────────────────────────────
def _shadow(widget, blur=30, offset_y=6, alpha=100):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur); s.setOffset(0, offset_y)
    s.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(s)

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
    QComboBox::down-arrow {{ color: {ACCENT}; }}
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

# ─────────────────────────────────────────────────────────────────────────────
# Worker: ETL individual
# ─────────────────────────────────────────────────────────────────────────────
class ETLWorker(QThread):
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, raw_text: str, db_manager):
        super().__init__()
        self.raw_text = raw_text
        self.db       = db_manager

    def run(self):
        try:
            doc = ETLEngine.run(self.raw_text)
            self.db.collection.insert_one(doc)
            self.finished.emit(doc)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Worker: ETL en lote desde archivo
# ─────────────────────────────────────────────────────────────────────────────
class BatchETLWorker(QThread):
    progress = Signal(int, int)   # procesados, total
    row_done = Signal(dict)       # doc insertado
    finished = Signal(int, int)   # éxitos, errores

    def __init__(self, texts: list, db_manager):
        super().__init__()
        self.texts = texts
        self.db    = db_manager

    def run(self):
        success = errors = 0
        total = len(self.texts)
        for i, text in enumerate(self.texts):
            try:
                doc = ETLEngine.run(str(text).strip())
                self.db.collection.insert_one(doc)
                success += 1
                self.row_done.emit(doc)
            except Exception:
                errors += 1
            self.progress.emit(i + 1, total)
        self.finished.emit(success, errors)


# ─────────────────────────────────────────────────────────────────────────────
# Tarjeta de resultado ETL
# ─────────────────────────────────────────────────────────────────────────────
class ResultCard(QFrame):
    def __init__(self, doc: dict):
        super().__init__()
        color = CAT_COLORS.get(doc.get("categoria", "Neutral"), TEXT_DIM)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-left: 4px solid {color};
                border-radius: 10px;
            }}
        """)
        _shadow(self, blur=20, offset_y=4, alpha=80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Fila 1: texto + categoría
        top = QHBoxLayout()
        txt = doc.get("texto_original", doc.get("texto", ""))
        lbl_txt = QLabel(f'"{txt[:90]}{"…" if len(txt) > 90 else ""}"')
        lbl_txt.setStyleSheet(f"color:{TEXT_DIM}; font-style:italic; font-size:12px;")
        lbl_txt.setWordWrap(True)

        cat = doc.get("categoria", "—")
        lbl_cat = QLabel(cat)
        lbl_cat.setStyleSheet(f"""
            background-color:{color}22; color:{color};
            border:1px solid {color}; border-radius:5px;
            padding:2px 10px; font-size:11px; font-weight:700;
        """)
        lbl_cat.setFixedHeight(24)
        lbl_cat.setAlignment(Qt.AlignCenter)
        top.addWidget(lbl_txt, 1); top.addWidget(lbl_cat)
        layout.addLayout(top)

        # Fila 2: métricas
        metrics = doc.get("metricas", {})
        grid = QHBoxLayout(); grid.setSpacing(12)
        grid.addWidget(self._chip("Polaridad",    f'{doc["polaridad"]:+.3f}', ACCENT))
        grid.addWidget(self._chip("Subjetividad", f'{doc["subjetividad"]:.3f}', ACCENT2))
        grid.addWidget(self._chip("Intensidad",   doc.get("intensidad", "—"), WARNING))
        grid.addWidget(self._chip("Palabras",     str(metrics.get("num_palabras", "—")), TEXT_DIM))
        grid.addWidget(self._chip("Oraciones",    str(metrics.get("num_oraciones", "—")), TEXT_DIM))
        grid.addWidget(self._chip("Dens. Léxica", f'{metrics.get("densidad_lexica", 0):.2f}', TEXT_DIM))
        grid.addStretch()
        layout.addLayout(grid)

        # Fila 3: keywords
        kw = metrics.get("palabras_clave", [])
        if kw:
            kw_row = QHBoxLayout(); kw_row.setSpacing(6)
            kw_row.addWidget(QLabel("Keywords:"))
            kw_row.children()[0].widget().setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            for w in kw[:6]:
                pill = QLabel(w)
                pill.setStyleSheet(f"""
                    background-color:#1a3050; color:{ACCENT};
                    border-radius:4px; padding:1px 7px; font-size:10px;
                """)
                kw_row.addWidget(pill)
            kw_row.addStretch()
            layout.addLayout(kw_row)

    @staticmethod
    def _chip(label: str, value: str, color: str) -> QWidget:
        w = QFrame()
        w.setStyleSheet("background-color:#0d1e2e; border-radius:6px;")
        lay = QVBoxLayout(w); lay.setContentsMargins(10, 6, 10, 6); lay.setSpacing(2)
        lv = QLabel(value); lv.setStyleSheet(f"color:{color}; font-size:15px; font-weight:700;")
        ll = QLabel(label.upper()); ll.setStyleSheet(f"color:{TEXT_DIM}; font-size:9px; letter-spacing:1px;")
        lay.addWidget(lv); lay.addWidget(ll)
        return w


# ─────────────────────────────────────────────────────────────────────────────
# Vista de Análisis ETL (manual + carga de archivo)
# ─────────────────────────────────────────────────────────────────────────────
class AnalisisView(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db           = db_manager
        self.worker       = None
        self.batch_worker = None
        self._file_df     = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        # Scroll exterior para toda la vista
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:transparent;}")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Encabezado ────────────────────────────────────────────────────────
        h = QLabel("Pipeline ETL — Análisis de Texto")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        sub = QLabel("Extract → Transform (limpieza NLP + features) → Load (MongoDB)")
        sub.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        layout.addWidget(h); layout.addWidget(sub)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.HLine)
        sep0.setStyleSheet(f"color:{BORDER};"); layout.addWidget(sep0)

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN A: Entrada manual
        # ═══════════════════════════════════════════════════════════════════
        sec_a = QLabel("A  /  ENTRADA MANUAL")
        sec_a.setStyleSheet(f"color:{ACCENT}; font-size:10px; font-weight:700; letter-spacing:2px;")
        layout.addWidget(sec_a)

        lbl = QLabel("TEXTO DE ENTRADA")
        lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:10px; letter-spacing:1px;")
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Ingresa el texto a procesar…")
        self.input_text.setStyleSheet(STYLE_INPUT)
        self.input_text.setMinimumHeight(44)
        self.input_text.returnPressed.connect(self.ejecutar_etl)
        layout.addWidget(lbl); layout.addWidget(self.input_text)

        row_a = QHBoxLayout(); row_a.setSpacing(12)
        self.progress_manual = QProgressBar()
        self.progress_manual.setValue(0); self.progress_manual.setTextVisible(False)
        self.progress_manual.setFixedHeight(10)
        self.progress_manual.setStyleSheet(STYLE_PROGRESS)

        self.btn_run = QPushButton("▶  Ejecutar ETL")
        self.btn_run.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_run.setMinimumHeight(44); self.btn_run.setFixedWidth(180)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.ejecutar_etl)

        row_a.addWidget(self.progress_manual, 1); row_a.addWidget(self.btn_run)
        layout.addLayout(row_a)

        self.lbl_status_manual = QLabel("")
        self.lbl_status_manual.setStyleSheet(f"color:{ACCENT}; font-size:11px;")
        layout.addWidget(self.lbl_status_manual)

        # Separador entre secciones
        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"color:{BORDER}; margin-top:6px; margin-bottom:6px;")
        layout.addWidget(sep1)

        # ═══════════════════════════════════════════════════════════════════
        # SECCIÓN B: Carga masiva desde archivo
        # ═══════════════════════════════════════════════════════════════════
        sec_b = QLabel("B  /  CARGA MASIVA DESDE ARCHIVO")
        sec_b.setStyleSheet(f"color:{ACCENT2}; font-size:10px; font-weight:700; letter-spacing:2px;")
        layout.addWidget(sec_b)

        hint_b = QLabel("Formatos soportados: CSV · Excel (.xlsx / .xls) · TSV")
        hint_b.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        layout.addWidget(hint_b)

        # Fila: botón seleccionar archivo + path
        file_row = QHBoxLayout(); file_row.setSpacing(10)
        self.btn_file = QPushButton("📂  Seleccionar archivo…")
        self.btn_file.setStyleSheet(STYLE_BTN_FILE)
        self.btn_file.setMinimumHeight(40); self.btn_file.setFixedWidth(220)
        self.btn_file.setCursor(Qt.PointingHandCursor)
        self.btn_file.clicked.connect(self._select_file)

        self.lbl_file = QLabel("Ningún archivo seleccionado")
        self.lbl_file.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        file_row.addWidget(self.btn_file); file_row.addWidget(self.lbl_file, 1)
        layout.addLayout(file_row)

        # Fila: seleccionar columna + botón procesar
        col_row = QHBoxLayout(); col_row.setSpacing(10)
        lbl_col = QLabel("Columna de texto:")
        lbl_col.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        lbl_col.setFixedWidth(120)

        self.combo_col = QComboBox()
        self.combo_col.setStyleSheet(STYLE_COMBO)
        self.combo_col.setMinimumWidth(180)
        self.combo_col.setPlaceholderText("— cargue un archivo primero —")
        self.combo_col.setEnabled(False)

        self.btn_batch = QPushButton("⚡  Procesar Dataset")
        self.btn_batch.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_batch.setMinimumHeight(40); self.btn_batch.setFixedWidth(200)
        self.btn_batch.setCursor(Qt.PointingHandCursor)
        self.btn_batch.setEnabled(False)
        self.btn_batch.clicked.connect(self._ejecutar_batch)

        col_row.addWidget(lbl_col); col_row.addWidget(self.combo_col, 1)
        col_row.addWidget(self.btn_batch)
        layout.addLayout(col_row)

        # Barra de progreso de lote + estado
        self.progress_batch = QProgressBar()
        self.progress_batch.setValue(0); self.progress_batch.setTextVisible(True)
        self.progress_batch.setFormat("  %v / %m filas")
        self.progress_batch.setFixedHeight(20)
        self.progress_batch.setStyleSheet(STYLE_PROGRESS + f"QProgressBar{{color:{TEXT_DIM}; font-size:10px;}}")
        self.progress_batch.hide()

        self.lbl_status_batch = QLabel("")
        self.lbl_status_batch.setStyleSheet(f"color:{ACCENT2}; font-size:11px;")
        layout.addWidget(self.progress_batch)
        layout.addWidget(self.lbl_status_batch)

        # Separador final
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color:{BORDER}; margin-top:6px;")
        layout.addWidget(sep2)

        # ═══════════════════════════════════════════════════════════════════
        # Área de resultados
        # ═══════════════════════════════════════════════════════════════════
        lbl_res = QLabel("RESULTADOS RECIENTES")
        lbl_res.setStyleSheet(f"color:{TEXT_DIM}; font-size:10px; letter-spacing:1px;")
        layout.addWidget(lbl_res)

        self.results_container = QWidget()
        self.results_layout    = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.addStretch()
        layout.addWidget(self.results_container)

        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── ETL manual ────────────────────────────────────────────────────────────
    def ejecutar_etl(self):
        texto = self.input_text.text().strip()
        if not texto:
            return
        self.btn_run.setEnabled(False)
        self.input_text.setEnabled(False)
        self._set_manual_status("⏳ [E] Extrayendo texto…", 15)

        self.worker = ETLWorker(texto, self.db)
        self.worker.finished.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, lambda: self._set_manual_status("🔄 [T] Transformando y limpiando…", 50))
        QTimer.singleShot(700, lambda: self._set_manual_status("💾 [L] Cargando en MongoDB…", 80))

    def _on_done(self, doc: dict):
        self._set_manual_status("✅ Pipeline completado.", 100)
        self._add_card(doc)
        self.input_text.clear()
        self.btn_run.setEnabled(True)
        self.input_text.setEnabled(True)

    def _on_error(self, msg: str):
        self._set_manual_status(f"❌ Error: {msg}", 0)
        self.btn_run.setEnabled(True)
        self.input_text.setEnabled(True)

    def _set_manual_status(self, msg: str, pct: int):
        self.lbl_status_manual.setText(msg)
        self.progress_manual.setValue(pct)

    # ── Selección de archivo ──────────────────────────────────────────────────
    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar dataset",
            "", "Archivos de datos (*.csv *.tsv *.xlsx *.xls);;Todos (*.*)"
        )
        if not path:
            return
        try:
            if path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(path)
            elif path.endswith(".tsv"):
                df = pd.read_csv(path, sep="\t")
            else:
                df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        except Exception as e:
            QMessageBox.critical(self, "Error al leer archivo", str(e)); return

        if df.empty:
            QMessageBox.warning(self, "Archivo vacío", "El archivo no contiene datos."); return

        self._file_df = df
        fname = path.split("/")[-1]
        self.lbl_file.setText(f"✔  {fname}  ({len(df)} filas, {len(df.columns)} columnas)")
        self.lbl_file.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")

        # Poblar combo con columnas tipo texto
        text_cols = [c for c in df.columns if df[c].dtype == object]
        if not text_cols:
            text_cols = list(df.columns)
        self.combo_col.clear()
        self.combo_col.addItems(text_cols)
        self.combo_col.setEnabled(True)
        self.btn_batch.setEnabled(True)
        self.lbl_status_batch.setText(f"Archivo listo. Selecciona la columna de texto y presiona Procesar.")
        self.lbl_status_batch.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")

    # ── ETL en lote ───────────────────────────────────────────────────────────
    def _ejecutar_batch(self):
        if self._file_df is None:
            return
        col = self.combo_col.currentText()
        texts = self._file_df[col].dropna().astype(str).str.strip()
        texts = texts[texts != ""].tolist()
        if not texts:
            QMessageBox.warning(self, "Sin datos", "La columna seleccionada no tiene texto válido."); return

        self.btn_batch.setEnabled(False)
        self.btn_file.setEnabled(False)
        self.combo_col.setEnabled(False)
        self.progress_batch.setMaximum(len(texts))
        self.progress_batch.setValue(0)
        self.progress_batch.show()
        self.lbl_status_batch.setStyleSheet(f"color:{ACCENT2}; font-size:11px;")
        self.lbl_status_batch.setText(f"⏳ Procesando {len(texts)} registros…")

        self.batch_worker = BatchETLWorker(texts, self.db)
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.row_done.connect(self._add_card)
        self.batch_worker.finished.connect(self._on_batch_done)
        self.batch_worker.start()

    def _on_batch_progress(self, current: int, total: int):
        self.progress_batch.setValue(current)
        self.lbl_status_batch.setText(f"🔄 Procesando fila {current} / {total}…")

    def _on_batch_done(self, success: int, errors: int):
        self.lbl_status_batch.setStyleSheet(f"color:{SUCCESS}; font-size:11px;")
        self.lbl_status_batch.setText(
            f"✅ Lote completado — {success} registros insertados"
            + (f", {errors} errores omitidos." if errors else ".")
        )
        self.btn_batch.setEnabled(True)
        self.btn_file.setEnabled(True)
        self.combo_col.setEnabled(True)

    # ── Shared ────────────────────────────────────────────────────────────────
    def _add_card(self, doc: dict):
        card = ResultCard(doc)
        self.results_layout.insertWidget(0, card)


# ─────────────────────────────────────────────────────────────────────────────
# ChartCanvas — FIX: constrained_layout elimina las warnings de tight_layout
# ─────────────────────────────────────────────────────────────────────────────
class ChartCanvas(FigureCanvas):
    def __init__(self, width=5, height=3):
        # FIX: usar constrained_layout en lugar de llamar a tight_layout()
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


# ─────────────────────────────────────────────────────────────────────────────
# Vista Dashboard
# ─────────────────────────────────────────────────────────────────────────────
class DashboardView(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.df = pd.DataFrame()
        self._build()
        self.load_data()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        h   = QLabel("Dashboard — Datos MongoDB")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        sub = QLabel("Últimos 100 registros   •   Procesado con Pandas")
        sub.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")

        btn_refresh = QPushButton("⟳  Actualizar")
        btn_refresh.setStyleSheet(STYLE_BTN_GHOST)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.load_data)

        hd = QVBoxLayout(); hd.addWidget(h); hd.addWidget(sub)
        header_row.addLayout(hd, 1); header_row.addWidget(btn_refresh)
        layout.addLayout(header_row)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{BORDER};"); layout.addWidget(sep)

        # Stat chips
        self.stats_row = QHBoxLayout(); self.stats_row.setSpacing(12)
        self.chip_total = self._stat_chip("Total registros",    "—")
        self.chip_pol   = self._stat_chip("Polaridad media",    "—")
        self.chip_sub   = self._stat_chip("Subjetividad media", "—")
        self.chip_pos   = self._stat_chip("% Positivos",        "—")
        for c in (self.chip_total, self.chip_pol, self.chip_sub, self.chip_pos):
            self.stats_row.addWidget(c)
        self.stats_row.addStretch()
        layout.addLayout(self.stats_row)

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("QSplitter::handle{background:#1e3448; height:4px;}")

        charts_widget = QWidget()
        charts_widget.setStyleSheet(f"background-color:{BG_PANEL};")
        charts_layout = QHBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 8, 0, 8); charts_layout.setSpacing(12)
        self.chart_dist = ChartCanvas(height=3)
        self.chart_cat  = ChartCanvas(height=3)
        charts_layout.addWidget(self.chart_dist)
        charts_layout.addWidget(self.chart_cat)

        table_widget = QWidget()
        table_widget.setStyleSheet(f"background-color:{BG_PANEL};")
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 4, 0, 0)
        self.table = QTableWidget()
        self.table.setStyleSheet(STYLE_TABLE)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.table)

        splitter.addWidget(charts_widget)
        splitter.addWidget(table_widget)
        splitter.setSizes([240, 360])
        layout.addWidget(splitter, 1)

        self.lbl_empty = QLabel(
            "Sin datos en la base de datos aún.\n"
            "Ejecuta el pipeline ETL para poblar la colección."
        )
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet(f"color:{TEXT_DIM}; font-size:13px;")
        self.lbl_empty.hide()
        layout.addWidget(self.lbl_empty)

    def load_data(self):
        try:
            raw = list(self.db.collection.find().sort("fecha", -1).limit(100))
        except Exception as e:
            QMessageBox.critical(self, "Error MongoDB", str(e)); return

        if not raw:
            self.lbl_empty.show(); self.table.hide()
            self._clear_charts(); return

        self.lbl_empty.hide(); self.table.show()

        df = pd.DataFrame(raw)
        df["fecha"]        = pd.to_datetime(df["fecha"],       errors="coerce") if "fecha"        in df.columns else pd.NaT
        df["polaridad"]    = pd.to_numeric(df["polaridad"],    errors="coerce").fillna(0)          if "polaridad"    in df.columns else 0.0
        df["subjetividad"] = pd.to_numeric(df["subjetividad"], errors="coerce").fillna(0)          if "subjetividad" in df.columns else 0.0
        df["texto"]        = df["texto"].astype(str).str[:80]    if "texto"      in df.columns else ""
        df["categoria"]    = df["categoria"].fillna("—")          if "categoria"  in df.columns else "—"
        df["intensidad"]   = df["intensidad"].fillna("—")         if "intensidad" in df.columns else "—"
        self.df = df

        self._update_chip(self.chip_total, "Total registros",    str(len(df)))
        self._update_chip(self.chip_pol,   "Polaridad media",    f'{df["polaridad"].mean():+.3f}')
        self._update_chip(self.chip_sub,   "Subjetividad media", f'{df["subjetividad"].mean():.3f}')
        pct_pos = (df["polaridad"] > 0.05).mean() * 100
        self._update_chip(self.chip_pos,   "% Positivos",        f'{pct_pos:.1f}%')

        cols   = ["texto", "polaridad", "subjetividad", "categoria", "intensidad", "fecha"]
        labels = ["Texto", "Polaridad", "Subjetividad", "Categoría", "Intensidad", "Fecha"]
        present_cols   = [c for c in cols if c in df.columns]
        present_labels = [labels[cols.index(c)] for c in present_cols]
        df_view = df[present_cols]

        self.table.setColumnCount(len(df_view.columns))
        self.table.setRowCount(len(df_view))
        self.table.setHorizontalHeaderLabels(present_labels)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        for i, row in df_view.iterrows():
            for j, val in enumerate(row):
                item = QTableWidgetItem(
                    val.strftime("%Y-%m-%d %H:%M") if hasattr(val, "strftime") else str(val)
                )
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if present_cols[j] == "polaridad":
                    try:
                        v = float(val)
                        item.setForeground(
                            QColor(SUCCESS) if v > 0.05 else
                            QColor(DANGER)  if v < -0.05 else
                            QColor(TEXT_DIM)
                        )
                    except: pass
                self.table.setItem(i, j, item)

        self._draw_histogram(df)
        self._draw_categories(df)

    def _draw_histogram(self, df: pd.DataFrame):
        self.chart_dist.clear()
        ax = self.chart_dist.ax()
        vals = df["polaridad"].dropna()
        ax.hist(vals, bins=20, color=ACCENT, alpha=0.8, edgecolor="#0d1e2e")
        ax.axvline(0, color=TEXT_DIM, linewidth=1, linestyle="--", alpha=0.6)
        ax.set_title("Distribución de Polaridad", color=TEXT_MAIN, fontsize=10, pad=8)
        ax.set_xlabel("Polaridad", color=TEXT_DIM, fontsize=8)
        ax.set_ylabel("Frecuencia", color=TEXT_DIM, fontsize=8)
        # FIX: eliminado tight_layout(), constrained_layout lo gestiona solo
        self.chart_dist.draw()

    def _draw_categories(self, df: pd.DataFrame):
        self.chart_cat.clear()
        ax = self.chart_cat.ax()
        if "categoria" not in df.columns:
            self.chart_cat.draw(); return
        counts = df["categoria"].value_counts()
        colors = [CAT_COLORS.get(c, TEXT_DIM) for c in counts.index]
        bars   = ax.barh(counts.index.tolist(), counts.values, color=colors, height=0.6)
        ax.set_title("Registros por Categoría", color=TEXT_MAIN, fontsize=10, pad=8)
        ax.set_xlabel("Cantidad", color=TEXT_DIM, fontsize=8)
        for bar, val in zip(bars, counts.values):
            ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", color=TEXT_MAIN, fontsize=8)
        # FIX: eliminado tight_layout()
        self.chart_cat.draw()

    def _clear_charts(self):
        for c in (self.chart_dist, self.chart_cat):
            c.clear(); c.draw()

    @staticmethod
    def _stat_chip(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color:{BG_CARD}; border:1px solid {BORDER};
                border-radius:10px;
            }}
        """)
        _shadow(card, blur=16, offset_y=3, alpha=70)
        lay = QVBoxLayout(card); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(3)
        card._lbl_val  = QLabel(value)
        card._lbl_val.setStyleSheet(f"color:{ACCENT}; font-size:22px; font-weight:800;")
        card._lbl_name = QLabel(label.upper())
        card._lbl_name.setStyleSheet(f"color:{TEXT_DIM}; font-size:9px; letter-spacing:1px;")
        lay.addWidget(card._lbl_val); lay.addWidget(card._lbl_name)
        card.setFixedHeight(76)
        return card

    @staticmethod
    def _update_chip(chip: QFrame, label: str, value: str):
        chip._lbl_val.setText(value)
        chip._lbl_name.setText(label.upper())


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar button
# ─────────────────────────────────────────────────────────────────────────────
STYLE_BTN_SIDEBAR = f"""
    QPushButton {{
        background-color:transparent; color:{TEXT_DIM};
        border:none; border-radius:8px; padding:12px 16px;
        text-align:left; font-size:13px; font-weight:500;
    }}
    QPushButton:hover {{ background-color:#1a2e42; color:{TEXT_MAIN}; }}
    QPushButton:checked {{
        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0d2a3f,stop:1 #0d2237);
        color:{ACCENT}; border-left:3px solid {ACCENT};
    }}
"""

class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(True)
        self.setStyleSheet(STYLE_BTN_SIDEBAR)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(46)


# ─────────────────────────────────────────────────────────────────────────────
# AppLayout
# ─────────────────────────────────────────────────────────────────────────────
STYLE_BTN_DANGER = f"""
    QPushButton {{
        background-color:transparent; color:{DANGER};
        border:1px solid {DANGER}; border-radius:8px;
        padding:7px 16px; font-size:12px; font-weight:600;
    }}
    QPushButton:hover {{ background-color:{DANGER}; color:white; }}
"""

class AppLayout(QWidget):
    def __init__(self, role: str, db_manager, logout_callback):
        super().__init__()
        self.db     = db_manager
        self.logout = logout_callback
        self.setStyleSheet(f"background-color:{BG_MAIN};")
        self._build(role)

    def _build(self, role: str):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        sb_widget = QWidget()
        sb_widget.setFixedWidth(200)
        sb_widget.setStyleSheet(f"background-color:{SIDEBAR_BG}; border-right:1px solid {BORDER};")
        sb = QVBoxLayout(sb_widget)
        sb.setContentsMargins(12, 24, 12, 16); sb.setSpacing(6)

        logo = QLabel("◈  ETL App")
        logo.setStyleSheet(f"color:{ACCENT}; font-size:15px; font-weight:800; letter-spacing:1px;")
        logo.setContentsMargins(8, 0, 0, 8); sb.addWidget(logo)

        chip = QLabel(f"{'👑 Admin' if role == 'admin' else '👤 User'}")
        chip.setStyleSheet(f"""
            background-color:{'#0d2a1f' if role=='admin' else '#0d1e2e'};
            color:{ACCENT if role=='admin' else TEXT_DIM};
            border-radius:6px; padding:4px 10px; font-size:11px; font-weight:600;
        """)
        chip.setFixedHeight(28); sb.addWidget(chip)
        sb.addSpacing(12)

        self.btn_analizar  = SidebarButton("⚡", "Analizar")
        self.btn_dashboard = SidebarButton("📊", "Dashboard")
        if role != "admin":
            self.btn_analizar.setEnabled(False)
            self.btn_analizar.setToolTip("Solo administradores")
        sb.addWidget(self.btn_analizar)
        sb.addWidget(self.btn_dashboard)
        sb.addStretch()

        btn_logout = QPushButton("⏻  Cerrar sesión")
        btn_logout.setStyleSheet(STYLE_BTN_DANGER)
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setMinimumHeight(38)
        btn_logout.clicked.connect(self.logout)
        sb.addWidget(btn_logout)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color:{BG_PANEL};")

        if role == "admin":
            self.stack.addWidget(AnalisisView(self.db))
        else:
            lbl = QLabel("⚠  Solo administradores\npueden ejecutar el pipeline ETL.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:14px;")
            self.stack.addWidget(lbl)

        self.stack.addWidget(DashboardView(self.db))

        self.btn_analizar.setChecked(True)
        self.btn_analizar.clicked.connect(lambda: self._switch(0, self.btn_analizar))
        self.btn_dashboard.clicked.connect(lambda: self._switch(1, self.btn_dashboard))

        root.addWidget(sb_widget)
        root.addWidget(self.stack, 1)

    def _switch(self, index: int, active: SidebarButton):
        self.stack.setCurrentIndex(index)
        for btn in (self.btn_analizar, self.btn_dashboard):
            btn.setChecked(btn is active)