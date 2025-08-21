from __future__ import annotations

import sys
import os
from typing import Dict, List, Tuple, Any

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget,
    QLineEdit, QTableView, QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
    QScrollArea  # Added for scrollable bar chart
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression, QUrl
from PySide6.QtGui import QAction, QDesktopServices

# Use PySide6-compatible matplotlib backend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.cm as cm




# -----------------------------
# Efficient table model for large dicts
# -----------------------------
class DictTableModel(QAbstractTableModel):
    def __init__(self, data_dict: Dict[Any, Any], col1: str, col2: str, parent=None):
        super().__init__(parent)
        # Convert dict to a list of tuples once; keep keys as strings for filtering
        self._headers = [col1, col2]
        # Sorting by key (string) once keeps proxy sorting fast later
        self._rows: List[Tuple[str, Any]] = sorted(
            ((str(k), v) for k, v in data_dict.items()),
            key=lambda kv: kv[0].lower()
        )

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else 2

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        key, val = self._rows[index.row()]
        return key if index.column() == 0 else str(val)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return section + 1

    # Enable proxy sorting by returning comparable values
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        reverse = (order == Qt.DescendingOrder)
        if column == 0:
            self.layoutAboutToBeChanged.emit()
            self._rows.sort(key=lambda r: r[0].lower(), reverse=reverse)
            self.layoutChanged.emit()
        else:
            # Numeric sort if possible, else string
            def val_key(r):
                try:
                    return float(r[1])
                except Exception:
                    return str(r[1])
            self.layoutAboutToBeChanged.emit()
            self._rows.sort(key=val_key, reverse=reverse)
            self.layoutChanged.emit()

    # Optional: quick export
    def to_rows(self) -> List[Tuple[str, Any]]:
        return self._rows[:]


class ContainsFilterProxy(QSortFilterProxyModel):
    """Case-insensitive 'contains' filter on a single column."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(0)  # default to first column

    def setFilterString(self, text: str):
        # Escape user input, use a simple .*text.* contains pattern
        pattern = QRegularExpression.escape(text)
        regex = QRegularExpression(f".*{pattern}.*", QRegularExpression.CaseInsensitiveOption)
        self.setFilterRegularExpression(regex)


# -----------------------------
# Main viewer
# -----------------------------
class StatisticsViewer(QDialog):
    """
    A dialog to display detailed statistics using multiple tabs:
    - Summary overview
    - Tables (efficient, searchable)
    - Charts (bar/pie; defaults to top_n=50 for big data)
    """
    def __init__(self, stats: Dict[str, Any], parent=None, default_top_n: int = 50):
        super().__init__(parent)
        self.setWindowTitle("Detailed Statistics")
        self.resize(1000, 680)
        self._default_top_n = default_top_n

        # Basic dark palette via stylesheet (works cross-platform)
        self.setStyleSheet("""
            QWidget { background-color: #1f1f1f; color: #eaeaea; }
            QTabBar::tab { padding: 8px 14px; }
            QLineEdit {
                padding: 8px; font-size: 13px; color: #ffffff;
                background-color: #2a2a2a; border: 1px solid #444; border-radius: 6px;
            }
            QPushButton {
                padding: 6px 10px; background: #333; border: 1px solid #555; border-radius: 8px;
            }
            QPushButton::hover { background: #3c3c3c; }
            QHeaderView::section {
                background-color: #2b2b2b; color: #dddddd; padding: 6px; font-weight: 600; border: none;
            }
            QTableView {
                gridline-color: #3a3a3a; alternate-background-color: #242424; selection-background-color: #4b4b4b;
                font-size: 13px;
            }
        """)

        tabs = QTabWidget()

        # === Summary tab ===
        tabs.addTab(self._make_summary_tab(stats), "📊 Summary")

        # === Table tabs === (use model/view + proxy for speed)
        tabs.addTab(
            self._make_table_tab(stats.get('Tag usage count', {}), "Tag", "Count"),
            "🏷 Tag Usage"
        )
        tabs.addTab(
            self._make_table_tab(stats.get('Topics per publisher', {}), "Publisher", "Topics"),
            "🏢 Topics per Publisher"
        )
        tabs.addTab(
            self._make_table_tab(stats.get('Chapters per topic', {}), "Topic", "Chapters"),
            "📚 Chapters per Topic"
        )

        # === Chart tabs === (limit categories by default)
        tabs.addTab(
            self._make_chart_tab(stats.get('Tag usage count', {}), "Tag Usage Chart", kind="bar", top_n=self._default_top_n),
            "📊 Tag Chart"
        )
        tabs.addTab(
            self._make_chart_tab(stats.get('Topics per publisher', {}), "Topics per Publisher Chart", kind="bar", top_n=self._default_top_n),
            "🏢 Publisher Chart"
        )
        tabs.addTab(
            self._make_chart_tab(stats.get('Chapters per topic', {}), "Chapters per Topic Chart", kind="bar", top_n=self._default_top_n),
            "📚 Topic Chart"
        )
        tabs.addTab(
            self._make_chart_tab(stats.get('Tag usage count', {}), "Tag Usage Pie", kind="pie", top_n=self._default_top_n),
            "🥧 Tag Pie"
        )
        tabs.addTab(
            self._make_chart_tab(stats.get('Tag usage count', {}), f"Top {self._default_top_n} Tags", kind="bar", top_n=self._default_top_n),
            "📊 Top Tags"
        )

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

        # Optional: simple export action in context (for charts)
        self._add_context_export()

    # -----------------------------
    # Summary
    # -----------------------------
    def _make_summary_tab(self, stats: Dict[str, Any]) -> QWidget:
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)

        def safe_fmt(key, label=None):
            if key in stats and stats[key] is not None:
                return f"<b>{label or key}:</b> {stats[key]}<br>"
            return ""

        summary_text = (
            "<h2>📊 Overview</h2>"
            + safe_fmt('Total publishers')
            + safe_fmt('Total topics')
            + safe_fmt('Total chapters')
            + safe_fmt('Total unique tags')
            + safe_fmt('Average topics per publisher')
            + safe_fmt('Average chapters per topic')
        )

        if 'Most used tag' in stats and stats['Most used tag']:
            tag, count = stats['Most used tag']
            summary_text += f"<b>Most used tag:</b> {tag} ({count} uses)<br>"

        if 'Least used tags' in stats and stats['Least used tags']:
            least = stats['Least used tags']
            if isinstance(least, (list, tuple)):
                summary_text += f"<b>Least used tags:</b> {', '.join(map(str, least))}<br>"

        summary_label = QLabel(summary_text or "<i>No summary available.</i>")
        summary_label.setTextFormat(Qt.RichText)
        summary_label.setStyleSheet("font-size: 14px; margin: 10px;")
        summary_label.setWordWrap(True)

        summary_layout.addWidget(summary_label)
        summary_layout.addStretch()
        return summary_tab

    # -----------------------------
    # Table tabs (efficient)
    # -----------------------------
    def _make_table_tab(self, data_dict: Dict[Any, Any], col1_name: str, col2_name: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Search + actions row
        top_row = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText(f"🔍 Search {col1_name}...")
        top_row.addWidget(search, 1)

        export_btn = QPushButton("Export CSV")
        top_row.addWidget(export_btn, 0)
        layout.addLayout(top_row)

        # Model + Proxy + View
        model = DictTableModel(data_dict, col1_name, col2_name, parent=widget)
        proxy = ContainsFilterProxy(widget)
        proxy.setSourceModel(model)
        proxy.setFilterKeyColumn(0)

        table = QTableView()
        table.setModel(proxy)
        table.setSortingEnabled(True)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(table)

        # Connect search
        search.textChanged.connect(proxy.setFilterString)

        # Export handler
        def do_export():
            if model.rowCount() == 0:
                QMessageBox.information(widget, "Export CSV", "No data to export.")
                return
            path, _ = QFileDialog.getSaveFileName(widget, "Save CSV", f"{col1_name.lower()}_{col2_name.lower()}.csv", "CSV Files (*.csv)")
            if not path:
                return
            try:
                # Export only currently filtered rows from proxy
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"{col1_name},{col2_name}\n")
                    for r in range(proxy.rowCount()):
                        k = proxy.index(r, 0).data()
                        v = proxy.index(r, 1).data()
                        # Basic escaping of commas/quotes
                        k_esc = '"' + str(k).replace('"', '""') + '"'
                        v_esc = '"' + str(v).replace('"', '""') + '"'
                        f.write(f"{k_esc},{v_esc}\n")
                QMessageBox.information(widget, "Export CSV", f"Saved: {path}")
            except Exception as e:
                QMessageBox.critical(widget, "Export CSV", f"Failed to save CSV:\n{e}")

        export_btn.clicked.connect(do_export)

        return widget

    # -----------------------------
    # Charts
    # -----------------------------


    # -----------------------------
    # Charts
    # -----------------------------
    def _make_chart_tab(
        self, 
        data_dict: Dict[Any, Any], 
        title: str,
        kind: str = "bar", 
        top_n: int | None = None, 
        allow_scroll: bool = True
    ) -> QWidget:
        """
        Create a chart tab (bar, pie, line, scatter, stacked).
        - Bar charts: Scrollable if > top_n (except Top 50 tab).
        - Pie charts: Groups leftover as "Others", supports recursive drilldown.
        """

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Clean data ---
        items: List[Tuple[str, float]] = []
        for k, v in data_dict.items():
            try:
                items.append((str(k), float(v)))
            except Exception:
                continue

        # Sort descending
        items.sort(key=lambda x: x[1], reverse=True)

        # Handle leftover for PIE charts only
        leftover_items: List[Tuple[str, float]] = []
        if top_n and kind == "pie" and len(items) > top_n:
            leftover_items = items[top_n:]
            top_items = items[:top_n]
            other_sum = sum(v for _, v in leftover_items)
            top_items.append(("Others", other_sum))
            items = top_items

        keys = [k for k, _ in items]
        values = [v for _, v in items]

        # --- Matplotlib setup ---
        fig = Figure(figsize=(7, 5), dpi=100, facecolor="#1f1f1f")
        ax = fig.add_subplot(111)

        if not items:
            ax.text(0.5, 0.5, "No numeric data", color="#dddddd",
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            return widget

        def truncate(label: str, max_len: int = 24) -> str:
            return label if len(label) <= max_len else (label[:max_len - 1] + "…")

        def format_val(v: float) -> str:
            return f"{v:,.2f}" if abs(v) >= 1 else f"{v:.4f}"


        # =====================================================
        # VERTICAL BAR CHART (scrollable, fixed figure height)
        # =====================================================
        if kind == "bar":
            # Sort values descending
            items.sort(key=lambda x: x[1], reverse=True)
            keys = [k for k, _ in items]
            values = [v for _, v in items]

            # Fixed height figure, but width adjusts with tags
            fig = Figure(figsize=(12, 6), dpi=100, facecolor="#1f1f1f")
            ax = fig.add_subplot(111)

            x_pos = range(len(keys))
            bars = ax.bar(x_pos, values, color="#5aa9e6")

            # X-axis labels
            ax.set_xticks(x_pos)
            ax.set_xticklabels(
                [truncate(k, 20) for k in keys],
                rotation=45, ha='right', color="#dddddd", fontsize=8
            )

            ax.tick_params(axis='y', colors="#dddddd")
            for spine in ax.spines.values():
                spine.set_color("#444444")
            ax.set_facecolor("#1f1f1f")
            ax.set_title(title, color="#dddddd")

            fig.tight_layout(pad=2.0)
            canvas = FigureCanvas(fig)

            # --- Make it scrollable ---
            scroll = QScrollArea()
            scroll.setWidget(canvas)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            # Dynamically set canvas width so it doesn’t cram labels
            min_width = max(1200, len(keys) * 25)  # 25px per tag
            canvas.setMinimumWidth(min_width)
            canvas.setMinimumHeight(500)

            # Tooltip on hover
            annot = ax.annotate(
                "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                bbox=dict(boxstyle="round", fc=(0, 0, 0, 0.8), ec="#dddddd"),
                fontsize=9, color="#ffffff", ha='left'
            )
            annot.set_visible(False)

            def on_hover(event):
                if event.inaxes != ax:
                    if annot.get_visible():
                        annot.set_visible(False)
                        canvas.draw_idle()
                    return
                vis = False
                for bar, k, v in zip(bars, keys, values):
                    if bar.contains(event)[0]:
                        annot.xy = (event.x, event.y)
                        annot.set_text(f"{k}\n{v:g}")
                        annot.set_visible(True)
                        vis = True
                        break
                if not vis and annot.get_visible():
                    annot.set_visible(False)
                canvas.draw_idle()

            canvas.mpl_connect("motion_notify_event", on_hover)

            # Add toolbar + scrollable chart
            layout.addWidget(NavigationToolbar(canvas, self))
            layout.addWidget(scroll)





        # =====================================================
        # PIE CHART (with recursive "Others" drilldown)
        # =====================================================
        elif kind == "pie":
            colors = cm.tab20.colors
            wedges, _ = ax.pie(
                values,
                colors=colors[:len(values)],
                labels=None,
                autopct=None,
                normalize=True,
                textprops={'color': "w"}
            )

            ax.axis("equal")
            ax.set_position([0.02, 0.02, 0.96, 0.96])
            ax.set_title(title, color="#dddddd", fontsize=14, pad=10)

            canvas = FigureCanvas(fig)

            # Tooltip
            annot = ax.annotate(
                "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                bbox=dict(boxstyle="round", fc=(0, 0, 0, 0.8), ec="#dddddd"),
                fontsize=10, color="#ffffff", ha='center'
            )
            annot.set_visible(False)

            def on_hover(event):
                if event.inaxes != ax:
                    if annot.get_visible():
                        annot.set_visible(False)
                        canvas.draw_idle()
                    return
                vis = False
                for wedge, k, v in zip(wedges, keys, values):
                    if wedge.contains(event)[0]:
                        annot.xy = (event.xdata, event.ydata)
                        pct = (v / sum(values) * 100.0) if values else 0.0
                        annot.set_text(f"{k}\n{format_val(v)} ({pct:.1f}%)")
                        annot.set_visible(True)
                        vis = True
                        break
                if not vis and annot.get_visible():
                    annot.set_visible(False)
                canvas.draw_idle()

            def on_double_click(event):
                for wedge, k in zip(wedges, keys):
                    if wedge.contains(event)[0] and k == "Others" and leftover_items:
                        sub_data = dict(leftover_items)
                        sub_dialog = QDialog(self)
                        sub_dialog.setWindowTitle("Others Breakdown")
                        sub_layout = QVBoxLayout(sub_dialog)
                        sub_layout.addWidget(
                            self._make_chart_tab(sub_data, "Others Breakdown", kind="pie", top_n=top_n)
                        )
                        sub_dialog.resize(600, 500)
                        sub_dialog.exec()
                        break

            canvas.mpl_connect("motion_notify_event", on_hover)
            canvas.mpl_connect("button_press_event",
                               lambda ev: on_double_click(ev) if ev.dblclick else None)

            layout.addWidget(canvas)

        # =====================================================
        # OTHER CHART TYPES (line, scatter, stacked)
        # =====================================================
        elif kind == "line":
            ax.plot(range(len(keys)), values, marker="o",
                    color="#5aa9e6", linewidth=2)
            ax.set_xticks(range(len(keys)))
            ax.set_xticklabels([truncate(k) for k in keys],
                               rotation=45, ha='right', color="#dddddd", fontsize=9)
            ax.tick_params(axis='y', colors="#dddddd")
            ax.set_facecolor("#1f1f1f")
            ax.set_title(title, color="#dddddd")
            fig.tight_layout(pad=2.0)
            layout.addWidget(FigureCanvas(fig))

        elif kind == "scatter":
            ax.scatter(range(len(keys)), values, color="#f28482", s=50, alpha=0.8)
            ax.set_xticks(range(len(keys)))
            ax.set_xticklabels([truncate(k) for k in keys],
                               rotation=45, ha='right', color="#dddddd", fontsize=9)
            ax.tick_params(axis='y', colors="#dddddd")
            ax.set_facecolor("#1f1f1f")
            ax.set_title(title, color="#dddddd")
            fig.tight_layout(pad=2.0)
            layout.addWidget(FigureCanvas(fig))

        elif kind == "stacked":
            if isinstance(items[0][1], dict):  # stacked grouped data
                subkeys = list(items[0][1].keys())
                bottoms = [0] * len(keys)
                colors = cm.tab20.colors
                for i, sub in enumerate(subkeys):
                    vals = [v[sub] for _, v in items]
                    ax.bar(keys, vals, bottom=bottoms,
                           label=sub, color=colors[i % len(colors)])
                    bottoms = [b + v for b, v in zip(bottoms, vals)]
                ax.legend(facecolor="#1f1f1f", labelcolor="#dddddd")
            else:
                ax.bar(keys, values, color="#5aa9e6")

            ax.set_xticklabels([truncate(k) for k in keys],
                               rotation=45, ha='right', color="#dddddd", fontsize=9)
            ax.tick_params(axis='y', colors="#dddddd")
            ax.set_facecolor("#1f1f1f")
            ax.set_title(title, color="#dddddd")
            fig.tight_layout(pad=2.0)
            layout.addWidget(FigureCanvas(fig))

        return widget










    # -----------------------------
    # Optional context actions
    # -----------------------------
    def _add_context_export(self):
        # Minimal example: right-click to save current chart canvas as PNG
        act = QAction("Save Chart as PNG", self)
        act.triggered.connect(self._save_visible_chart)
        self.addAction(act)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

    def _save_visible_chart(self):
        # Finds the first FigureCanvas in the currently visible tab and saves it
        tabw: QTabWidget = self.findChild(QTabWidget)
        if not tabw:
            return
        current = tabw.currentWidget()
        if not current:
            return
        canvases = current.findChildren(FigureCanvas)
        if not canvases:
            QMessageBox.information(self, "Save Chart", "No chart on this tab.")
            return
        canvas = canvases[0]
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart as PNG", "chart.png", "PNG Image (*.png)")
        if not path:
            return
        try:
            canvas.figure.savefig(path, dpi=160, bbox_inches="tight")
            QMessageBox.information(self, "Save Chart", f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Chart", f"Failed to save chart:\n{e}")

    def _show_drilldown(self, data: Dict[str, float], title: str = "Others Breakdown"):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(640, 480)
        vb = QVBoxLayout(dlg)
        vb.addWidget(self._make_chart_tab(data, title, kind="pie"))
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        vb.addWidget(btns)
        dlg.exec()
            
# -----------------------------
# Optional demo runner
# -----------------------------
if __name__ == "__main__":
    demo_stats = {
        "Total publishers": 42,
        "Total topics": 1800,
        "Total chapters": 9500,
        "Total unique tags": 1250,
        "Average topics per publisher": 42.9,
        "Average chapters per topic": 5.27,
        "Most used tag": ("python", 1234),
        "Least used tags": ["obscure1", "obscure2"],
        "Tag usage count": {f"tag_{i}": (1000 - i % 100) for i in range(5000)},  # big
        "Topics per publisher": {f"publisher_{i}": (i % 200) + 1 for i in range(1000)},
        "Chapters per topic": {f"topic_{i}": (i % 30) + 1 for i in range(2000)},
    }

    app = QApplication(sys.argv)
    dlg = StatisticsViewer(demo_stats, default_top_n=50)
    dlg.show()
    sys.exit(app.exec())
