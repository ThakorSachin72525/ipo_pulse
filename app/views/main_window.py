"""Main application window for the IPO Pulse GUI."""

import sys
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication


def build_main_window():
    """Load the Qt Designer .ui file and wire the button behavior."""
    ui_path = Path(__file__).resolve().parent / "ui" / "main_window.ui"
    ui_file = QFile(str(ui_path))

    if not ui_file.exists():
        raise FileNotFoundError(f"UI file not found: {ui_path}")

    ui_file.open(QFile.ReadOnly)
    loader = QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()

    if window is None:
        raise RuntimeError("Failed to load the UI form.")

    window.statusLabel.setText("IPO Pulse is ready.")
    window.loadButton.clicked.connect(
        lambda: window.statusLabel.setText("Sample IPO data loaded successfully.")
    )
    return window


def main() -> int:
    app = QApplication(sys.argv)
    window = build_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
