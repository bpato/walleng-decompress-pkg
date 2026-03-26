"""Graphical user interface for walleng-pkg."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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
from walleng_pkg.i18n import init_i18n, set_language, tr


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
            self.progress.emit(tr("parsing_package"))
            info = parse_package(self.package_path)
            
            self.progress.emit(tr("extracting_files", n=len(info.files)))
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
        self.retranslate_ui()
    
    def setup_ui(self):
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        self.package_label = QLabel()
        self.package_label.setStyleSheet("color: gray;")
        header_layout.addWidget(self.package_label)
        
        self.select_btn = QPushButton()
        self.select_btn.clicked.connect(self.select_file)
        header_layout.addWidget(self.select_btn)
        
        layout.addLayout(header_layout)
        
        info_layout = QHBoxLayout()
        self.root_label = QLabel()
        self.files_label = QLabel()
        info_layout.addWidget(self.root_label)
        info_layout.addWidget(self.files_label)
        layout.addLayout(info_layout)
        
        self.file_list = QListWidget()
        self.files_header = QLabel()
        layout.addWidget(self.files_header)
        layout.addWidget(self.file_list)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        self.extract_btn = QPushButton()
        self.extract_btn.clicked.connect(self.extract)
        self.extract_btn.setEnabled(False)
        btn_layout.addWidget(self.extract_btn)
        
        self.output_btn = QPushButton()
        self.output_btn.clicked.connect(self.select_output_dir)
        btn_layout.addWidget(self.output_btn)
        
        layout.addLayout(btn_layout)
        
        self.output_dir = Path.cwd()
        self.output_label = QLabel()
        layout.addWidget(self.output_label)
        
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Español"])
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
    
    def retranslate_ui(self):
        self.setWindowTitle(tr("app_title"))
        self.package_label.setText(tr("no_file_selected"))
        self.select_btn.setText(tr("select_pkg_file"))
        self.root_label.setText(f"{tr('root')}: -")
        self.files_label.setText(f"{tr('files')}: -")
        self.files_header.setText(f"{tr('files_label')}")
        self.extract_btn.setText(tr("extract"))
        self.output_btn.setText(tr("change_output_dir"))
        self.output_label.setText(f"{tr('output')}: {self.output_dir}")
        self.lang_label.setText("Language:")
    
    @Slot(int)
    def change_language(self, index: int):
        lang_map = {"en": "English", "es": "Español"}
        for code, name in lang_map.items():
            if name == self.lang_combo.currentText():
                set_language(code)
                break
        self.retranslate_ui()
    
    @Slot()
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("select_package_file"),
            str(Path.cwd()),
            tr("package_files"),
        )
        if path:
            self.package_path = Path(path)
            self.package_label.setText(f"{tr('file')}: {self.package_path.name}")
            self.package_label.setStyleSheet("color: black;")
            self.load_package_info()
    
    @Slot()
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            tr("select_output_directory"),
            str(self.output_dir),
        )
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_label.setText(f"{tr('output')}: {self.output_dir}")
    
    def load_package_info(self):
        try:
            if self.package_path is None:
                return
            self.package_info = parse_package(self.package_path)
            self.root_label.setText(f"{tr('root')}: {self.package_info.root}")
            self.files_label.setText(f"{tr('files')}: {len(self.package_info.files)}")
            
            self.file_list.clear()
            for entry in self.package_info.files:
                self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')})")
            
            self.extract_btn.setEnabled(True)
            self.status_label.setText("")
        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"{tr('failed_to_parse')}\n{e}")
    
    @Slot()
    def extract(self):
        if not self.package_path:
            return
        
        self.extract_btn.setEnabled(False)
        self.status_label.setText(tr("parsing_package"))
        
        self.extraction_thread = ExtractionThread(self.package_path, self.output_dir)
        self.extraction_thread.finished.connect(self.on_extraction_finished)
        self.extraction_thread.error.connect(self.on_extraction_error)
        self.extraction_thread.progress.connect(self.status_label.setText)
        self.extraction_thread.start()
    
    @Slot(list)
    def on_extraction_finished(self, extracted: list):
        self.extract_btn.setEnabled(True)
        self.status_label.setText(tr("done", n=len(extracted)))
        
        reply = QMessageBox.question(
            self,
            tr("extraction_complete"),
            f"{tr('done', n=len(extracted))}\n\n{tr('open_output_dir')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))
    
    @Slot(str)
    def on_extraction_error(self, error_msg: str):
        self.extract_btn.setEnabled(True)
        self.status_label.setText(tr("error"))
        QMessageBox.critical(self, tr("extraction_error"), error_msg)


def main():
    init_i18n()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
