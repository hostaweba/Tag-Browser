from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTabWidget, QWidget,
    QLineEdit, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class StatisticsViewer(QDialog):
    """
    A dialog to display detailed statistics using multiple tabs:
    - Summary overview
    - Tables (e.g., tag usage, topics per publisher)
    - Interactive charts and pie charts
    """
    def __init__(self, stats, parent=None):
        """
        :param stats: Dictionary with precomputed statistics.
        :param parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Detailed Statistics")
        self.resize(900, 600)

        tabs = QTabWidget()

        # === Summary tab ===
        summary_tab = QWidget()
        summary_layout = QVBoxLayout()

        # Build summary as rich text
        summary_text = (
            "<h2>📊 Overview</h2>"
            f"<b>Total publishers:</b> {stats['Total publishers']}<br>"
            f"<b>Total topics:</b> {stats['Total topics']}<br>"
            f"<b>Total chapters:</b> {stats['Total chapters']}<br>"
            f"<b>Total unique tags:</b> {stats['Total unique tags']}<br>"
        )
        if 'Average topics per publisher' in stats:
            summary_text += f"<b>Average topics per publisher:</b> {stats['Average topics per publisher']}<br>"
        if 'Average chapters per topic' in stats:
            summary_text += f"<b>Average chapters per topic:</b> {stats['Average chapters per topic']}<br>"
        if 'Most used tag' in stats:
            tag, count = stats['Most used tag']
            summary_text += f"<b>Most used tag:</b> {tag} ({count} uses)<br>"
        if 'Least used tags' in stats and stats['Least used tags']:
            summary_text += f"<b>Least used tags:</b> {', '.join(stats['Least used tags'])}<br>"

        summary_label = QLabel(summary_text)
        summary_label.setTextFormat(Qt.RichText)
        summary_label.setStyleSheet("font-size: 14px; margin: 10px;")
        summary_layout.addWidget(summary_label)
        summary_layout.addStretch()
        summary_tab.setLayout(summary_layout)
        tabs.addTab(summary_tab, "📊 Summary")

        # === Table tabs ===
        tabs.addTab(self.make_table_tab(stats['Tag usage count'], "Tag", "Count"), "🏷 Tag Usage")
        tabs.addTab(self.make_table_tab(stats['Topics per publisher'], "Publisher", "Topics"), "🏢 Topics per Publisher")
        tabs.addTab(self.make_table_tab(stats['Chapters per topic'], "Topic", "Chapters"), "📚 Chapters per Topic")

        # === Chart tabs ===
        tabs.addTab(self.make_chart_tab(stats['Tag usage count'], "Tag Usage Chart", kind="bar"), "📊 Tag Chart")
        tabs.addTab(self.make_chart_tab(stats['Topics per publisher'], "Topics per Publisher Chart", kind="bar"), "🏢 Publisher Chart")
        tabs.addTab(self.make_chart_tab(stats['Chapters per topic'], "Chapters per Topic Chart", kind="bar"), "📚 Topic Chart")
        tabs.addTab(self.make_chart_tab(stats['Tag usage count'], "Tag Usage Pie", kind="pie"), "🥧 Tag Pie")
        tabs.addTab(self.make_chart_tab(stats['Tag usage count'], "Top 20 Tags", kind="bar", top_n=20), "📊 Top Tags")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

    def make_table_tab(self, data_dict, col1_name, col2_name):
        """
        Create a tab with a searchable table.
        """
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        search = QLineEdit()
        search.setPlaceholderText(f"🔍 Search {col1_name}...")
        search.setClearButtonEnabled(True)
        search.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                font-size: 13px;
                color: #ffffff;
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
            }
        """)
        layout.addWidget(search)

        # Table widget
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels([col1_name, col2_name])
        table.setRowCount(len(data_dict))
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)

        # Dark style
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #242424;
                color: #f0f0f0;
                gridline-color: #444444;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #444444;
                color: #dddddd;
                padding: 4px;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #555555;
            }
        """)

        # Fill table data
        for row, (key, value) in enumerate(sorted(data_dict.items(), key=lambda x: str(x[0]).lower())):
            table.setItem(row, 0, QTableWidgetItem(str(key)))
            table.setItem(row, 1, QTableWidgetItem(str(value)))

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        # Filter table on search
        def filter_table(text):
            lower = text.lower()
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                table.setRowHidden(row, lower not in item.text().lower())

        search.textChanged.connect(filter_table)

        widget.setLayout(layout)
        return widget

    def make_chart_tab(self, data_dict, title, kind="bar", top_n=None):
        """
        Create a tab with a matplotlib chart: bar or pie.
        """
        widget = QWidget()
        layout = QVBoxLayout()

        fig = Figure(facecolor="#2b2b2b")
        ax = fig.add_subplot(111)
        fig.subplots_adjust(bottom=0.3)

        # Use top_n items if requested
        items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        if top_n:
            items = items[:top_n]
        keys = [str(k) for k, v in items]
        values = [v for k, v in items]

        if kind == "bar":
            positions = range(len(keys))
            bars = ax.bar(positions, values, color="#5aa9e6")
            ax.set_xticks(positions)
            ax.set_xticklabels(keys, rotation=45, ha='right', color="#dddddd")
            ax.tick_params(axis='y', colors="#dddddd")
            ax.title.set_text(title)
            ax.title.set_color("#dddddd")

            # Tooltip annotation
            annot = ax.annotate(
                "", xy=(0,0), xytext=(20,20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc=(0,0,0,0.8), ec="#dddddd"),
                fontsize=10, color="#ffffff", ha='center'
            )
            annot.set_visible(False)

            def on_hover(event):
                visible = False
                for bar, key, value in zip(bars, keys, values):
                    if bar.contains(event)[0]:
                        annot.xy = (event.xdata, event.ydata)
                        annot.set_text(f"{key}: {value}")
                        annot.set_visible(True)
                        visible = True
                        break
                if not visible:
                    annot.set_visible(False)
                canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", on_hover)

        elif kind == "pie":
            wedges, _ = ax.pie(values, labels=None, textprops={'color': "w"})
            ax.set_facecolor("#2b2b2b")
            ax.title.set_text(title)
            ax.title.set_color("#dddddd")

            annot = ax.annotate(
                "", xy=(0,0), xytext=(20,20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc=(0,0,0,0.8), ec="#dddddd"),
                fontsize=10, color="#ffffff", ha='center'
            )
            annot.set_visible(False)

            def on_hover(event):
                visible = False
                for wedge, key, value in zip(wedges, keys, values):
                    if wedge.contains_point((event.x, event.y)):
                        annot.xy = (event.xdata, event.ydata)
                        annot.set_text(f"{key}: {value}")
                        annot.set_visible(True)
                        visible = True
                        break
                if not visible:
                    annot.set_visible(False)
                canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", on_hover)

        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        widget.setLayout(layout)
        return widget
