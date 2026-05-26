"""
dashboard_view.py — Dashboard principal.
  FIXES:
  - btn_refresh.clicked pasa un bool → wrapped con lambda para load_data()
  - load_data(query="") acepta solo str
"""
import csv
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QLineEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from .components import (
    BG_PANEL, BG_CARD, TEXT_MAIN, TEXT_DIM, ACCENT, ACCENT2,
    BORDER, DANGER, SUCCESS,
    CAT_COLORS,
    STYLE_BTN_GHOST, STYLE_BTN_DANGER, STYLE_TABLE,
    shadow, h_separator, StatCard, ChartCanvas,
)

_STYLE_SEARCH = f"""
    QLineEdit {{
        background-color: #0d1e2e; color: {TEXT_MAIN};
        border: 1.5px solid {BORDER}; border-radius: 8px;
        padding: 8px 14px; font-size: 12px;
    }}
    QLineEdit:focus {{ border: 1.5px solid {ACCENT}; }}
"""


class DashboardView(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db         = db
        self.df         = pd.DataFrame()
        self._raw_docs  = []
        self._build()
        self.load_data()

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Encabezado + refresh
        header_row = QHBoxLayout()
        hd  = QVBoxLayout()
        h   = QLabel("Dashboard — Datos MongoDB")
        h.setStyleSheet(f"color:{TEXT_MAIN}; font-size:20px; font-weight:700;")
        sub = QLabel("Hasta 200 registros  •  Pandas + Matplotlib")
        sub.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px;")
        hd.addWidget(h)
        hd.addWidget(sub)
        header_row.addLayout(hd, 1)

        btn_refresh = QPushButton("⟳  Actualizar")
        btn_refresh.setStyleSheet(STYLE_BTN_GHOST)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        # ── FIX: clicked emite bool(checked); usar lambda para ignorarlo ──────
        btn_refresh.clicked.connect(lambda: self.load_data())
        header_row.addWidget(btn_refresh)
        layout.addLayout(header_row)
        layout.addWidget(h_separator())

        # KPI chips
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self.chip_total = StatCard("Total registros")
        self.chip_pol   = StatCard("Polaridad media",    color=ACCENT)
        self.chip_sub   = StatCard("Subjetividad media", color=ACCENT2)
        self.chip_pos   = StatCard("% Positivos",        color=SUCCESS)
        for c in (self.chip_total, self.chip_pol, self.chip_sub, self.chip_pos):
            kpi_row.addWidget(c)
        kpi_row.addStretch()
        layout.addLayout(kpi_row)

        # Splitter: gráficos arriba, tabla abajo
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background: #1e3448; height: 4px; }")

        charts_w = QWidget()
        charts_w.setStyleSheet(f"background-color: {BG_PANEL};")
        ch_lay = QHBoxLayout(charts_w)
        ch_lay.setContentsMargins(0, 8, 0, 8)
        ch_lay.setSpacing(12)
        self.chart_dist = ChartCanvas(height=3)
        self.chart_cat  = ChartCanvas(height=3)
        ch_lay.addWidget(self.chart_dist)
        ch_lay.addWidget(self.chart_cat)

        table_w = QWidget()
        table_w.setStyleSheet(f"background-color: {BG_PANEL};")
        t_lay = QVBoxLayout(table_w)
        t_lay.setContentsMargins(0, 4, 0, 0)
        t_lay.setSpacing(8)
        t_lay.addLayout(self._build_table_toolbar())
        t_lay.addWidget(self._build_table())

        splitter.addWidget(charts_w)
        splitter.addWidget(table_w)
        splitter.setSizes([240, 380])
        layout.addWidget(splitter, 1)

        self.lbl_empty = QLabel(
            "Sin datos en la base de datos.\n"
            "Ejecuta el pipeline ETL para poblar la colección."
        )
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet(f"color:{TEXT_DIM}; font-size:13px;")
        self.lbl_empty.hide()
        layout.addWidget(self.lbl_empty)

    def _build_table_toolbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Buscar en tabla…")
        self.search_bar.setStyleSheet(_STYLE_SEARCH)
        self.search_bar.setMinimumHeight(36)
        self.search_bar.textChanged.connect(self._filter_table)

        self.lbl_selection = QLabel("0 seleccionados")
        self.lbl_selection.setStyleSheet(
            f"color:{TEXT_DIM}; font-size:11px; min-width:110px;"
        )

        self.btn_select_all = QPushButton("☑  Seleccionar todo")
        self.btn_select_all.setStyleSheet(STYLE_BTN_GHOST)
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setMinimumHeight(34)
        self.btn_select_all.clicked.connect(self._toggle_select_all)

        self.btn_delete_sel = QPushButton("🗑  Eliminar selección")
        self.btn_delete_sel.setStyleSheet(STYLE_BTN_DANGER)
        self.btn_delete_sel.setCursor(Qt.PointingHandCursor)
        self.btn_delete_sel.setMinimumHeight(34)
        self.btn_delete_sel.setEnabled(False)
        self.btn_delete_sel.clicked.connect(self._delete_selected)

        self.btn_delete_all = QPushButton("⚠  Eliminar todo")
        self.btn_delete_all.setStyleSheet(STYLE_BTN_DANGER)
        self.btn_delete_all.setCursor(Qt.PointingHandCursor)
        self.btn_delete_all.setMinimumHeight(34)
        self.btn_delete_all.clicked.connect(self._delete_all)

        self.btn_export = QPushButton("⬇  Exportar CSV")
        self.btn_export.setStyleSheet(STYLE_BTN_GHOST)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setMinimumHeight(34)
        self.btn_export.clicked.connect(self._export_csv)

        row.addWidget(self.search_bar, 1)
        row.addWidget(self.lbl_selection)
        row.addWidget(self.btn_select_all)
        row.addWidget(self.btn_delete_sel)
        row.addWidget(self.btn_delete_all)
        row.addWidget(self.btn_export)
        return row

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget()
        self.table.setStyleSheet(STYLE_TABLE)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        return self.table

    # ── Data ──────────────────────────────────────────────────────────────────
    def load_data(self, query: str = ""):
        """Carga datos desde MongoDB. query debe ser str, no bool."""
        # Guardia: si por algún signal llega un bool, ignorar
        if not isinstance(query, str):
            query = ""
        try:
            raw = self.db.search(query) if query.strip() else self.db.get_all()
        except Exception as e:
            QMessageBox.critical(self, "Error MongoDB", str(e))
            return

        self._raw_docs = raw
        self.search_bar.clear()

        if not raw:
            self.lbl_empty.show()
            self.table.hide()
            self._clear_charts()
            self._update_kpis(pd.DataFrame())
            return

        self.lbl_empty.hide()
        self.table.show()

        df = pd.DataFrame(raw)
        df["fecha"]        = pd.to_datetime(df.get("fecha"),        errors="coerce")
        df["polaridad"]    = pd.to_numeric(df.get("polaridad"),     errors="coerce").fillna(0)
        df["subjetividad"] = pd.to_numeric(df.get("subjetividad"),  errors="coerce").fillna(0)
        df["texto"]        = df["texto"].astype(str).str[:80]  if "texto"      in df.columns else ""
        df["categoria"]    = df["categoria"].fillna("—")        if "categoria"  in df.columns else "—"
        df["intensidad"]   = df["intensidad"].fillna("—")       if "intensidad" in df.columns else "—"
        df["idioma"]       = df["idioma"].fillna("—")           if "idioma"     in df.columns else "—"
        self.df = df

        self._update_kpis(df)
        self._populate_table(df, raw)
        self._draw_histogram(df)
        self._draw_categories(df)

    def _populate_table(self, df: pd.DataFrame, raw: list):
        COLS   = ["texto", "polaridad", "subjetividad", "categoria",
                  "intensidad", "idioma", "fecha"]
        LABELS = ["Texto", "Polaridad", "Subjetividad", "Categoría",
                  "Intensidad", "Idioma", "Fecha"]
        present = [(c, l) for c, l in zip(COLS, LABELS) if c in df.columns]
        if not present:
            return
        cols_used, labels_used = zip(*present)

        self.table.setColumnCount(len(cols_used))
        self.table.setRowCount(len(df))
        self.table.setHorizontalHeaderLabels(list(labels_used))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        for row_i, (df_row, doc) in enumerate(zip(df.itertuples(), raw)):
            for col_j, col_name in enumerate(cols_used):
                val  = getattr(df_row, col_name, "")
                text = val.strftime("%Y-%m-%d %H:%M") if hasattr(val, "strftime") else str(val)

                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                if col_j == 0:
                    item.setData(Qt.UserRole, str(doc.get("_id", "")))

                if col_name == "polaridad":
                    try:
                        v = float(val)
                        item.setForeground(
                            QColor("#00d4aa") if v >  0.05 else
                            QColor("#ff5f6d") if v < -0.05 else
                            QColor(TEXT_DIM)
                        )
                    except Exception:
                        pass

                self.table.setItem(row_i, col_j, item)

    # ── Filtrado local ────────────────────────────────────────────────────────
    def _filter_table(self, text: str):
        q = text.lower()
        for row in range(self.table.rowCount()):
            visible = any(
                self.table.item(row, col) and
                q in self.table.item(row, col).text().lower()
                for col in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not visible)
        self._on_selection_changed()

    # ── Selección ─────────────────────────────────────────────────────────────
    def _on_selection_changed(self):
        n = len({idx.row() for idx in self.table.selectedIndexes()})
        self.lbl_selection.setText(f"{n} seleccionado{'s' if n != 1 else ''}")
        self.btn_delete_sel.setEnabled(n > 0)

    def _toggle_select_all(self):
        visible = [r for r in range(self.table.rowCount())
                   if not self.table.isRowHidden(r)]
        selected = {idx.row() for idx in self.table.selectedIndexes()}
        if set(visible) == selected:
            self.table.clearSelection()
        else:
            for r in visible:
                self.table.selectRow(r)

    # ── Eliminar seleccionados ────────────────────────────────────────────────
    def _delete_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        ids  = [
            self.table.item(r, 0).data(Qt.UserRole)
            for r in rows
            if self.table.item(r, 0) and self.table.item(r, 0).data(Qt.UserRole)
        ]
        if not ids:
            return
        if QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Eliminar {len(ids)} registro(s)?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            deleted = self.db.delete_by_ids(ids)
            QMessageBox.information(self, "Eliminados", f"{deleted} registro(s) eliminado(s).")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Eliminar todo ─────────────────────────────────────────────────────────
    def _delete_all(self):
        if self.table.rowCount() == 0:
            return
        if QMessageBox.question(
            self, "⚠  Eliminar TODA la colección",
            f"Se eliminarán TODOS los registros.\n¿Estás seguro?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        if QMessageBox.warning(
            self, "Confirmación final",
            "Última oportunidad: ¿Eliminar TODOS los registros?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            deleted = self.db.delete_all()
            QMessageBox.information(
                self, "Colección vaciada", f"{deleted} registro(s) eliminado(s)."
            )
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ── Exportar CSV ──────────────────────────────────────────────────────────
    def _export_csv(self):
        if self.df.empty:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar CSV", "sentiment_export.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            export_cols = [
                c for c in ["texto", "polaridad", "subjetividad",
                             "categoria", "intensidad", "idioma", "fecha"]
                if c in self.df.columns
            ]
            self.df[export_cols].to_csv(path, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    def _update_kpis(self, df: pd.DataFrame):
        if df.empty:
            for c in (self.chip_total, self.chip_pol, self.chip_sub, self.chip_pos):
                c.update("—")
            return
        self.chip_total.update(str(len(df)))
        self.chip_pol.update(f'{df["polaridad"].mean():+.3f}')
        self.chip_sub.update(f'{df["subjetividad"].mean():.3f}')
        pct = (df["polaridad"] > 0.05).mean() * 100
        self.chip_pos.update(f"{pct:.1f}%")

    # ── Gráficos ──────────────────────────────────────────────────────────────
    def _draw_histogram(self, df: pd.DataFrame):
        self.chart_dist.clear()
        ax = self.chart_dist.ax()
        ax.hist(df["polaridad"].dropna(), bins=20,
                color=ACCENT, alpha=0.8, edgecolor="#0d1e2e")
        ax.axvline(0, color=TEXT_DIM, linewidth=1, linestyle="--", alpha=0.6)
        ax.set_title("Distribución de Polaridad", color=TEXT_MAIN, fontsize=10, pad=8)
        ax.set_xlabel("Polaridad",  color=TEXT_DIM, fontsize=8)
        ax.set_ylabel("Frecuencia", color=TEXT_DIM, fontsize=8)
        self.chart_dist.draw()

    def _draw_categories(self, df: pd.DataFrame):
        self.chart_cat.clear()
        ax = self.chart_cat.ax()
        if "categoria" not in df.columns:
            self.chart_cat.draw()
            return
        counts = df["categoria"].value_counts()
        colors = [CAT_COLORS.get(c, TEXT_DIM) for c in counts.index]
        bars   = ax.barh(counts.index.tolist(), counts.values,
                         color=colors, height=0.6)
        ax.set_title("Registros por Categoría", color=TEXT_MAIN, fontsize=10, pad=8)
        ax.set_xlabel("Cantidad", color=TEXT_DIM, fontsize=8)
        for bar, val in zip(bars, counts.values):
            ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", color=TEXT_MAIN, fontsize=8)
        self.chart_cat.draw()

    def _clear_charts(self):
        for c in (self.chart_dist, self.chart_cat):
            c.clear()
            c.draw()