import sys
import os
import csv
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from Modules.tag_browser import TagBrowser


# === Run app ===
def main():
    """
    Entry point for the Tag Browser application.
    Loads the root directory from 'address.csv', sets up the dark-themed Qt application,
    and launches the TagBrowser main window.
    """
    root_dir = None

    # Try to read the first valid folder path from address.csv
    try:
        file_path = os.path.join("recources", "address.csv")
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)            
            
            for row in reader:
                # Check if row is non-empty and the path exists as a directory
                if row and os.path.isdir(row[0]):
                    root_dir = row[0]
                    break
    except FileNotFoundError:
        # Show error if the CSV file is missing
        QMessageBox.critical(None, "Error", "address.csv file not found.")
        return

    if not root_dir:
        # Show error if no valid folder path is found
        QMessageBox.critical(None, "Error", "Valid folder path not found in address.csv.")
        return

    # Create the Qt application
    app = QApplication(sys.argv)

    # Apply a custom dark Fusion style palette
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(50, 50, 50))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(100, 150, 220))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    # Launch the TagBrowser main window with the selected root directory
    window = TagBrowser(root_dir)
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
