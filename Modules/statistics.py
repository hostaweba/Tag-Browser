# Modules/statistics.py
from __future__ import annotations

import sys
import csv
import json
from typing import Dict, List, Tuple, Any

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QWidget, QStackedWidget,
    QLineEdit, QTableView, QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QComboBox, QSpinBox, QGridLayout, QSplitter,
    QListWidget, QListWidgetItem, QColorDialog
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QRegularExpression, Signal
from PySide6.QtGui import QAction, QColor, QPalette, QFont

# Matplotlib setup
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.cm as cm
import numpy as np


# ==========================================
# 1. Core Data Models
# ==========================================
class DictTableModel(QAbstractTableModel):
    def __init__(self, data_dict: Dict[Any, Any], col1: str, col2: str, parent=None):
        super().__init__(parent)
        self._headers = [col1, col2]
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

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        reverse = (order == Qt.DescendingOrder)
        self.layoutAboutToBeChanged.emit()
        if column == 0:
            self._rows.sort(key=lambda r: r[0].lower(), reverse=reverse)
        else:
            def val_key(r):
                try: return float(r[1])
                except ValueError: return str(r[1])
            self._rows.sort(key=val_key, reverse=reverse)
        self.layoutChanged.emit()

class ContainsFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(0) 

    def setFilterString(self, text: str):
        pattern = QRegularExpression.escape(text)
        regex = QRegularExpression(f".*{pattern}.*", QRegularExpression.CaseInsensitiveOption)
        self.setFilterRegularExpression(regex)


# ==========================================
# 2. Advanced Interactive Chart Widget
# ==========================================
class AdvancedChartWidget(QWidget):
    def __init__(self, data_dict: Dict[Any, Any], title: str, default_top_n: int = 50, parent=None):
        super().__init__(parent)
        self.data_dict = data_dict
        self.chart_title = title
        self.app_theme = parent.app_theme if hasattr(parent, 'app_theme') else {"bg": "#1e1e1e", "fg": "#ffffff", "accent": "#007ACC"}
        
        self.annot = None
        self._hover_cid = None 
        self._click_cid = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- Control Panel ---
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("ChartControlFrame")
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(15, 10, 15, 10)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Filter items...")
        self.search_edit.setFixedWidth(180)
        self.search_edit.textChanged.connect(self.draw_chart)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["Bar", "Pie", "Line", "Area", "Scatter", "Histogram"])
        self.type_cb.currentTextChanged.connect(self.draw_chart)
        
        self.sort_cb = QComboBox()
        self.sort_cb.addItems(["Value (Descending)", "Value (Ascending)", "Name (A-Z)"])
        self.sort_cb.currentTextChanged.connect(self.draw_chart)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(5, 5000)
        self.limit_spin.setValue(default_top_n)
        self.limit_spin.setPrefix("Top: ")
        self.limit_spin.valueChanged.connect(self.draw_chart)

        self.export_btn = QPushButton("💾 Export Image")
        self.export_btn.clicked.connect(self.export_chart)

        ctrl_layout.addWidget(self.search_edit)
        ctrl_layout.addWidget(QLabel("Chart Type:"))
        ctrl_layout.addWidget(self.type_cb)
        ctrl_layout.addWidget(QLabel("Sort By:"))
        ctrl_layout.addWidget(self.sort_cb)
        ctrl_layout.addWidget(self.limit_spin)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.export_btn)
        self.layout.addWidget(ctrl_frame)

        # --- Matplotlib Canvas ---
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("ChartScrollArea")
        self.layout.addWidget(self.scroll_area)

        self.draw_chart()

    def update_theme(self, theme: Dict[str, str]):
        self.app_theme = theme
        self.draw_chart()

    def process_data(self) -> Tuple[List[str], List[float]]:
        filter_text = self.search_edit.text().lower()
        items = []
        for k, v in self.data_dict.items():
            if filter_text and filter_text not in str(k).lower():
                continue
            try: items.append((str(k), float(v)))
            except: continue

        sort_mode = self.sort_cb.currentText()
        if sort_mode == "Value (Descending)": items.sort(key=lambda x: x[1], reverse=True)
        elif sort_mode == "Value (Ascending)": items.sort(key=lambda x: x[1], reverse=False)
        else: items.sort(key=lambda x: x[0].lower())

        limit = self.limit_spin.value()
        if len(items) > limit and self.type_cb.currentText() == "Pie":
            leftovers = items[limit:]
            items = items[:limit]
            items.append(("Others", sum(v for _, v in leftovers)))
        elif len(items) > limit:
            items = items[:limit]

        return [k for k, _ in items], [v for _, v in items]

    def draw_chart(self):
        if self._hover_cid: self.canvas.mpl_disconnect(self._hover_cid)
        if self._click_cid: self.canvas.mpl_disconnect(self._click_cid)

        self.ax.clear()
        self.annot = None 
        chart_type = self.type_cb.currentText()
        keys, values = self.process_data()

        bg_color = self.app_theme["bg"]
        fg_color = self.app_theme["fg"]
        accent = self.app_theme["accent"]

        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        if not keys:
            self.ax.text(0.5, 0.5, "No data matches criteria", color=fg_color, ha='center', va='center')
            self.ax.set_axis_off()
            self.canvas.draw()
            return

        self.ax.set_axis_on()
        def truncate(lbl, mx=15): return lbl if len(lbl) <= mx else (lbl[:mx-1] + "…")

        min_width = max(800, len(keys) * 35) if chart_type not in ["Pie", "Histogram"] else 800
        self.canvas.setMinimumWidth(min_width)

        if chart_type == "Bar":
            bars = self.ax.bar(range(len(keys)), values, color=accent, edgecolor=bg_color)
            self.ax.set_xticks(range(len(keys)))
            self.ax.set_xticklabels([truncate(k) for k in keys], rotation=40, ha='right', color=fg_color)
            self._setup_hover(bars, keys, values, False)

        elif chart_type == "Pie":
            wedges, _ = self.ax.pie(values, colors=cm.tab20.colors, normalize=True, wedgeprops={'edgecolor': bg_color})
            self.ax.axis("equal")
            self._setup_hover(wedges, keys, values, True)

        elif chart_type == "Line":
            self.ax.plot(range(len(keys)), values, marker="o", color=accent, lw=2)
            self.ax.set_xticks(range(len(keys)))
            self.ax.set_xticklabels([truncate(k) for k in keys], rotation=40, ha='right', color=fg_color)

        elif chart_type == "Area":
            self.ax.fill_between(range(len(keys)), values, color=accent, alpha=0.4)
            self.ax.plot(range(len(keys)), values, color=accent, lw=2)
            self.ax.set_xticks(range(len(keys)))
            self.ax.set_xticklabels([truncate(k) for k in keys], rotation=40, ha='right', color=fg_color)

        elif chart_type == "Scatter":
            self.ax.scatter(range(len(keys)), values, color=accent, s=60, alpha=0.8)
            self.ax.set_xticks(range(len(keys)))
            self.ax.set_xticklabels([truncate(k) for k in keys], rotation=40, ha='right', color=fg_color)
            
        elif chart_type == "Histogram":
            self.ax.hist(values, bins=min(20, len(set(values))), color=accent, edgecolor=bg_color)
            self.ax.set_xlabel("Value Range", color=fg_color)

        if chart_type != "Pie":
            self.ax.tick_params(colors=fg_color)
            self.ax.grid(True, axis='y', linestyle='-', alpha=0.1, color=fg_color)
            for spine in self.ax.spines.values(): spine.set_color(fg_color)
            for spine in ['top', 'right']: self.ax.spines[spine].set_visible(False)
        
        self.ax.set_title(self.chart_title, color=fg_color, pad=15, fontweight='bold')
        self.fig.tight_layout()
        self.canvas.draw()

    def _setup_hover(self, artists, keys, values, is_pie):
        self.annot = self.ax.annotate("", xy=(0,0), xytext=(10, 10), textcoords="offset points",
                                      bbox=dict(boxstyle="round", fc=self.app_theme["bg"], ec=self.app_theme["accent"], alpha=0.9),
                                      color=self.app_theme["fg"], zorder=100)
        self.annot.set_visible(False)

        def hover(event):
            if event.inaxes != self.ax: return
            is_vis = False
            for art, k, v in zip(artists, keys, values):
                if art.contains(event)[0]:
                    if is_pie:
                        pct = (v / sum(values) * 100) if sum(values) else 0
                        self.annot.set_text(f"{k}\n{v:,.2f} ({pct:.1f}%)")
                        self.annot.xy = (event.xdata, event.ydata)
                    else:
                        self.annot.set_text(f"{k}\n{v:,.2f}")
                        self.annot.xy = (art.get_x() + art.get_width()/2, art.get_height())
                    self.annot.set_visible(True)
                    is_vis = True
                    break
            if not is_vis and self.annot.get_visible(): self.annot.set_visible(False)
            self.canvas.draw_idle()

        self._hover_cid = self.canvas.mpl_connect("motion_notify_event", hover)

    def export_chart(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "chart.png", "PNG (*.png);;PDF (*.pdf)")
        if path:
            self.fig.savefig(path, dpi=300, bbox_inches='tight', facecolor=self.fig.get_facecolor())
            QMessageBox.information(self, "Saved", f"Saved to {path}")


# ==========================================
# 3. Main Dashboard Window (Dialog Container)
# ==========================================
class StatisticsViewer(QDialog):
    theme_changed = Signal(dict)

    def __init__(self, stats: Dict[str, Any], parent=None, default_top_n: int = 50):
        super().__init__(parent)
        self.setWindowTitle("Pro Analytics Workspace")
        self.resize(1280, 800)
        self.stats = stats
        self._default_top_n = default_top_n
        
        # Default Theme Setup
        self.current_theme = {
            "mode": "dark", "bg": "#1e1e1e", "fg": "#e0e0e0", 
            "panel": "#252526", "border": "#333333", "accent": "#007ACC"
        }
        
        self.charts = [] 

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        # Base layout for the Dialog
        base_layout = QVBoxLayout(self)
        base_layout.setContentsMargins(0, 0, 0, 0)
        base_layout.setSpacing(0)

        # Content Container (replaces QMainWindow central widget behavior)
        content_widget = QWidget()
        main_layout = QHBoxLayout(content_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar Navigation ---
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setObjectName("Sidebar")
        
        nav_items = ["🏠 Executive Dashboard", "🏷 Tag Analytics", "🏢 Publisher Analytics", "📚 Topic Analytics", "⚙ Settings"]
        for item in nav_items:
            listItem = QListWidgetItem(item)
            listItem.setSizeHint(listItem.sizeHint().expandedTo(listItem.sizeHint().transposed() * 0 + listItem.sizeHint().transposed().expandedTo(listItem.sizeHint()) * 2))
            self.sidebar.addItem(listItem)
            
        self.sidebar.currentRowChanged.connect(self.switch_page)

        # --- Main Content Stack ---
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")

        self.stack.addWidget(self.build_dashboard_page())
        self.stack.addWidget(self.build_analytics_page(self.stats.get('Tag usage count', {}), "Tag"))
        self.stack.addWidget(self.build_analytics_page(self.stats.get('Topics per publisher', {}), "Publisher"))
        self.stack.addWidget(self.build_analytics_page(self.stats.get('Chapters per topic', {}), "Topic"))
        self.stack.addWidget(self.build_settings_page())

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        base_layout.addWidget(content_widget)

        # Status Bar Mockup for QDialog
        self.statusBarLabel = QLabel(" System Ready")
        self.statusBarLabel.setObjectName("StatusBar")
        base_layout.addWidget(self.statusBarLabel)

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        self.statusBarLabel.setText(f" Navigated to: {self.sidebar.currentItem().text()}")

    # --- Page Builders ---
    def build_dashboard_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("DashScroll")
        
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(20)

        header = QLabel("System Overview")
        header.setObjectName("PageHeader")
        grid.addWidget(header, 0, 0, 1, 4)

        metrics = [
            ("TOTAL PUBLISHERS", self.stats.get('Total publishers', 0)),
            ("TOTAL TOPICS", self.stats.get('Total topics', 0)),
            ("TOTAL CHAPTERS", self.stats.get('Total chapters', 0)),
            ("UNIQUE TAGS", self.stats.get('Total unique tags', 0)),
            ("AVG TOPICS/PUB", self.stats.get('Average topics per publisher', 0)),
            ("AVG CHAP/TOPIC", self.stats.get('Average chapters per topic', 0))
        ]

        row, col = 1, 0
        for title, val in metrics:
            card = QFrame()
            card.setObjectName("MetricCard")
            cl = QVBoxLayout(card)
            t_lbl = QLabel(title)
            t_lbl.setObjectName("CardTitle")
            v_lbl = QLabel(str(val))
            v_lbl.setObjectName("CardValue")
            cl.addWidget(t_lbl)
            cl.addWidget(v_lbl)
            cl.addStretch()
            grid.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        grid.setRowStretch(row, 1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return widget

    def build_analytics_page(self, data: Dict, entity_name: str):
        splitter = QSplitter(Qt.Vertical)
        
        # 1. Chart Section
        chart_widget = AdvancedChartWidget(data, f"{entity_name} Distribution", self._default_top_n, self)
        self.charts.append(chart_widget)
        self.theme_changed.connect(chart_widget.update_theme)
        splitter.addWidget(chart_widget)

        # 2. Table Section
        table_container = QWidget()
        tl = QVBoxLayout(table_container)
        tl.setContentsMargins(0,0,0,0)
        
        search = QLineEdit()
        search.setPlaceholderText(f"Search {entity_name} data...")
        tl.addWidget(search)

        model = DictTableModel(data, entity_name, "Value", parent=table_container)
        proxy = ContainsFilterProxy(table_container)
        proxy.setSourceModel(model)

        table = QTableView()
        table.setModel(proxy)
        table.setSortingEnabled(True)
        table.horizontalHeader().setStretchLastSection(True)
        tl.addWidget(table)
        
        search.textChanged.connect(proxy.setFilterString)
        splitter.addWidget(table_container)
        
        return splitter

    def build_settings_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        
        header = QLabel("Application Settings")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        form = QFrame()
        form.setObjectName("SettingsForm")
        fl = QGridLayout(form)
        
        # Theme Toggle
        fl.addWidget(QLabel("UI Mode:"), 0, 0)
        self.theme_cb = QComboBox()
        self.theme_cb.addItems(["Dark Mode", "Light Mode"])
        self.theme_cb.currentTextChanged.connect(self.toggle_mode)
        fl.addWidget(self.theme_cb, 0, 1)

        # Accent Color
        fl.addWidget(QLabel("Accent Color:"), 1, 0)
        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self.choose_accent_color)
        fl.addWidget(color_btn, 1, 1)

        # Data Export
        fl.addWidget(QLabel("Raw Data:"), 2, 0)
        export_json = QPushButton("Export All to JSON")
        export_json.clicked.connect(self.export_all_json)
        fl.addWidget(export_json, 2, 1)

        layout.addWidget(form)
        return widget

    # --- Interactions & Theming ---
    def toggle_mode(self, mode_text):
        if "Dark" in mode_text:
            self.current_theme.update({"mode": "dark", "bg": "#1e1e1e", "fg": "#e0e0e0", "panel": "#252526", "border": "#333333"})
        else:
            self.current_theme.update({"mode": "light", "bg": "#ffffff", "fg": "#333333", "panel": "#f3f3f3", "border": "#dddddd"})
        self.apply_theme()

    def choose_accent_color(self):
        color = QColorDialog.getColor(QColor(self.current_theme["accent"]), self, "Choose Accent Color")
        if color.isValid():
            self.current_theme["accent"] = color.name()
            self.apply_theme()

    def export_all_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Workspace", "workspace.json", "JSON (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(self.stats, f, indent=4)
            self.statusBarLabel.setText(f" Workspace exported to {path}")

    def apply_theme(self):
        t = self.current_theme
        css = f"""
            QDialog, QWidget {{ background-color: {t['bg']}; color: {t['fg']}; font-family: 'Segoe UI', Arial; font-size: 13px; }}
            
            #Sidebar {{ background-color: {t['panel']}; border-right: 1px solid {t['border']}; outline: none; }}
            #Sidebar::item {{ padding: 15px; border-bottom: 1px solid {t['border']}; }}
            #Sidebar::item:selected {{ background-color: {t['accent']}; color: white; font-weight: bold; border-left: 4px solid white; }}
            #Sidebar::item:hover:!selected {{ background-color: {t['border']}; }}
            
            #PageHeader {{ font-size: 24px; font-weight: bold; padding: 10px 0px; color: {t['fg']}; }}
            
            #MetricCard {{ background-color: {t['panel']}; border: 1px solid {t['border']}; border-radius: 8px; border-top: 4px solid {t['accent']}; padding: 15px; }}
            #CardTitle {{ font-size: 11px; font-weight: bold; color: #888; }}
            #CardValue {{ font-size: 28px; font-weight: bold; color: {t['accent']}; }}
            
            #SettingsForm {{ background-color: {t['panel']}; border-radius: 8px; padding: 20px; }}
            
            QLineEdit, QComboBox, QSpinBox {{ padding: 8px; background-color: {t['bg']}; border: 1px solid {t['border']}; border-radius: 4px; color: {t['fg']}; }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {t['accent']}; }}
            
            QPushButton {{ padding: 8px 16px; background-color: {t['accent']}; color: white; border: none; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {t['accent']}dd; }}
            
            QTableView {{ background-color: {t['bg']}; gridline-color: {t['border']}; alternate-background-color: {t['panel']}; selection-background-color: {t['accent']}; border: 1px solid {t['border']}; border-radius: 4px; }}
            QHeaderView::section {{ background-color: {t['panel']}; color: {t['fg']}; padding: 8px; border: none; border-bottom: 1px solid {t['border']}; border-right: 1px solid {t['border']}; }}
            
            QSplitter::handle {{ background-color: {t['border']}; }}
            
            #StatusBar {{ background-color: {t['accent']}; color: white; font-weight: bold; padding: 5px; }}
        """
        self.setStyleSheet(css)
        self.theme_changed.emit(t)


# ==========================================
# 4. App Launcher
# ==========================================
if __name__ == "__main__":
    # Robust Dummy Data
    demo_stats = {
        "Total publishers": 240, "Total topics": 4500, "Total chapters": 22000, "Total unique tags": 5100,
        "Average topics per publisher": 18.7, "Average chapters per topic": 4.8,
        "Tag usage count": {f"tag_{i}": int(np.random.exponential(2) * 100) for i in range(1500)}, 
        "Topics per publisher": {f"Pub_{i}": int(np.random.normal(50, 15)) for i in range(240)},
        "Chapters per topic": {f"Topic_{i}": int(np.random.poisson(5)) + 1 for i in range(4500)},
    }
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = StatisticsViewer(demo_stats, default_top_n=50)
    window.exec() # Use exec() as it's now a QDialog again
