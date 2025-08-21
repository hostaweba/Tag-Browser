import os
import csv
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QLineEdit, QFileDialog, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from Modules.tag_editor import TagEditor
from Modules.utils import load_tags, save_tags, open_folder
from Modules.statistics import StatisticsViewer

class TagBrowser(QMainWindow):
    """
    Main application window for browsing and managing tags across publishers, topics, and chapters.
    """
    def __init__(self, root_directory):
        super().__init__()
        self.root_directory = root_directory
        self.tag_cache = {}  # Maps relative paths to their tag lists

        # === Window setup ===
        self.setWindowTitle("Tag Browser")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon("resources/icon2.png"))

        # === Search boxes ===
        self.global_search_box = QLineEdit()
        self.global_search_box.setPlaceholderText("🔍 Global search...")

        self.publisher_search_box = QLineEdit(); self.publisher_search_box.setPlaceholderText("Search publishers...")
        self.topic_search_box = QLineEdit(); self.topic_search_box.setPlaceholderText("Search topics...")
        self.chapter_search_box = QLineEdit(); self.chapter_search_box.setPlaceholderText("Search chapters...")
        self.tag_search_box = QLineEdit(); self.tag_search_box.setPlaceholderText("Search tags...")

        # === List widgets for hierarchy ===
        self.publisher_list = QListWidget()
        self.topic_list = QListWidget()
        self.chapter_list = QListWidget()
        self.tag_list = QListWidget()

        # === Action buttons ===
        self.export_tags_button = QPushButton("📤 Export Tags")
        self.import_overwrite_button = QPushButton("📥 Import & Overwrite")
        self.import_merge_button = QPushButton("🔀 Import & Merge")
        self.clear_all_tags_button = QPushButton("🧹 Clear All Tags")
        self.show_statistics_button = QPushButton("📈 Statistics")

        # === Build layout ===
        self.build_layout()

        # === Load data on startup ===
        self.load_publishers()
        self.load_all_tags()

        # === Connect UI events to logic ===
        self.setup_connections()

    def build_layout(self):
        """Assemble the window layout using toolbars, splitters, and lists."""
        # Top toolbar layout
        top_toolbar = QHBoxLayout()
        top_toolbar.addWidget(self.global_search_box)
        top_toolbar.addWidget(self.export_tags_button)
        top_toolbar.addWidget(self.import_overwrite_button)
        top_toolbar.addWidget(self.import_merge_button)
        top_toolbar.addWidget(self.clear_all_tags_button)
        top_toolbar.addWidget(self.show_statistics_button)

        # Hierarchical sections: Publishers → Topics → Chapters → Tags
        hierarchy_splitter = QSplitter()
        hierarchy_splitter.addWidget(self.create_list_section("Publishers", self.publisher_search_box, self.publisher_list))
        hierarchy_splitter.addWidget(self.create_list_section("Topics", self.topic_search_box, self.topic_list))
        hierarchy_splitter.addWidget(self.create_list_section("Chapters", self.chapter_search_box, self.chapter_list))
        hierarchy_splitter.addWidget(self.create_list_section("Tags", self.tag_search_box, self.tag_list))

        # Main vertical layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_toolbar)
        main_layout.addWidget(hierarchy_splitter)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def create_list_section(self, title, search_box, list_widget):
        """Create a titled section with a search box and list widget."""
        section_layout = QVBoxLayout()
        section_layout.addWidget(QLabel(f"<b>{title}</b>"))
        section_layout.addWidget(search_box)
        section_layout.addWidget(list_widget)
        section_widget = QWidget()
        section_widget.setLayout(section_layout)
        return section_widget

    def setup_connections(self):
        """Connect UI events (search, click, double-click, context menus) to handler methods."""
        # Global and section search
        self.global_search_box.textChanged.connect(self.global_search)
        self.publisher_search_box.textChanged.connect(self.filter_publishers)
        self.topic_search_box.textChanged.connect(self.filter_topics)
        self.chapter_search_box.textChanged.connect(self.filter_chapters)
        self.tag_search_box.textChanged.connect(self.filter_tags)

        # Button actions
        self.export_tags_button.clicked.connect(self.export_tags)
        self.import_overwrite_button.clicked.connect(lambda: self.import_tags(overwrite=True))
        self.import_merge_button.clicked.connect(lambda: self.import_tags(overwrite=False))
        self.clear_all_tags_button.clicked.connect(self.clear_all_tags)
        self.show_statistics_button.clicked.connect(self.show_statistics)

        # List interactions
        self.publisher_list.itemClicked.connect(self.load_topics)
        self.topic_list.itemClicked.connect(self.load_chapters)
        self.tag_list.itemClicked.connect(self.filter_by_tag)

        self.publisher_list.itemDoubleClicked.connect(lambda: self.open_selected_folder(self.publisher_list))
        self.topic_list.itemDoubleClicked.connect(lambda: self.open_selected_folder(self.topic_list))
        self.chapter_list.itemDoubleClicked.connect(lambda: self.open_selected_folder(self.chapter_list))

        # Context menus for editing tags
        self.topic_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.topic_list.customContextMenuRequested.connect(lambda pos: self.show_edit_tags_menu(self.topic_list, pos))
        self.chapter_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chapter_list.customContextMenuRequested.connect(lambda pos: self.show_edit_tags_menu(self.chapter_list, pos))

    # === Data loading methods ===
    def load_publishers(self):
        """Load publisher folders (with certain prefixes) into the publisher list."""
        prefixes = ('$_', '$__', '#_', '#__', '__')
        self.all_publishers = sorted([
            name for name in os.listdir(self.root_directory)
            if os.path.isdir(os.path.join(self.root_directory, name)) and name.startswith(prefixes)
        ])
        self.publisher_list.clear()
        self.publisher_list.addItems(self.all_publishers)

    def load_all_tags(self):
        """Scan all directories for tag.txt files and cache tags."""
        self.tag_cache.clear()
        for dirpath, _, _ in os.walk(self.root_directory):
            relative = os.path.relpath(dirpath, self.root_directory)
            tags = load_tags(os.path.join(dirpath, 'tag.txt'))
            if tags:
                self.tag_cache[relative] = tags

        self.all_tags = sorted({tag for tags in self.tag_cache.values() for tag in tags})
        self.tag_list.clear()
        self.tag_list.addItems(self.all_tags)

    def load_topics(self, publisher_item):
        """Load topic folders under selected publisher."""
        publisher = publisher_item.text()
        publisher_path = os.path.join(self.root_directory, publisher)
        topics = sorted([
            topic for topic in os.listdir(publisher_path)
            if os.path.isdir(os.path.join(publisher_path, topic))
        ])
        self.all_topics = [(topic, os.path.join(publisher, topic)) for topic in topics]
        self.update_list_widget(self.topic_list, self.all_topics)
        self.chapter_list.clear()

    def load_chapters(self, topic_item):
        """Load chapter folders under selected topic."""
        topic_relative = topic_item.data(Qt.UserRole)
        topic_path = os.path.join(self.root_directory, topic_relative)
        topic_name = os.path.basename(topic_relative)
        chapters = sorted([
            chapter for chapter in os.listdir(topic_path)
            if os.path.isdir(os.path.join(topic_path, chapter))
        ])
        self.all_chapters = [(f"{chapter} ({topic_name})", os.path.join(topic_relative, chapter)) for chapter in chapters]
        self.update_list_widget(self.chapter_list, self.all_chapters)

    # === Filtering and search methods ===
    def global_search(self, text):
        """
        Search across publishers, topics, chapters, and tags simultaneously.
        """
        query = text.strip().lower()
        if not query:
            self.reset_all_lists()
            return

        matched_publishers = [p for p in self.all_publishers if query in p.lower()]
        matched_tags = [tag for tag in self.all_tags if query in tag.lower()]

        matched_topics = []
        matched_chapters = []
        for relative_path, tags in self.tag_cache.items():
            parts = relative_path.split(os.sep)
            last_folder = parts[-1].lower()
            if query in last_folder or any(query in tag.lower() for tag in tags):
                if len(parts) == 2:
                    matched_topics.append((parts[1], relative_path))
                elif len(parts) == 3:
                    matched_chapters.append((f"{parts[2]} ({parts[1]})", relative_path))

        self.publisher_list.clear(); self.publisher_list.addItems(matched_publishers)
        self.update_list_widget(self.topic_list, matched_topics)
        self.update_list_widget(self.chapter_list, matched_chapters)
        self.tag_list.clear(); self.tag_list.addItems(matched_tags)

    def filter_publishers(self, text):
        """Filter publishers by text."""
        filtered = [p for p in self.all_publishers if text.lower().strip() in p.lower()]
        self.publisher_list.clear(); self.publisher_list.addItems(filtered)

    def filter_topics(self, text):
        """Filter topics by text."""
        filtered = [(name, rel) for name, rel in getattr(self, 'all_topics', []) if text.lower().strip() in name.lower()]
        self.update_list_widget(self.topic_list, filtered)

    def filter_chapters(self, text):
        """Filter chapters by text."""
        filtered = [(name, rel) for name, rel in getattr(self, 'all_chapters', []) if text.lower().strip() in name.lower()]
        self.update_list_widget(self.chapter_list, filtered)

    def filter_tags(self, text):
        """Filter tags by text."""
        filtered = [tag for tag in self.all_tags if text.lower().strip() in tag.lower()]
        self.tag_list.clear(); self.tag_list.addItems(filtered)

    def filter_by_tag(self, tag_item):
        """
        Show only topics and chapters containing the clicked tag.
        """
        clicked_tag = tag_item.text().strip().lower()
        matched_topics, matched_chapters = [], []

        for dirpath, _, _ in os.walk(self.root_directory):
            tag_file = os.path.join(dirpath, 'tag.txt')
            if os.path.isfile(tag_file):
                tags = [t.lower() for t in load_tags(tag_file)]
                if clicked_tag in tags:
                    relative = os.path.relpath(dirpath, self.root_directory)
                    parts = relative.split(os.sep)
                    if len(parts) == 2:
                        matched_topics.append((f"{parts[1]} ({parts[0]})", relative))
                    elif len(parts) == 3:
                        matched_chapters.append((f"({parts[0]}) ({parts[1]}) {parts[2]}", relative))

        self.update_list_widget(self.topic_list, matched_topics)
        self.update_list_widget(self.chapter_list, matched_chapters)

    # === Helper methods ===
    def update_list_widget(self, list_widget, items):
        """Update list widget with new items, storing relative paths as metadata."""
        list_widget.clear()
        for name, relative in items:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, relative)
            list_widget.addItem(item)

    def reset_all_lists(self):
        """Reset to default publisher list, clear topics and chapters, and reload tags."""
        self.load_publishers()
        self.load_all_tags()
        self.topic_list.clear()
        self.chapter_list.clear()

    def open_selected_folder(self, list_widget):
        """Open folder corresponding to selected list item."""
        item = list_widget.currentItem()
        if item:
            relative = item.data(Qt.UserRole) or item.text()
            open_folder(os.path.join(self.root_directory, relative))

    def show_edit_tags_menu(self, list_widget, pos):
        """Show TagEditor dialog on context menu click."""
        item = list_widget.itemAt(pos)
        if item:
            relative = item.data(Qt.UserRole)
            tag_file = os.path.join(self.root_directory, relative, 'tag.txt')
            if TagEditor(tag_file, self).exec():
                self.load_all_tags()

    # === Tag import/export and clearing ===
    def export_tags(self):
        """Export tag cache to a CSV file."""
        fname, _ = QFileDialog.getSaveFileName(self, "Export Tags", "", "CSV Files (*.csv)")
        if fname:
            with open(fname, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Path', 'Tags'])
                for relative, tags in self.tag_cache.items():
                    writer.writerow([relative, ', '.join(tags)])
            QMessageBox.information(self, "Export", "Export successful!")

    def import_tags(self, overwrite=True):
        """Import tags from CSV, optionally overwriting existing tags."""
        fname, _ = QFileDialog.getOpenFileName(self, "Import Tags CSV", "", "CSV Files (*.csv)")
        if fname:
            with open(fname, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    relative = row['Path']
                    new_tags = [t.strip() for t in row['Tags'].split(',') if t.strip()]
                    full_path = os.path.join(self.root_directory, relative)
                    if os.path.isdir(full_path):
                        tag_file = os.path.join(full_path, 'tag.txt')
                        if overwrite:
                            save_tags(tag_file, new_tags)
                            self.tag_cache[relative] = new_tags
                        else:
                            existing = load_tags(tag_file)
                            combined = list(set(existing + new_tags))
                            save_tags(tag_file, combined)
                            self.tag_cache[relative] = combined
            self.load_all_tags()
            QMessageBox.information(self, "Import", "Import successful!")

    def clear_all_tags(self):
        """Clear all tags in tag.txt files after confirmation."""
        if QMessageBox.question(self, "Clear All", "Are you sure?") == QMessageBox.Yes:
            for relative in list(self.tag_cache.keys()):
                tag_file = os.path.join(self.root_directory, relative, 'tag.txt')
                save_tags(tag_file, [])
                self.tag_cache[relative] = []
            self.load_all_tags()

    # === Statistics ===
    def show_statistics(self):
        """Compute and show statistics about publishers, topics, chapters, and tags."""
        stats = self.compute_statistics()
        StatisticsViewer(stats, self).exec()

    def compute_statistics(self):
        """Compute various counts and detailed breakdowns for statistics."""
        stats = {'Total publishers': len(self.all_publishers)}

        # Topics per publisher
        publisher_topic_count = {}
        for pub in self.all_publishers:
            pub_path = os.path.join(self.root_directory, pub)
            topics = [t for t in os.listdir(pub_path) if os.path.isdir(os.path.join(pub_path, t))]
            publisher_topic_count[pub] = len(topics)
        stats['Total topics'] = sum(publisher_topic_count.values())

        # Chapters per topic
        topic_chapter_count = {}
        total_chapters = 0
        for pub, topic_count in publisher_topic_count.items():
            pub_path = os.path.join(self.root_directory, pub)
            for topic in os.listdir(pub_path):
                topic_path = os.path.join(pub_path, topic)
                if os.path.isdir(topic_path):
                    chapters = [c for c in os.listdir(topic_path) if os.path.isdir(os.path.join(topic_path, c))]
                    topic_chapter_count[f"{pub}/{topic}"] = len(chapters)
                    total_chapters += len(chapters)
        stats['Total chapters'] = total_chapters

        # Tag counts
        stats['Total unique tags'] = len(self.all_tags)
        tag_usage_count = {tag: sum(1 for tags in self.tag_cache.values() if tag in tags) for tag in self.all_tags}

        stats['Topics per publisher'] = publisher_topic_count
        stats['Chapters per topic'] = topic_chapter_count
        stats['Tag usage count'] = tag_usage_count

        return stats


    def show_statistics(self):
        """
        Show statistics in dialog.
        """
        stats = self.compute_statistics()
        dlg = StatisticsViewer(stats, self)
        dlg.exec()
