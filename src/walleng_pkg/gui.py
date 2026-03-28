"""Graphical user interface for walleng-pkg."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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

from walleng_pkg.core import FileEntry, PackageInfo, extract_package, parse_package
from walleng_pkg.i18n import init_i18n, set_language, tr
from walleng_pkg.tex import TexInfo, extract_textures as extract_tex_textures, parse_tex_package


class ExtractionThread(QThread):
    """Worker thread for file extraction."""
    
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, package_path: Path, output_dir: Path, extract_tex: bool = False):
        super().__init__()
        self.package_path = package_path
        self.output_dir = output_dir
        self.extract_tex = extract_tex
    
    def run(self):
        try:
            if self.package_path.suffix.lower() == ".tex":
                self.progress.emit(tr("extracting_textures"))
                extracted = extract_tex_textures(self.package_path, self.output_dir)
            else:
                self.progress.emit(tr("parsing_package"))
                info = parse_package(self.package_path)
                
                self.progress.emit(tr("extracting_files", n=len(info.files)))
                extracted = extract_package(self.package_path, self.output_dir, self.extract_tex)
            
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
        self.file_list.itemDoubleClicked.connect(self.on_file_double_clicked)
        self.files_header = QLabel()
        layout.addWidget(self.files_header)
        layout.addWidget(self.file_list)
        
        self.tex_checkbox = QCheckBox()
        self.tex_checkbox.setChecked(False)
        self.tex_checkbox.toggled.connect(self.on_tex_check_changed)
        layout.addWidget(self.tex_checkbox)
        
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
        self.tex_checkbox.setText(tr("extract_tex"))
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
            tr("all_files"),
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
            
            if self.package_path.suffix.lower() == ".tex":
                tex_info = parse_tex_package(self.package_path)
                self.root_label.setText(f"{tr('root')}: -")
                self.files_label.setText(f"{tr('files')}: {len(tex_info.textures)} (TEX)")
                
                self.file_list.clear()
                for i, tex in enumerate(tex_info.textures):
                    self.file_list.addItem(f"  {tex.width}x{tex.height} ({tex.format.value}, {tex.data_size:,} {tr('bytes')})")
                
                self.tex_checkbox.setVisible(False)
            else:
                self.package_info = parse_package(self.package_path)
                self.root_label.setText(f"{tr('root')}: {self.package_info.root}")
                self.files_label.setText(f"{tr('files')}: {len(self.package_info.files)}")
                
                self.file_list.clear()
                for entry in self.package_info.files:
                    self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')})")
                
                self.tex_checkbox.setVisible(True)
                self.on_tex_check_changed(self.tex_checkbox.isChecked())
            
            self.extract_btn.setEnabled(True)
            self.status_label.setText("")
        except Exception as e:
            QMessageBox.critical(self, tr("error"), f"{tr('failed_to_parse')}\n{e}")
    
    def _get_tex_data(self, entry: FileEntry) -> bytes | None:
        """Extract .tex file data from the package."""
        if not self.package_path or not self.package_info:
            return None
        try:
            with open(self.package_path, "rb") as f:
                f.seek(self.package_info.data_offset + entry.offset)
                return f.read(entry.length)
        except Exception:
            return None
    
    def _preview_tex(self, tex_data: bytes) -> TexInfo | None:
        """Parse TEX data and return texture info."""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as tmp:
                tmp.write(tex_data)
                tmp.flush()
                return parse_tex_package(Path(tmp.name))
        except Exception:
            return None
    
    @Slot(bool)
    def on_tex_check_changed(self, checked: bool):
        if not self.package_path or not self.package_info:
            return
        if self.package_path.suffix.lower() == ".tex":
            return
            
        self.file_list.clear()
        
        if checked:
            for entry in self.package_info.files:
                if entry.name.lower().endswith(".tex"):
                    tex_data = self._get_tex_data(entry)
                    if tex_data:
                        tex_info = self._preview_tex(tex_data)
                        if tex_info:
                            self.file_list.addItem(f"[TEX] {entry.name}")
                            for i, tex in enumerate(tex_info.textures):
                                self.file_list.addItem(f"    {i}: {tex.width}x{tex.height} ({tex.format.value}, {tex.data_size:,} {tr('bytes')})")
                        else:
                            self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')}) [parse error]")
                    else:
                        self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')})")
                else:
                    self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')})")
        else:
            for entry in self.package_info.files:
                self.file_list.addItem(f"{entry.name} ({entry.length:,} {tr('bytes')})")
        
        self.files_label.setText(f"{tr('files')}: {self.file_list.count()}")
    
    @Slot("QListWidgetItem*")
    def on_file_double_clicked(self, item):
        if not self.package_path:
            return
        
        text = item.text()
        row = self.file_list.row(item)
        
        if self.package_path.suffix.lower() == ".tex":
            self._extract_single_tex_texture(text)
        else:
            self._extract_single_pkg_entry(text, row)
    
    def _extract_single_tex_texture(self, text: str):
        if not self.package_path:
            return
        try:
            import re
            match = re.search(r"(\d+)x(\d+)\s+\((\w+),\s+(\d+)", text)
            if not match:
                return
            width = int(match.group(1))
            height = int(match.group(2))
            fmt = match.group(3)
            
            tex_info = parse_tex_package(self.package_path)
            base_name = self.package_path.stem
            
            for tex in tex_info.textures:
                if tex.width == width and tex.height == height and tex.format.value == fmt:
                    output_path = self.output_dir / f"{base_name}_{tex.width}x{tex.height}.{tex.format.value}"
                    with open(output_path, "wb") as f:
                        f.write(tex.data)
                    self.status_label.setText(f"{tr('extracted')}: {output_path.name}")
                    self._ask_open_dir(output_path)
                    return
        except Exception as e:
            QMessageBox.critical(self, tr("error"), str(e))
    
    def _extract_single_pkg_entry(self, text: str, row: int):
        if not self.package_path or not self.package_info:
            return
        
        import re
        
        is_tex_header = text.startswith("[TEX]")
        
        if is_tex_header:
            tex_name = text.replace("[TEX] ", "")
            entry = next((e for e in self.package_info.files if e.name == tex_name), None)
            if entry:
                self._extract_tex_entry(entry)
        elif text.startswith("    ") and ": " in text:
            tex_entry = self._find_tex_entry_from_preview(row)
            if tex_entry:
                self._extract_single_texture_from_tex_entry(tex_entry[0], tex_entry[1], tex_entry[2])
        else:
            file_name = text.rsplit(" (", 1)[0]
            entry = next((e for e in self.package_info.files if e.name == file_name), None)
            if entry:
                self._extract_file_entry(entry)
    
    def _find_tex_entry_from_preview(self, row: int):
        if not self.package_info:
            return None
        
        tex_file_name = None
        for i in range(row, -1, -1):
            prev_item = self.file_list.item(i)
            if prev_item:
                prev_text = prev_item.text()
                if prev_text.startswith("[TEX]"):
                    tex_file_name = prev_text.replace("[TEX] ", "")
                    break
        
        if not tex_file_name:
            return None
        
        entry = next((e for e in self.package_info.files if e.name == tex_file_name), None)
        if not entry:
            return None
        
        tex_data = self._get_tex_data(entry)
        if not tex_data:
            return None
        
        curr_item = self.file_list.item(row)
        if not curr_item:
            return None
        curr_text = curr_item.text()
        
        import re
        tex_idx_match = re.match(r"\s+(\d+):", curr_text)
        if not tex_idx_match:
            return None
        tex_idx = int(tex_idx_match.group(1))
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as tmp:
            tmp.write(tex_data)
            tmp.flush()
            tex_info = parse_tex_package(Path(tmp.name))
        
        if tex_idx < len(tex_info.textures):
            return (tex_info, tex_idx, tex_file_name)
        return None
    
    def _extract_single_texture_from_tex_entry(self, tex_info: TexInfo, tex_idx: int, tex_file_name: str):
        if not self.package_path or not self.package_info:
            return
        try:
            tex = tex_info.textures[tex_idx]
            base_name = Path(tex_file_name).stem
            output_path = self.output_dir / f"{base_name}_{tex.width}x{tex.height}.{tex.format.value}"
            with open(output_path, "wb") as f:
                f.write(tex.data)
            self.status_label.setText(f"{tr('extracted')}: {output_path.name}")
            self._ask_open_dir(output_path)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), str(e))
    
    def _extract_file_entry(self, entry: FileEntry):
        if not self.package_path or not self.package_info:
            return
        try:
            with open(self.package_path, "rb") as f:
                f.seek(self.package_info.data_offset + entry.offset)
                data = f.read(entry.length)
            
            base_path = self.output_dir / self.package_info.root
            file_path = base_path / entry.name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as out_file:
                out_file.write(data)
            
            self.status_label.setText(f"{tr('extracted')}: {entry.name}")
            self._ask_open_dir(file_path)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), str(e))
    
    def _extract_tex_entry(self, entry: FileEntry):
        if not self.package_path or not self.package_info:
            return
        try:
            tex_data = self._get_tex_data(entry)
            if not tex_data:
                QMessageBox.critical(self, tr("error"), tr("failed_to_extract_tex"))
                return
            
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as tmp:
                tmp.write(tex_data)
                tmp.flush()
                tex_path = Path(tmp.name)
            
            tex_info = parse_tex_package(tex_path)
            base_path = self.output_dir / self.package_info.root
            tex_base = base_path / entry.name.replace(".tex", "")
            tex_base.parent.mkdir(parents=True, exist_ok=True)
            
            extracted = []
            for i, tex in enumerate(tex_info.textures):
                output_path = tex_base.parent / f"{tex_base.stem}_{tex.width}x{tex.height}.{tex.format.value}"
                with open(output_path, "wb") as f:
                    f.write(tex.data)
                extracted.append(output_path)
            
            self.status_label.setText(f"{tr('extracted')}: {entry.name} ({len(extracted)} textures)")
            self._ask_open_dir(tex_base.parent)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), str(e))
    
    def _ask_open_dir(self, path: Path):
        reply = QMessageBox.question(
            self,
            tr("extraction_complete"),
            f"{tr('open_output_dir')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
    
    @Slot()
    def extract(self):
        if not self.package_path:
            return
        
        self.extract_btn.setEnabled(False)
        
        extract_tex = self.tex_checkbox.isChecked() if self.tex_checkbox.isVisible() else False
        
        self.extraction_thread = ExtractionThread(self.package_path, self.output_dir, extract_tex)
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
