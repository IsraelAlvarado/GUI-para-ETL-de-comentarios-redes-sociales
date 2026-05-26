"""
extractor_view.py — Extractor de comentarios de redes sociales.
Plataformas con backend implementado:
  ✓ Twitter/X  — TWITTER_BEARER_TOKEN
  ✓ YouTube    — YT_API_KEY
  ✓ Reddit     — REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET
  ✗ Instagram  — Requiere aprobación Meta (no disponible)
  ✗ Facebook   — Requiere aprobación Meta (no disponible)
"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QComboBox, QSpinBox,
    QDateEdit, QCheckBox, QTextEdit,
)
from PySide6.QtCore import Qt, QDate, QThread, Signal

from src.social_extractors import (
    EXTRACTORS,
    PlatformNotConfiguredError,
    PlatformNotInstalledError,
    PlatformUnavailableError,
)
from .components import (
    BG_CARD, BG_PANEL, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
    BORDER, WARNING, SUCCESS, DANGER, MUTED,
    STYLE_INPUT, STYLE_COMBO, STYLE_BTN_PRIMARY, STYLE_BTN_GHOST,
    shadow, h_separator, section_label, dim_label,
)

# ── Estilos locales ────────────────────────────────────────────────────────────
_STYLE_SPINBOX = f"""
    QSpinBox, QDateEdit {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 6px;
        padding: 6px 10px; font-size: 12px; min-height: 32px;
    }}
    QSpinBox:focus, QDateEdit:focus {{ border-color: {ACCENT}; }}
"""
_STYLE_TEXTAREA = f"""
    QTextEdit {{
        background-color: #0a1520; color: {TEXT_MAIN};
        border: 1px solid {BORDER}; border-radius: 8px;
        padding: 10px; font-size: 11px; font-family: monospace;
    }}
"""
_STYLE_BADGE_OK   = (
    f"background:#0d2a1f; color:{SUCCESS}; border:1px solid {SUCCESS}44;"
    f" border-radius:4px; padding:2px 8px; font-size:10px; font-weight:700;"
)
_STYLE_BADGE_WARN = (
    f"background:#2a200d; color:{WARNING}; border:1px solid {WARNING}44;"
    f" border-radius:4px; padding:2px 8px; font-size:10px; font-weight:700;"
)
_STYLE_BADGE_ERR  = (
    f"background:#2a0d0d; color:{DANGER}; border:1px solid {DANGER}44;"
    f" border-radius:4px; padding:2px 8px; font-size:10px; font-weight:700;"
)

# ── Worker de extracción ───────────────────────────────────────────────────────
class ExtractionWorker(QThread):
    log_msg  = Signal(str)          # mensaje para el log
    finished = Signal(int, int)     # (textos_extraídos, insertados_en_mongo)

    def __init__(self, extractor_cls, query, limit, send_to_etl, db):
        super().__init__()
        self.extractor_cls = extractor_cls
        self.query         = query
        self.limit         = limit
        self.send_to_etl   = send_to_etl
        self.db            = db
        self._running      = True

    def stop(self):
        self._running = False

    def run(self):
        extracted = inserted = 0
        try:
            texts = self.extractor_cls.extract(
                self.query,
                self.limit,
                progress_cb=lambda m: self.log_msg.emit(m),
            )
            extracted = len(texts)
            self.log_msg.emit(
                f"\n{'─'*50}\n✅  {extracted} texto(s) extraído(s).\n{'─'*50}"
            )

            if self.send_to_etl and texts:
                self.log_msg.emit("🔄  Enviando al pipeline ETL…")
                from src.etl_engine import ETLEngine
                for i, text in enumerate(texts, 1):
                    if not self._running:
                        self.log_msg.emit("⏹  Detenido por el usuario.")
                        break
                    try:
                        doc = ETLEngine.run(
                            text,
                            source=self.extractor_cls.NAME,
                        )
                        self.db.collection.insert_one(doc)
                        inserted += 1
                        self.log_msg.emit(
                            f"  [ETL {i}/{extracted}]  cat={doc['categoria']}  "
                            f"pol={doc['polaridad']:+.3f}  → MongoDB ✓"
                        )
                    except Exception as e:
                        self.log_msg.emit(f"  [ETL Error #{i}] {e}")

                self.log_msg.emit(
                    f"\n✅  {inserted}/{extracted} documentos insertados en MongoDB."
                )

        except (PlatformNotConfiguredError, PlatformNotInstalledError,
                PlatformUnavailableError) as e:
            self.log_msg.emit(f"❌  {e}")
        except Exception as e:
            self.log_msg.emit(f"❌  Error inesperado: {e}")

        self.finished.emit(extracted, inserted)


# ── Vista principal ────────────────────────────────────────────────────────────
class ExtractorView(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db      = db
        self._worker = None
        self._current_platform = "Twitter / X"
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner  = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 24)

        # Encabezado
        h = QLabel("📡  Extractor de Redes Sociales")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        layout.addWidget(h)
        layout.addWidget(
            dim_label("Extrae comentarios y textos directamente al pipeline ETL.")
        )
        layout.addWidget(h_separator())

        # ── A: Selector de plataforma ─────────────────────────────────────────
        layout.addWidget(section_label("PLATAFORMA"))
        layout.addWidget(self._build_platform_selector())
        layout.addWidget(h_separator())

        # ── B: Estado de credenciales ─────────────────────────────────────────
        layout.addWidget(section_label("CREDENCIALES"))
        self._cred_card = self._build_credentials_card()
        layout.addWidget(self._cred_card)
        layout.addWidget(h_separator())

        # ── C: Parámetros ─────────────────────────────────────────────────────
        layout.addWidget(section_label("PARÁMETROS"))
        layout.addWidget(self._build_params_card())
        layout.addWidget(h_separator())

        # ── D: Extracción + log ───────────────────────────────────────────────
        layout.addWidget(section_label("EXTRACCIÓN"))
        layout.addWidget(self._build_action_card())

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # Seleccionar primera plataforma
        self._select_platform("Twitter / X")

    # ── Selector de plataforma ────────────────────────────────────────────────
    def _build_platform_selector(self) -> QWidget:
        w   = QWidget()
        row = QHBoxLayout(w)
        row.setSpacing(8)
        row.setContentsMargins(0, 0, 0, 0)

        self._platform_btns: dict[str, QPushButton] = {}
        icons = {
            "Twitter / X": "🐦",
            "YouTube":     "▶",
            "Reddit":      "🔴",
            "Instagram":   "📷",
            "Facebook":    "📘",
        }

        for name, ext_cls in EXTRACTORS.items():
            btn = QPushButton(f"{icons.get(name, '●')}  {name}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(42)
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda _, n=name: self._select_platform(n))
            self._platform_btns[name] = btn
            row.addWidget(btn)

        row.addStretch()
        return w

    def _select_platform(self, name: str):
        self._current_platform = name
        for n, btn in self._platform_btns.items():
            btn.setChecked(n == name)
            btn.setStyleSheet(self._btn_style(n == name))

        ext_cls = EXTRACTORS[name]

        # Actualizar placeholder de input
        placeholders = {
            "Twitter / X": "@usuario  o  #hashtag  o  keyword",
            "YouTube":     "URL del video o ID (ej: dQw4w9WgXcQ)",
            "Reddit":      "r/subreddit  o  URL del hilo",
            "Instagram":   "No disponible",
            "Facebook":    "No disponible",
        }
        self.input_target.setPlaceholderText(placeholders.get(name, ""))
        self.input_target.setEnabled(ext_cls.is_installed() and ext_cls.is_configured())

        # Actualizar tarjeta de credenciales
        self._refresh_credentials_card(name)

        # Actualizar botón de inicio
        ready = ext_cls.is_installed() and ext_cls.is_configured()
        self.btn_extract.setEnabled(ready)
        if ready:
            self._set_badge(self.lbl_status, "✓  Listo para extraer", "ok")
        elif not ext_cls.is_installed() and ext_cls.INSTALL:
            self._set_badge(
                self.lbl_status,
                f"✗  Instala: {ext_cls.INSTALL}",
                "err",
            )
        elif not ext_cls.is_configured() and ext_cls.ENV_VARS:
            self._set_badge(
                self.lbl_status,
                "⚠  Faltan credenciales en .env",
                "warn",
            )
        else:
            self._set_badge(self.lbl_status, "✗  No disponible", "err")

    # ── Tarjeta de credenciales ───────────────────────────────────────────────
    def _build_credentials_card(self) -> QFrame:
        card = self._card()
        card.setObjectName("cred_card")
        self._cred_layout = QVBoxLayout(card)
        self._cred_layout.setContentsMargins(20, 14, 20, 14)
        self._cred_layout.setSpacing(8)
        return card

    def _refresh_credentials_card(self, platform: str):
        # Limpiar contenido anterior
        while self._cred_layout.count():
            item = self._cred_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ext_cls = EXTRACTORS[platform]

        # Plataformas sin soporte
        if not ext_cls.INSTALL and not ext_cls.ENV_VARS:
            lbl = QLabel(
                "⚠  Esta plataforma requiere aprobación especial de Meta y "
                "no está disponible en esta versión."
            )
            lbl.setStyleSheet(f"color:{WARNING}; font-size:12px;")
            lbl.setWordWrap(True)
            self._cred_layout.addWidget(lbl)
            return

        # Estado del paquete
        pkg_row = QHBoxLayout()
        pkg_lbl = QLabel(f"Paquete Python  ({ext_cls.INSTALL or 'N/A'}):")
        pkg_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
        pkg_lbl.setFixedWidth(280)
        pkg_status = QLabel()
        if ext_cls.is_installed():
            pkg_status.setText("✓  Instalado")
            pkg_status.setStyleSheet(f"color:{SUCCESS}; font-size:11px; font-weight:700;")
        else:
            pkg_status.setText(f"✗  No instalado  →  {ext_cls.INSTALL}")
            pkg_status.setStyleSheet(f"color:{DANGER}; font-size:11px; font-weight:700;")
        pkg_row.addWidget(pkg_lbl)
        pkg_row.addWidget(pkg_status)
        pkg_row.addStretch()
        self._cred_layout.addLayout(pkg_row)

        # Estado de cada variable de entorno
        for env_key in ext_cls.ENV_VARS:
            row = QHBoxLayout()
            key_lbl = QLabel(f"{env_key}:")
            key_lbl.setStyleSheet(
                f"color:{TEXT_DIM}; font-size:11px; font-family:monospace;"
            )
            key_lbl.setFixedWidth(280)
            val_lbl = QLabel()
            if os.getenv(env_key):
                val_lbl.setText("●  Configurado")
                val_lbl.setStyleSheet(f"color:{SUCCESS}; font-size:11px; font-weight:700;")
            else:
                val_lbl.setText("○  No configurado  →  agrega al .env")
                val_lbl.setStyleSheet(f"color:{DANGER}; font-size:11px; font-weight:700;")
            row.addWidget(key_lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            self._cred_layout.addLayout(row)

    # ── Parámetros ────────────────────────────────────────────────────────────
    def _build_params_card(self) -> QFrame:
        card = self._card()
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        lay.addWidget(dim_label("URL / USUARIO / HASHTAG / SUBREDDIT", size=10))
        self.input_target = QLineEdit()
        self.input_target.setStyleSheet(STYLE_INPUT)
        self.input_target.setMinimumHeight(42)
        lay.addWidget(self.input_target)

        # Fila de opciones
        row_opts = QHBoxLayout()
        row_opts.setSpacing(16)

        col1 = QVBoxLayout()
        col1.addWidget(dim_label("Máx. textos", size=11))
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 1000)
        self.spin_limit.setValue(50)
        self.spin_limit.setSingleStep(25)
        self.spin_limit.setStyleSheet(_STYLE_SPINBOX)
        col1.addWidget(self.spin_limit)

        col2 = QVBoxLayout()
        col2.addWidget(dim_label("Idioma", size=11))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Todos", "Español", "English", "Português"])
        self.combo_lang.setStyleSheet(STYLE_COMBO)
        col2.addWidget(self.combo_lang)

        row_opts.addLayout(col1)
        row_opts.addLayout(col2)
        row_opts.addStretch()
        lay.addLayout(row_opts)

        # Opciones adicionales
        opts = QHBoxLayout()
        self.chk_etl = QCheckBox("Enviar automáticamente al pipeline ETL  (→ MongoDB)")
        self.chk_etl.setChecked(True)
        self.chk_etl.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        opts.addWidget(self.chk_etl)
        opts.addStretch()
        lay.addLayout(opts)
        return card

    # ── Zona de acción ────────────────────────────────────────────────────────
    def _build_action_card(self) -> QFrame:
        card = self._card()
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        action_row = QHBoxLayout()

        self.btn_extract = QPushButton("🚀  Iniciar Extracción")
        self.btn_extract.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_extract.setMinimumHeight(44)
        self.btn_extract.setFixedWidth(220)
        self.btn_extract.setCursor(Qt.PointingHandCursor)
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self._start_extraction)

        self.btn_stop = QPushButton("⏹  Detener")
        self.btn_stop.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{DANGER};"
            f" border:1px solid {DANGER}; border-radius:8px; padding:10px 20px;"
            f" font-size:13px; font-weight:700; }}"
            f"QPushButton:hover {{ background:{DANGER}; color:white; }}"
            f"QPushButton:disabled {{ color:{MUTED}; border-color:{MUTED}; }}"
        )
        self.btn_stop.setMinimumHeight(44)
        self.btn_stop.setFixedWidth(140)
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_extraction)

        self.lbl_status = QLabel("⚠  Selecciona una plataforma")
        self.lbl_status.setStyleSheet(_STYLE_BADGE_WARN)

        action_row.addWidget(self.btn_extract)
        action_row.addWidget(self.btn_stop)
        action_row.addWidget(self.lbl_status)
        action_row.addStretch()
        lay.addLayout(action_row)

        # Log
        lay.addWidget(dim_label("LOG DE EXTRACCIÓN", size=10))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(_STYLE_TEXTAREA)
        self.log_area.setMinimumHeight(180)
        self.log_area.setPlaceholderText(
            "El log de extracción aparecerá aquí…\n\n"
            "Requisitos por plataforma:\n"
            "  Twitter / X  →  TWITTER_BEARER_TOKEN  (Twitter Developer Portal)\n"
            "  YouTube      →  YT_API_KEY            (Google Cloud Console)\n"
            "  Reddit       →  REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET  "
            "(reddit.com/prefs/apps)\n\n"
            "Agrega las variables al archivo .env y reinicia la aplicación."
        )

        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()

        btn_copy = QPushButton("📋  Copiar log")
        btn_copy.setStyleSheet(STYLE_BTN_GHOST)
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setMinimumHeight(30)
        btn_copy.clicked.connect(self._copy_log)

        btn_clear = QPushButton("🗑  Limpiar")
        btn_clear.setStyleSheet(STYLE_BTN_GHOST)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setMinimumHeight(30)
        btn_clear.clicked.connect(self.log_area.clear)

        log_toolbar.addWidget(btn_copy)
        log_toolbar.addWidget(btn_clear)

        lay.addWidget(self.log_area)
        lay.addLayout(log_toolbar)
        return card

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _start_extraction(self):
        query = self.input_target.text().strip()
        if not query:
            self._log("⚠  Ingresa una URL, usuario o keyword antes de extraer.")
            return

        ext_cls = EXTRACTORS[self._current_platform]
        limit   = self.spin_limit.value()

        self.log_area.clear()
        self._log(
            f"{'─'*50}\n"
            f"  Plataforma : {self._current_platform}\n"
            f"  Query      : {query}\n"
            f"  Límite     : {limit} textos\n"
            f"  Pipeline   : {'SÍ → MongoDB' if self.chk_etl.isChecked() else 'NO (solo extraer)'}\n"
            f"{'─'*50}"
        )

        self._worker = ExtractionWorker(
            extractor_cls = ext_cls,
            query         = query,
            limit         = limit,
            send_to_etl   = self.chk_etl.isChecked(),
            db            = self.db,
        )
        self._worker.log_msg.connect(self._log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self.btn_extract.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._set_badge(self.lbl_status, "⏳  Extrayendo…", "warn")

    def _stop_extraction(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._log("⏹  Detención solicitada…")
        self.btn_stop.setEnabled(False)

    def _on_finished(self, extracted: int, inserted: int):
        self.btn_extract.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if inserted > 0:
            self._set_badge(
                self.lbl_status,
                f"✓  {inserted} doc(s) en MongoDB",
                "ok",
            )
        elif extracted > 0:
            self._set_badge(
                self.lbl_status,
                f"✓  {extracted} texto(s) extraído(s)",
                "ok",
            )
        else:
            self._set_badge(self.lbl_status, "⚠  Sin resultados", "warn")

    def _log(self, msg: str):
        self.log_area.append(msg)
        # Scroll automático al final
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_log(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_area.toPlainText())

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _set_badge(label: QLabel, text: str, kind: str):
        styles = {"ok": _STYLE_BADGE_OK, "warn": _STYLE_BADGE_WARN, "err": _STYLE_BADGE_ERR}
        label.setText(text)
        label.setStyleSheet(styles.get(kind, _STYLE_BADGE_WARN))

    @staticmethod
    def _btn_style(active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background:#0d2a3a; color:{ACCENT};"
                f" border:1.5px solid {ACCENT}; border-radius:8px;"
                f" padding:8px 14px; font-size:12px; font-weight:700; }}"
            )
        return (
            f"QPushButton {{ background:#0d1e2e; color:{TEXT_DIM};"
            f" border:1px solid {BORDER}; border-radius:8px;"
            f" padding:8px 14px; font-size:12px; }}"
            f"QPushButton:hover {{ background:#1a2e42; color:{TEXT_MAIN}; }}"
        )

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{BG_CARD}; border:1px solid {BORDER};"
            f" border-radius:10px; }}"
        )
        shadow(card, blur=16, offset_y=3, alpha=60)
        return card