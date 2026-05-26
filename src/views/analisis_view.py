"""
analisis_view.py — Vista de análisis ETL.
  - Entrada manual de texto
  - Carga masiva desde CSV / Excel / TSV
  - Tarjetas de resultado
"""
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QProgressBar, QFrame, QScrollArea, QFileDialog,
    QComboBox, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from src.etl_engine import ETLEngine
from .components import (
    BG_CARD, BORDER, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
    WARNING, SUCCESS, MUTED,
    CAT_COLORS, STYLE_INPUT, STYLE_COMBO, STYLE_BTN_PRIMARY,
    STYLE_BTN_FILE, STYLE_PROGRESS,
    shadow, h_separator, section_label, dim_label, metric_chip,
)


# ── Workers ───────────────────────────────────────────────────────────────────
class ETLWorker(QThread):
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, raw_text: str, db):
        super().__init__()
        self.raw_text = raw_text
        self.db       = db

    def run(self):
        try:
            doc = ETLEngine.run(self.raw_text)
            self.db.collection.insert_one(doc)
            self.finished.emit(doc)
        except Exception as e:
            self.error.emit(str(e))


class BatchETLWorker(QThread):
    progress = Signal(int, int)   # procesados, total
    row_done = Signal(dict)
    finished = Signal(int, int)   # éxitos, errores

    def __init__(self, texts: list, db):
        super().__init__()
        self.texts = texts
        self.db    = db

    def run(self):
        success = errors = 0
        total   = len(self.texts)
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


# ── ResultCard ────────────────────────────────────────────────────────────────
class ResultCard(QFrame):
    def __init__(self, doc: dict):
        super().__init__()
        color = CAT_COLORS.get(doc.get("categoria", "Neutral"), TEXT_DIM)
        self.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER};"
            f" border-left: 4px solid {color}; border-radius: 10px; }}"
        )
        shadow(self, blur=20, offset_y=4, alpha=80)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # Fila 1: extracto + categoría
        top = QHBoxLayout()
        txt = doc.get("texto_original", doc.get("texto", ""))
        lbl_txt = QLabel(f'"{txt[:90]}{"…" if len(txt) > 90 else ""}"')
        lbl_txt.setStyleSheet(f"color:{TEXT_DIM}; font-style:italic; font-size:12px;")
        lbl_txt.setWordWrap(True)

        cat     = doc.get("categoria", "—")
        lbl_cat = QLabel(cat)
        lbl_cat.setStyleSheet(
            f"background-color:{color}22; color:{color}; border:1px solid {color};"
            f" border-radius:5px; padding:2px 10px; font-size:11px; font-weight:700;"
        )
        lbl_cat.setFixedHeight(24)
        lbl_cat.setAlignment(Qt.AlignCenter)
        top.addWidget(lbl_txt, 1)
        top.addWidget(lbl_cat)
        lay.addLayout(top)

        # Fila 2: métricas principales
        m    = doc.get("metricas", {})
        grid = QHBoxLayout()
        grid.setSpacing(12)
        grid.addWidget(metric_chip("Polaridad",    f'{doc.get("polaridad", 0):+.3f}', ACCENT))
        grid.addWidget(metric_chip("Subjetividad", f'{doc.get("subjetividad", 0):.3f}', ACCENT2))
        grid.addWidget(metric_chip("Intensidad",   doc.get("intensidad", "—"), WARNING))
        grid.addWidget(metric_chip("Palabras",     str(m.get("num_palabras", "—")), TEXT_DIM))
        grid.addWidget(metric_chip("Oraciones",    str(m.get("num_oraciones", "—")), TEXT_DIM))
        grid.addWidget(metric_chip("Dens. Léx.",   f'{m.get("densidad_lexica", 0):.2f}', TEXT_DIM))

        # Idioma + negación
        idioma = doc.get("idioma", "")
        if idioma:
            grid.addWidget(metric_chip("Idioma", idioma, ACCENT2))
        if doc.get("tiene_negacion"):
            grid.addWidget(metric_chip("Negación", "✓", WARNING))
        grid.addStretch()
        lay.addLayout(grid)

        # Fila 3: keywords
        kw = m.get("palabras_clave", [])
        if kw:
            kw_row = QHBoxLayout()
            kw_row.setSpacing(6)
            lbl_kw = QLabel("Keywords:")
            lbl_kw.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            kw_row.addWidget(lbl_kw)
            for w in kw[:6]:
                pill = QLabel(w)
                pill.setStyleSheet(
                    f"background-color:#1a3050; color:{ACCENT};"
                    f" border-radius:4px; padding:1px 7px; font-size:10px;"
                )
                kw_row.addWidget(pill)
            kw_row.addStretch()
            lay.addLayout(kw_row)


# ── AnalisisView ──────────────────────────────────────────────────────────────
class AnalisisView(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db           = db
        self.worker       = None
        self.batch_worker = None
        self._file_df     = None
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
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        # Encabezado
        h = QLabel("Pipeline ETL — Análisis de Texto")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        layout.addWidget(h)
        layout.addWidget(dim_label("Extract → Transform (NLP + features) → Load (MongoDB)"))
        layout.addWidget(h_separator())

        # ── Sección A: Entrada manual ─────────────────────────────────────────
        layout.addWidget(section_label("A  /  ENTRADA MANUAL"))
        layout.addWidget(dim_label("TEXTO DE ENTRADA", size=10))

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Ingresa el texto a procesar…")
        self.input_text.setStyleSheet(STYLE_INPUT)
        self.input_text.setMinimumHeight(44)
        self.input_text.returnPressed.connect(self.ejecutar_etl)
        layout.addWidget(self.input_text)

        row_a = QHBoxLayout()
        row_a.setSpacing(12)
        self.progress_manual = QProgressBar()
        self.progress_manual.setValue(0)
        self.progress_manual.setTextVisible(False)
        self.progress_manual.setFixedHeight(10)
        self.progress_manual.setStyleSheet(STYLE_PROGRESS)

        self.btn_run = QPushButton("▶  Ejecutar ETL")
        self.btn_run.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_run.setMinimumHeight(44)
        self.btn_run.setFixedWidth(180)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.ejecutar_etl)
        row_a.addWidget(self.progress_manual, 1)
        row_a.addWidget(self.btn_run)
        layout.addLayout(row_a)

        self.lbl_status_manual = QLabel("")
        self.lbl_status_manual.setStyleSheet(f"color:{ACCENT}; font-size:11px;")
        layout.addWidget(self.lbl_status_manual)
        layout.addWidget(h_separator())

        # ── Sección B: Carga masiva ───────────────────────────────────────────
        layout.addWidget(section_label("B  /  CARGA MASIVA DESDE ARCHIVO", ACCENT2))
        layout.addWidget(dim_label("Formatos soportados: CSV · Excel (.xlsx / .xls) · TSV"))

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self.btn_file = QPushButton("📂  Seleccionar archivo…")
        self.btn_file.setStyleSheet(STYLE_BTN_FILE)
        self.btn_file.setMinimumHeight(40)
        self.btn_file.setFixedWidth(220)
        self.btn_file.setCursor(Qt.PointingHandCursor)
        self.btn_file.clicked.connect(self._select_file)
        self.lbl_file = QLabel("Ningún archivo seleccionado")
        self.lbl_file.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        file_row.addWidget(self.btn_file)
        file_row.addWidget(self.lbl_file, 1)
        layout.addLayout(file_row)

        col_row = QHBoxLayout()
        col_row.setSpacing(10)
        lbl_col = QLabel("Columna de texto:")
        lbl_col.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        lbl_col.setFixedWidth(130)
        self.combo_col = QComboBox()
        self.combo_col.setStyleSheet(STYLE_COMBO)
        self.combo_col.setMinimumWidth(180)
        self.combo_col.setPlaceholderText("— cargue un archivo primero —")
        self.combo_col.setEnabled(False)
        self.btn_batch = QPushButton("⚡  Procesar Dataset")
        self.btn_batch.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_batch.setMinimumHeight(40)
        self.btn_batch.setFixedWidth(200)
        self.btn_batch.setCursor(Qt.PointingHandCursor)
        self.btn_batch.setEnabled(False)
        self.btn_batch.clicked.connect(self._ejecutar_batch)
        col_row.addWidget(lbl_col)
        col_row.addWidget(self.combo_col, 1)
        col_row.addWidget(self.btn_batch)
        layout.addLayout(col_row)

        self.progress_batch = QProgressBar()
        self.progress_batch.setValue(0)
        self.progress_batch.setTextVisible(True)
        self.progress_batch.setFormat("  %v / %m filas")
        self.progress_batch.setFixedHeight(20)
        self.progress_batch.setStyleSheet(
            STYLE_PROGRESS + f"QProgressBar {{ color:{TEXT_DIM}; font-size:10px; }}"
        )
        self.progress_batch.hide()
        self.lbl_status_batch = QLabel("")
        self.lbl_status_batch.setStyleSheet(f"color:{ACCENT2}; font-size:11px;")
        layout.addWidget(self.progress_batch)
        layout.addWidget(self.lbl_status_batch)
        layout.addWidget(h_separator())

        # ── Resultados ────────────────────────────────────────────────────────
        layout.addWidget(dim_label("RESULTADOS RECIENTES", size=10))
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
        QTimer.singleShot(300,  lambda: self._set_manual_status("🔄 [T] Transformando…", 50))
        QTimer.singleShot(700,  lambda: self._set_manual_status("💾 [L] Cargando en MongoDB…", 80))

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

    # ── Archivo ───────────────────────────────────────────────────────────────
    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar dataset", "",
            "Archivos de datos (*.csv *.tsv *.xlsx *.xls);;Todos (*.*)",
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
            QMessageBox.critical(self, "Error al leer archivo", str(e))
            return

        if df.empty:
            QMessageBox.warning(self, "Archivo vacío", "El archivo no contiene datos.")
            return

        self._file_df = df
        fname = path.split("/")[-1]
        self.lbl_file.setText(f"✔  {fname}  ({len(df)} filas, {len(df.columns)} cols)")
        self.lbl_file.setStyleSheet(f"color:{SUCCESS}; font-size:12px;")

        text_cols = [c for c in df.columns if df[c].dtype == object] or list(df.columns)
        self.combo_col.clear()
        self.combo_col.addItems(text_cols)
        self.combo_col.setEnabled(True)
        self.btn_batch.setEnabled(True)
        self.lbl_status_batch.setText("Archivo listo. Selecciona la columna y presiona Procesar.")
        self.lbl_status_batch.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")

    # ── Batch ─────────────────────────────────────────────────────────────────
    def _ejecutar_batch(self):
        if self._file_df is None:
            return
        col   = self.combo_col.currentText()
        texts = (
            self._file_df[col].dropna().astype(str).str.strip()
            .pipe(lambda s: s[s != ""])
            .tolist()
        )
        if not texts:
            QMessageBox.warning(self, "Sin datos", "La columna no tiene texto válido.")
            return

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

    def _add_card(self, doc: dict):
        card = ResultCard(doc)
        self.results_layout.insertWidget(0, card)