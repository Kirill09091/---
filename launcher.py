import sys
import os
import json
import subprocess
import psutil
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QLabel, QPushButton, QFileDialog,
                             QInputDialog, QMenu, QMessageBox, QStackedWidget,
                             QListWidget, QLineEdit)
from PyQt5.QtCore import Qt, QMimeData, QSize, QDir
from PyQt5.QtGui import QColor, QPalette, QDrag, QIcon, QPixmap
from PyQt5.QtWidgets import QAbstractItemView

# Класс для кнопки с возможностью перетаскивания
class DraggableProgramButton(QPushButton):
    def __init__(self, name, path, parent=None):
        super().__init__(name, parent)
        self.program_name = name
        self.program_path = path
        self.setToolTip(name)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.LeftButton:
            return

        mimeData = QMimeData()
        mimeData.setText(self.program_name)

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        
        drag.exec_(Qt.MoveAction)

# Класс для элементов списка программ
class ProgramListItem(QWidget):
    def __init__(self, program_info, section_name, parent=None):
        super().__init__(parent)
        self.program_info = program_info
        self.section_name = section_name
        self.setObjectName("program-list-item")
        
        item_layout = QHBoxLayout(self)
        item_layout.setContentsMargins(10, 5, 10, 5)

        self.program_button = DraggableProgramButton(program_info["name"], program_info["path"], self)
        self.program_button.setObjectName("program-list-button")
        
        item_layout.addWidget(self.program_button, 1)

        self.delete_button = QPushButton("X", self)
        self.delete_button.setObjectName("delete-button")
        self.delete_button.setFixedSize(QSize(30, 30))
        item_layout.addWidget(self.delete_button)

# Основной класс приложения-лаунчера
class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.running_processes = {}
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.resize(1000, 700)
        self.setWindowTitle('Зенитный-Нексус')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.offset = None

        # Настройка палитры для темной темы
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(20, 20, 20))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

        # Стили неоморфизма
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                font-family: "Segoe UI", sans-serif;
            }
            #main_frame {
                background-color: #2e2e2e;
                border-radius: 20px;
            }
            .title_bar {
                background-color: #2e2e2e;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
            .title_bar_button {
                background-color: #2e2e2e;
                border: none;
                color: #ffffff;
                font-size: 18px;
            }
            .title_bar_button:hover {
                color: #4a90e2;
            }
            QPushButton {
                background: #2e2e2e;
                color: white;
                border-radius: 12px;
                padding: 12px 24px;
                font-weight: bold;
                border: 2px solid #3e3e3e;
            }
            QPushButton:hover {
                background: #3a3a3a;
            }
            QPushButton:pressed {
            }
            QLineEdit {
                background-color: #2e2e2e;
                border-radius: 10px;
                border: 2px solid #3a3a3a;
                padding: 8px;
                color: #ffffff;
            }
            QFrame#nav_frame {
                background: #2e2e2e;
                border-radius: 15px;
            }
            #nav_frame QPushButton {
                background: #2e2e2e;
                border-radius: 8px;
                text-align: left;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: normal;
                color: #e0e0e0;
                border: none;
            }
            #nav_frame QPushButton:checked {
                background: #4a90e2;
                color: white;
                font-weight: bold;
            }
            #page_frame {
                background-color: #2e2e2e;
                border-radius: 15px;
            }
            .program-list-item {
                background-color: #3e3e3e;
                border-radius: 10px;
                margin-bottom: 8px;
            }
            .program-list-button {
                background-color: #3e3e3e;
                color: #e0e0e0;
                font-size: 14px;
                border: none;
                padding: 10px;
                text-align: left;
            }
            .program-list-button:hover {
                background-color: #4e4e4e;
            }
            .delete-button {
                background-color: #e74c3c;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                width: 30px;
                height: 30px;
            }
            .delete-button:hover {
                background-color: #c0392b;
            }
            QListWidget {
                background-color: #2e2e2e;
                border: 2px solid #3a3a3a;
                border-radius: 10px;
                color: #e0e0e0;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Панель заголовка
        self.title_bar = QWidget(self)
        self.title_bar.setObjectName("title_bar")
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(15, 0, 15, 0)
        self.title_label = QLabel("Зенитный-Нексус", self)
        self.title_bar_layout.addWidget(self.title_label)
        self.title_bar_layout.addStretch()
        self.minimize_button = QPushButton("—", self)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.close_button = QPushButton("X", self)
        self.close_button.clicked.connect(self.close)
        self.title_bar_layout.addWidget(self.minimize_button)
        self.title_bar_layout.addWidget(self.close_button)
        self.main_layout.addWidget(self.title_bar)
        
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("main_frame")
        self.main_layout.addWidget(self.main_frame)
        self.content_layout = QHBoxLayout(self.main_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.nav_frame = QFrame(self)
        self.nav_frame.setObjectName("nav_frame")
        self.nav_layout = QVBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(self.nav_frame, 1)

        self.sections_stack = QStackedWidget(self)
        self.content_layout.addWidget(self.sections_stack, 3)

        # Панель управления (поиск, сортировка)
        self.control_panel_layout = QHBoxLayout()
        
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self.filter_programs)
        self.control_panel_layout.addWidget(self.search_input)

        self.sort_name_button = QPushButton("Сортировать по имени", self)
        self.sort_name_button.clicked.connect(lambda: self.sort_programs("name"))
        self.control_panel_layout.addWidget(self.sort_name_button)
        
        self.sort_path_button = QPushButton("Сортировать по пути", self)
        self.sort_path_button.clicked.connect(lambda: self.sort_programs("path"))
        self.control_panel_layout.addWidget(self.sort_path_button)
        
        self.main_layout.addLayout(self.control_panel_layout)

        # Панель для кнопок управления
        self.control_buttons_layout = QHBoxLayout()
        self.main_layout.addLayout(self.control_buttons_layout)
        
        self.add_program_button = QPushButton("Добавить программу", self)
        self.add_program_button.clicked.connect(self.add_program)
        self.control_buttons_layout.addWidget(self.add_program_button)
        
        self.add_section_button = QPushButton("Добавить раздел", self)
        self.add_section_button.clicked.connect(self.add_section)
        self.control_buttons_layout.addWidget(self.add_section_button)

        self.remove_section_button = QPushButton("Удалить раздел", self)
        self.remove_section_button.clicked.connect(self.remove_section)
        self.control_buttons_layout.addWidget(self.remove_section_button)
        
        self.update_ui()
        self.update_running_processes_list()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() == Qt.LeftButton:
            x = event.globalX()
            y = event.globalY()
            self.move(x - self.offset.x(), y - self.offset.y())

    def mouseReleaseEvent(self, event):
        self.offset = None
    
    def load_settings(self):
        settings_file = self.get_settings_file_path()
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {
                "sections": {
                    "Программы": {"icon_path": "", "programs": []},
                    "Игры": {"icon_path": "", "programs": []}
                }
            }

    def save_settings(self):
        settings_file = self.get_settings_file_path()
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
    
    def get_settings_file_path(self):
        # Получаем путь к исполняемому файлу или текущему скрипту
        if getattr(sys, 'frozen', False):
            # Если приложение запущено как исполняемый файл
            return os.path.join(os.path.dirname(sys.executable), "settings.json")
        else:
            # Если запущено как скрипт Python
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

    def add_program(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать программу", "", "Executable Files (*.exe)")
        
        if file_path:
            program_name = os.path.basename(file_path).replace(".exe", "")
            
            section_names = list(self.data["sections"].keys())
            if not section_names:
                QMessageBox.warning(self, "Ошибка", "Сначала создайте раздел.")
                return

            section_name, ok = QInputDialog.getItem(self, "Выбор раздела", "Выберите раздел для программы:", section_names, 0, False)
            
            if ok and section_name:
                self.data["sections"][section_name]["programs"].append({
                    "name": program_name,
                    "path": file_path,
                    "run_as_admin": False
                })
                self.save_settings()
                self.update_ui()

    def add_section(self):
        section_name, ok = QInputDialog.getText(self, "Новый раздел", "Введите название для нового раздела:")
        
        if ok and section_name:
            if section_name not in self.data["sections"]:
                self.data["sections"][section_name] = {"icon_path": "", "programs": []}
                self.save_settings()
                self.update_ui()
            else:
                QMessageBox.warning(self, "Ошибка", "Раздел с таким именем уже существует.")

    def remove_section(self):
        section_names = list(self.data["sections"].keys())
        if not section_names:
            QMessageBox.warning(self, "Ошибка", "Нет разделов для удаления.")
            return

        section_name, ok = QInputDialog.getItem(self, "Удалить раздел", "Выберите раздел для удаления:", section_names, 0, False)
        
        if ok and section_name:
            reply = QMessageBox.question(self, "Удаление раздела", 
                                         f"Вы уверены, что хотите удалить раздел '{section_name}' и все его программы?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.data["sections"][section_name]
                self.save_settings()
                self.update_ui()

    def update_ui(self):
        while self.nav_layout.count():
            item = self.nav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        while self.sections_stack.count():
            widget = self.sections_stack.widget(0)
            self.sections_stack.removeWidget(widget)
            widget.deleteLater()
            
        first_section_name = None
        
        for section_name, section_data in self.data.get("sections", {}).items():
            if first_section_name is None:
                first_section_name = section_name
                
            nav_button = QPushButton(section_name, self)
            nav_button.setCheckable(True)
            self.nav_layout.addWidget(nav_button)
            
            page = QFrame(self)
            page.setObjectName("page_frame")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(20, 20, 20, 20)
            
            label = QLabel(section_name, page)
            label.setObjectName("section_label")
            page_layout.addWidget(label)
            
            program_list_layout = QVBoxLayout()
            page_layout.addLayout(program_list_layout)
            page_layout.addStretch(1)
            
            page.setAcceptDrops(True)
            page.dragEnterEvent = self.dragEnterEvent
            page.dropEvent = lambda e, s=section_name: self.dropEvent(e, s)
            
            self.sections_stack.addWidget(page)
            
            nav_button.clicked.connect(lambda checked, idx=self.sections_stack.count()-1: self.sections_stack.setCurrentIndex(idx))
            
            for program in section_data["programs"]:
                item = ProgramListItem(program, section_name, self)
                item.program_button.clicked.connect(lambda checked, path=program["path"], admin=program.get("run_as_admin", False): self.launch_program(path, admin))
                item.program_button.customContextMenuRequested.connect(
                    lambda pos, p=program, sec=section_name: self.show_program_context_menu(pos, p, sec)
                )
                item.delete_button.clicked.connect(lambda checked, sec_name=section_name, name=program["name"]: self.remove_program(sec_name, name))
                program_list_layout.addWidget(item)

        # Добавляем раздел с запущенными процессами
        nav_button = QPushButton("Запущенные программы", self)
        nav_button.setCheckable(True)
        self.nav_layout.addWidget(nav_button)
        
        running_page = QFrame(self)
        running_page.setObjectName("page_frame")
        running_layout = QVBoxLayout(running_page)
        running_layout.setContentsMargins(20, 20, 20, 20)
        
        running_label = QLabel("Запущенные программы", running_page)
        running_layout.addWidget(running_label)
        
        self.running_list_widget = QListWidget(running_page)
        self.running_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.running_list_widget.customContextMenuRequested.connect(self.show_running_context_menu)
        running_layout.addWidget(self.running_list_widget)
        
        self.sections_stack.addWidget(running_page)
        nav_button.clicked.connect(lambda checked, idx=self.sections_stack.count()-1: self.sections_stack.setCurrentIndex(idx))
        
        self.nav_layout.addStretch(1)
        
        if self.sections_stack.count() > 0:
            self.sections_stack.setCurrentIndex(0)
            if self.nav_layout.itemAt(0) and self.nav_layout.itemAt(0).widget():
                self.nav_layout.itemAt(0).widget().setChecked(True)

    def filter_programs(self, text):
        for i in range(self.sections_stack.count()):
            page = self.sections_stack.widget(i)
            # Пропускаем страницу с запущенными программами
            if page.children() and isinstance(page.children()[-1], QListWidget):
                continue
            
            list_layout = page.children()[-1]
            if not isinstance(list_layout, QVBoxLayout):
                continue
            
            for j in range(list_layout.count()):
                item_widget = list_layout.itemAt(j).widget()
                if item_widget and isinstance(item_widget, ProgramListItem):
                    name = item_widget.program_info.get("name", "").lower()
                    path = item_widget.program_info.get("path", "").lower()
                    if text.lower() in name or text.lower() in path:
                        item_widget.setVisible(True)
                    else:
                        item_widget.setVisible(False)
    
    def sort_programs(self, key):
        current_index = self.sections_stack.currentIndex()
        if current_index >= 0 and current_index < len(self.data["sections"]):
            section_name = list(self.data["sections"].keys())[current_index]
            programs = self.data["sections"][section_name]["programs"]
            programs.sort(key=lambda p: p.get(key, "").lower())
            self.save_settings()
            self.update_ui()
    
    def show_program_context_menu(self, pos, program, section_name):
        menu = QMenu(self)
        
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.remove_program(section_name, program["name"]))
        
        edit_action = menu.addAction("Изменить")
        edit_action.triggered.connect(lambda: self.edit_program(section_name, program))

        open_location_action = menu.addAction("Открыть расположение")
        open_location_action.triggered.connect(lambda: self.open_program_location(program["path"]))
        
        run_as_admin_action = menu.addAction("Запустить от имени администратора")
        run_as_admin_action.setCheckable(True)
        run_as_admin_action.setChecked(program.get("run_as_admin", False))
        run_as_admin_action.triggered.connect(lambda: self.toggle_run_as_admin(section_name, program))
        
        menu.exec_(self.mapToGlobal(pos))
    
    def show_running_context_menu(self, pos):
        item = self.running_list_widget.itemAt(pos)
        if not item:
            return
        
        process_name = item.text()
        pid = self.running_processes.get(process_name)
        if not pid:
            return

        menu = QMenu(self)
        kill_action = menu.addAction("Закрыть программу")
        kill_action.triggered.connect(lambda: self.kill_process(pid))
        
        menu.exec_(self.running_list_widget.mapToGlobal(pos))

    def edit_program(self, section_name, program):
        new_name, ok = QInputDialog.getText(self, "Изменить название", "Введите новое название программы:", text=program["name"])
        if ok and new_name:
            program["name"] = new_name
            self.save_settings()
            self.update_ui()

    def toggle_run_as_admin(self, section_name, program):
        program["run_as_admin"] = not program.get("run_as_admin", False)
        self.save_settings()
        self.update_ui()
        QMessageBox.information(self, "Настройки", f"Запуск '{program['name']}' от имени администратора: {'включен' if program['run_as_admin'] else 'выключен'}")

    def remove_program(self, section_name, program_name):
        reply = QMessageBox.question(self, "Удаление программы", 
                                     f"Вы уверены, что хотите удалить '{program_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.data["sections"][section_name]["programs"] = [
                p for p in self.data["sections"][section_name]["programs"] 
                if p["name"] != program_name
            ]
            self.save_settings()
            self.update_ui()

    def open_program_location(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден. Возможно, он был удален или перемещен.")
            return

        try:
            subprocess.Popen(['explorer', '/select,', path])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть расположение: {e}")

    def launch_program(self, path, run_as_admin=False):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден. Возможно, он был удален или перемещен.")
            return
            
        try:
            if run_as_admin:
                subprocess.Popen(['runas', '/user:Administrator', path])
            else:
                process = subprocess.Popen([path])
                self.running_processes[os.path.basename(path)] = process.pid
                self.update_running_processes_list()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить программу: {e}")

    def update_running_processes_list(self):
        self.running_list_widget.clear()
        
        # Обновляем список, удаляя завершенные процессы
        pids_to_check = list(self.running_processes.values())
        for pid in pids_to_check:
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    self.running_list_widget.addItem(p.name())
                else:
                    for name, p_id in list(self.running_processes.items()):
                        if p_id == pid:
                            del self.running_processes[name]
                            break
            except psutil.NoSuchProcess:
                for name, p_id in list(self.running_processes.items()):
                    if p_id == pid:
                        del self.running_processes[name]
                        break

    def kill_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            QMessageBox.information(self, "Успех", f"Процесс {p.name()} был успешно завершен.")
            self.update_running_processes_list()
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Ошибка", "Процесс уже не запущен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось завершить процесс: {e}")
            
    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e, new_section):
        program_name = e.mimeData().text()
        
        old_section = None
        program_to_move = None
        for section_name, section_data in self.data["sections"].items():
            for program in section_data["programs"]:
                if program["name"] == program_name:
                    old_section = section_name
                    program_to_move = program
                    self.data["sections"][old_section]["programs"].remove(program)
                    break
            if old_section:
                break
        
        if old_section and new_section:
            self.data["sections"][new_section]["programs"].append(program_to_move)
            self.save_settings()
            self.update_ui()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec_())
