import os
import sys


# === Utilities ===
def load_tags(tag_file):
    """
    Load tags from a comma-separated file, removing whitespace.
    Returns a list of tags.
    """
    if os.path.isfile(tag_file):
        with open(tag_file, 'r', encoding='utf-8') as f:
            return [t.strip() for t in f.read().split(',') if t.strip()]
    return []


def save_tags(tag_file, tags):
    """
    Save unique, sorted tags as a comma-separated string into a file.
    """
    with open(tag_file, 'w', encoding='utf-8') as f:
        f.write(', '.join(sorted(set(tags))))


def open_folder(path):
    """
    Open the given folder in the OS file explorer.
    """
    if os.name == 'nt':  # Windows
        os.startfile(path)
    elif sys.platform == 'darwin':  # macOS
        os.system(f'open "{path}"')
    else:  # Linux and others
        os.system(f'xdg-open "{path}"')
