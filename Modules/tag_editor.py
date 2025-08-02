from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QLineEdit
)
from Modules.utils import load_tags, save_tags

class TagEditor(QDialog):
    """
    A simple dialog for editing tags stored in a tag.txt file.
    
    Loads existing tags, displays them as comma-separated text,
    and saves them back to file when accepted.
    """
    def __init__(self, tag_file, parent=None):
        """
        :param tag_file: Path to the tag.txt file to edit.
        :param parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Tags")
        self.tag_file = tag_file

        # Load existing tags and show them in a single line edit field
        existing_tags = load_tags(tag_file)
        self.edit = QLineEdit(', '.join(existing_tags))

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Dialog layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tags (comma separated):"))
        layout.addWidget(self.edit)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def accept(self):
        """
        Collect tags from the input, clean them,
        save back to file, then close the dialog.
        """
        # Parse tags: remove whitespace and empty items
        tags = [t.strip() for t in self.edit.text().split(',') if t.strip()]
        save_tags(self.tag_file, tags)
        super().accept()
