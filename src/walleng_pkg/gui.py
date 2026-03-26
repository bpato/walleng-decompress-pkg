"""Graphical user interface for walleng-pkg."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from walleng_pkg.core import PackageInfo, extract_package, parse_package


class ExtractionThread(QThread):
    """Worker thread for file extraction."""
    
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, package_path: Path, output_dir: Path):
        super().__init__()
        self.package_path = package_path
        self.output_dir = output_dir
    
    def run(self):
        try:
            self.progress.emit("Parsing package...")
            info = parse_package(self.package_path)
            
            self.progress.emit(f"Extracting {len(info.files)} files...")
            extracted = extract_package(self.package_path, self.output_dir)
            
            self.finished.emit(extracted)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QWidget):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.package_path: Path | None = None
        self.package_info: PackageInfo | None = None
        self.extraction_thread: ExtractionThread | None = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("walleng-pkg")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        self.package_label = QLabel("No file selected")
        self.package_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self.package_label)
        
        select_btn = QPushButton("Select .pkg File")
        select_btn.clicked.connect(self.select_file)
        header_layout.addWidget(select_btn)
        
        layout.addLayout(header_layout)
        
        info_layout = QHBoxLayout()
        self.root_label = QLabel("Root: -")
        self.files_label = QLabel("Files: -")
        info_layout.addWidget(self.root_label)
        info_layout.addWidget(self.files_label)
        layout.addLayout(info_layout)
        
        self.file_list = QListWidget()
        layout.addWidget(QLabel("Files:"))
        layout.addWidget(self.file_list)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        self.extract_btn = QPushButton("Extract")
        self.extract_btn.clicked.connect(self.extract)
        self.extract_btn.setEnabled(False)
        btn_layout.addWidget(self.extract_btn)
        
        self.output_btn = QPushButton("Change Output Directory")
        self.output_btn.clicked.connect(self.select_output_dir)
        btn_layout.addWidget(self.output_btn)
        
        layout.addLayout(btn_layout)
        
        self.output_dir = Path.cwd()
        self.output_label = QLabel(f"Output: {self.output_dir}")
        layout.addWidget(self.output_label)
    
    @Slot()
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Package File",
            str(Path.cwd()),
            "Package Files (*.pkg);;All Files (*)",
        )
        if path:
            self.package_path = Path(path)
            self.package_label.setText(f"File: {self.package_path.name}")
            self.package_label.setStyleSheet("color: black;")
            self.load_package_info()
    
    @Slot()
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            str(self.output_dir),
        )
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_label.setText(f"Output: {self.output_dir}")
    
    def load_package_info(self):
        try:
            if self.package_path is None:
                return
            self.package_info = parse_package(self.package_path)
            self.root_label.setText(f"Root: {self.package_info.root}")
            self.files_label.setText(f"Files: {len(self.package_info.files)}")
            
            self.file_list.clear()
            for entry in self.package_info.files:
                self.file_list.addItem(f"{entry.name} ({entry.length:,} bytes)")
            
            self.extract_btn.setEnabled(True)
            self.status_label.setText("")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse package:\n{e}")
    
    @Slot()
    def extract(self):
        if not self.package_path:
            return
        
        self.extract_btn.setEnabled(False)
        self.status_label.setText("Extracting...")
        
        self.extraction_thread = ExtractionThread(self.package_path, self.output_dir)
        self.extraction_thread.finished.connect(self.on_extraction_finished)
        self.extraction_thread.error.connect(self.on_extraction_error)
        self.extraction_thread.progress.connect(self.status_label.setText)
        self.extraction_thread.start()
    
    @Slot(list)
    def on_extraction_finished(self, extracted: list):
        self.extract_btn.setEnabled(True)
        self.status_label.setText(f"Done! Extracted {len(extracted)} files.")
        
        reply = QMessageBox.question(
            self,
            "Extraction Complete",
            f"Extracted {len(extracted)} files.\n\nOpen output directory?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))
    
    @Slot(str)
    def on_extraction_error(self, error_msg: str):
        self.extract_btn.setEnabled(True)
        self.status_label.setText("Error")
        QMessageBox.critical(self, "Extraction Error", error_msg)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
