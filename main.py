"""Quản lý điểm K10TIN học kỳ 5 với SQLite."""

import sys
import sqlite3
import textwrap
from collections import Counter
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets, uic

import resources_rc  # noqa: F401 - đăng ký hình ảnh cho file .ui


from database import Database, DEFAULT_DB, CLASS_NAME, SEMESTER
from grading import CATEGORIES, COLORS, search_key
from reports import export_workbook
from login import LoginDialog


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, database_path=DEFAULT_DB):
        super().__init__()
        uic.loadUi(str(Path(__file__).with_name("main.ui")), self)
        self.mainTabs.setCurrentWidget(self.entryTab)
        self.db = Database(database_path)
        self.policy = self.db.policy()
        self.selected_code = None
        self.form_mode = 'new'
        self.setWindowTitle(f'Quản lý điểm sinh viên - Lớp {CLASS_NAME} - Học kỳ {SEMESTER}')
        self.subtitleLabel.setText(f'Lớp {CLASS_NAME}  |  Học kỳ {SEMESTER}')
        self.classEdit.setText(CLASS_NAME)
        self.classEdit.setReadOnly(True)
        validator = QtGui.QDoubleValidator(0, 100, 2, self.conductEdit)
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        validator.setLocale(QtCore.QLocale.c())
        self.conductEdit.setValidator(validator)
        self.conductEdit.setToolTip('Điểm rèn luyện học kỳ từ 0 đến 100; để trống nếu chưa có.')
        self.midtermScoreSpinLabel.setText('Điểm định kỳ:')
        self.totalCaption.setToolTip('(Điểm thường xuyên + 2 × điểm định kỳ + 3 × điểm cuối kỳ) / 6; làm tròn 1 chữ số thập phân.')
        self.subjectCombo.clear()
        self.filterSubjectCombo.clear()
        for subject in self.db.subjects():
            self.subjectCombo.addItem(subject['name'], subject['id'])
            self.filterSubjectCombo.addItem(subject['name'], subject['id'])
        self._score_editors = {}
        for spin in self.score_spins():
            spin.setRange(0, 10)
            spin.setDecimals(2)
            spin.setSingleStep(0.1)
            spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            spin.setSpecialValueText('')
            spin.setFocusPolicy(QtCore.Qt.StrongFocus)
            spin.setToolTip('Gõ điểm từ 0 đến 10, tối đa 2 chữ số thập phân, ví dụ 9.25. Dùng Tab để chuyển ô.')
            self._score_editors[spin.lineEdit()] = spin
            spin.installEventFilter(self)
            spin.lineEdit().installEventFilter(self)
            spin.valueChanged.connect(self.update_preview)
        self.studentsTable.setColumnCount(8)
        self.studentsTable.setHorizontalHeaderLabels(['STT', 'Mã SV', 'Họ tên', 'Điểm\nthường xuyên', 'Điểm\nđịnh kỳ', 'Điểm\ncuối kỳ', 'Điểm TBC\nmôn học', 'Xếp loại'])
        self.studentsTable.horizontalHeader().setMinimumHeight(52)
        self.studentsTable.horizontalHeader().setStretchLastSection(False)
        self.studentsTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.studentsTable.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.studentsTable.setColumnWidth(0, 38)
        for column in (1, 3, 4, 5, 6):
            self.studentsTable.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        self.studentsTable.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.studentsTable.verticalHeader().setDefaultSectionSize(32)
        self.setup_summary()
        self.searchEdit.textChanged.connect(self.filter_students)
        self.studentsTable.itemSelectionChanged.connect(self.select_student)
        self.refreshButton.clicked.connect(self.refresh)
        self.closeButton.clicked.connect(self.close)
        self.subjectCombo.currentIndexChanged.connect(self.filterSubjectCombo.setCurrentIndex)
        self.filterSubjectCombo.currentIndexChanged.connect(self.subjectCombo.setCurrentIndex)
        self.addButton.clicked.connect(self.add_record)
        self.editButton.clicked.connect(self.edit_record)
        self.deleteButton.clicked.connect(self.delete_record)
        self.exportButton.clicked.connect(lambda: self.export_table(self.studentsTable, 'Điểm môn ' + self.subjectCombo.currentText()))
        self.subjectCombo.currentIndexChanged.connect(self.reload_data)
        self.newButton = QtWidgets.QPushButton('Nhập sinh viên mới')
        self.studentCardLayout.addWidget(self.newButton)
        self.newButton.clicked.connect(self.clear_form)
        self.reload_data()
        self.fit_to_screen()
        self.adjust_summary_layout()
        QtCore.QTimer.singleShot(0, self.adjust_summary_layout)

    def setup_summary(self):
        # Report an outdated Designer file instead of silently showing an old UI.
        dashboard_controls = (
            "summarySearchEdit", "summarySearchButton",
            "summaryRefreshButton", "summaryExportButton", "summaryBottomLayout",
            "summaryActionsCard", "summaryActionsCardBodyLayout",
        )
        self._has_summary_dashboard = all(hasattr(self, name) for name in dashboard_controls)
        self._summary_compact = None
        header = self.summaryTable.horizontalHeader()
        self.summaryTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        header.setStretchLastSection(False)
        if not self._has_summary_dashboard:
            raise RuntimeError(
                "main.ui đang là bản cũ hoặc thiếu các khung của tab tổng hợp. "
                "Đóng file trong Qt Designer, rồi chạy "
                r".\.venv\Scripts\python.exe tools\restore_ui.py "
                "để khôi phục bản đã kiểm tra."
            )
        header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.summaryBottomLayout.setAlignment(QtCore.Qt.AlignTop)
        self.summaryBottomLayout.setRowStretch(0, 0)
        self.summaryBottomLayout.setRowStretch(1, 0)
        self.statisticsCard.setMinimumHeight(0)
        self.summaryActionsCard.setMinimumHeight(0)
        self.summaryActionsCard.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        for index in (0, self.summaryActionsCardBodyLayout.count() - 1):
            self.summaryActionsCardBodyLayout.itemAt(index).spacerItem().changeSize(
                0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.summaryActionsCardBodyLayout.invalidate()
        self.summaryActionsCardHeader.hide()
        self.summaryActionsCard.setStyleSheet('QFrame#summaryActionsCard { background: transparent; border: none; }')
        self.statisticsBodyLayout.addWidget(self.resultsChart, 0, 0, 1, 2, QtCore.Qt.AlignHCenter)
        self.totalStudentsCard.hide()
        self.statisticsBodyLayout.addWidget(self.resultsLegend, 1, 0, 1, 2)
        self.resultsChart.setFixedSize(150, 150)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setFixedHeight(38)
        self.summaryTable.verticalHeader().setDefaultSectionSize(26)
        self.summarySearchEdit.textChanged.connect(self.filter_summary_students)
        self.summarySearchEdit.returnPressed.connect(self.search_summary)
        self.summarySearchButton.clicked.connect(self.search_summary)
        self.summaryRefreshButton.clicked.connect(self.refresh_summary)
        self.summaryExportButton.clicked.connect(lambda: self.export_table(self.summaryTable, 'Bảng điểm tổng hợp'))
        self.mainTabs.currentChanged.connect(lambda: QtCore.QTimer.singleShot(0, self.adjust_summary_layout))
        self.summaryTable.viewport().installEventFilter(self)
        self.missingLegendLabel = QtWidgets.QLabel()
        missing_swatch = QtWidgets.QLabel()
        missing_swatch.setFixedSize(13, 13)
        missing_swatch.setStyleSheet('background: #bbc3cc; border-radius: 3px;')
        self.resultsLegendLayout.addWidget(missing_swatch, 5, 0)
        self.resultsLegendLayout.addWidget(self.missingLegendLabel, 5, 1)
        for name in ('excellent', 'good', 'fair', 'average', 'weak', 'missing'):
            label = getattr(self, name + 'LegendLabel')
            label.setWordWrap(True)
            label.setMinimumWidth(0)
        self._summary_compact = None

    def filter_summary_students(self, text):
        keyword = search_key(text.strip())
        for row in range(self.summaryTable.rowCount()):
            value = " ".join(self.summaryTable.item(row, column).text() for column in (1, 2))
            self.summaryTable.setRowHidden(row, keyword not in search_key(value))

    def search_summary(self):
        self.filter_summary_students(self.summarySearchEdit.text())

    def refresh_summary(self):
        self.summarySearchEdit.clear()
        self.reload_data()

    def resize_summary_columns(self):
        for column in range(self.summaryTable.columnCount()):
            self.summaryTable.setColumnWidth(column, 110 if column >= 3 else (38 if column == 0 else 90))
        self.summaryTable.setColumnWidth(2, 170)
        self.summaryTable.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.summaryTable.horizontalHeader().setFixedHeight(72)

    def adjust_summary_layout(self):
        if not self._has_summary_dashboard:
            return
        self.resize_summary_columns()

    def eventFilter(self, obj, event):
        score_controls = getattr(self, '_score_editors', {})
        if obj in score_controls or obj in score_controls.values():
            if event.type() == QtCore.QEvent.Wheel:
                return True
            if event.type() == QtCore.QEvent.KeyPress and event.key() in (
                    QtCore.Qt.Key_Up, QtCore.Qt.Key_Down,
                    QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown):
                return True
        if event.type() == QtCore.QEvent.FocusIn:
            spin = getattr(self, '_score_editors', {}).get(obj)
            if spin is not None and not spin.isReadOnly():
                QtCore.QTimer.singleShot(0, spin.selectAll)
        if event.type() == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
            spin = score_controls.get(obj)
            if spin is not None and not spin.isReadOnly():
                QtCore.QTimer.singleShot(0, spin.selectAll)
        if event.type() == QtCore.QEvent.Resize and hasattr(self, "summaryTable"):
            if obj is self.summaryTable.viewport():
                self.resize_summary_columns()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_summary_compact"):
            self.adjust_summary_layout()

    def fit_to_screen(self):
        screen = self.screen() or QtWidgets.QApplication.primaryScreen()
        available = screen.availableGeometry()
        # Leave room for the title bar, window borders and taskbar.
        max_width = max(1, available.width() - 40)
        max_height = max(1, available.height() - 64)
        self.setMinimumSize(min(860, max_width), min(480, max_height))
        self.resize(min(1160, max_width), min(640, max_height))
        self.move(
            available.x() + (available.width() - self.width()) // 2,
            available.y() + max(8, (available.height() - self.height() - 32) // 2),
        )

    def filter_students(self, text):
        keyword = search_key(text.strip())
        for row in range(self.studentsTable.rowCount()):
            value = " ".join(self.studentsTable.item(row, col).text() for col in (1, 2))
            self.studentsTable.setRowHidden(row, keyword not in search_key(value))
        row = self.studentsTable.currentRow()
        if row >= 0 and self.studentsTable.isRowHidden(row):
            self.clear_form()

    def score_spins(self):
        return (self.regularScoreSpin, self.midtermScoreSpin, self.finalScoreSpin)

    def set_form_mode(self, mode):
        self.form_mode = mode
        editable = mode in ('new', 'edit')
        self.studentIdEdit.setReadOnly(not editable)
        self.fullNameEdit.setReadOnly(not editable)
        self.conductEdit.setReadOnly(not editable)
        for spin in self.score_spins():
            spin.setReadOnly(not editable)
        self.editButton.setText('Xác nhận' if mode == 'edit' else 'Sửa điểm')
        self.editButton.setProperty('confirming', mode == 'edit')
        self.editButton.style().unpolish(self.editButton)
        self.editButton.style().polish(self.editButton)
        self.editButton.update()
        self.editButton.setEnabled(mode != 'new')
        self.addButton.setEnabled(mode == 'new')
        self.deleteButton.setEnabled(mode == 'view')
        # Keep the student and subject fixed until confirmation or starting a new student.
        for control in (self.studentsTable, self.subjectCombo, self.filterSubjectCombo,
                        self.searchEdit, self.refreshButton, self.summaryRefreshButton):
            control.setEnabled(mode != 'edit')

    def clear_form(self):
        self.studentsTable.clearSelection()
        self.selected_code = None
        self.studentIdEdit.setText(self.db.next_student_code())
        self.fullNameEdit.clear()
        self.conductEdit.clear()
        for spin in self.score_spins():
            spin.setValue(0)
        self.set_form_mode('new')
        self.update_preview()
        self.fullNameEdit.setFocus()

    def select_student(self):
        if not self.studentsTable.selectedItems():
            return
        row = self.studentsTable.currentRow()
        self.selected_code = self.studentsTable.item(row, 1).text()
        self.studentIdEdit.setText(self.selected_code)
        self.fullNameEdit.setText(self.studentsTable.item(row, 2).text())
        conduct = self.db.conduct_score(self.selected_code)
        self.conductEdit.setText('' if conduct is None else f'{conduct:g}')
        grade = self.db.grade(self.selected_code, self.subjectCombo.currentData())
        for spin, key in zip(self.score_spins(), ('regular', 'midterm', 'final')):
            spin.setValue(grade[key] if grade else 0)
        self.set_form_mode('view')
        self.update_preview()

    def update_preview(self):
        values = [spin.value() for spin in self.score_spins()]
        total = self.policy.course_score(*values)
        self.totalScoreLabel.setText('—' if total is None else f'{total:.1f}')
        self.totalScoreLabel.setToolTip(self.policy.classify(total))

    def form_scores(self):
        for spin in self.score_spins():
            if not spin.hasAcceptableInput():
                raise ValueError('Điểm phải là số từ 0 đến 10.')
            spin.interpretText()
        values = tuple(spin.value() for spin in self.score_spins())
        return values

    def save_record(self, editing):
        if self.form_mode != ('edit' if editing else 'new'):
            return
        if editing and not self.selected_code:
            QtWidgets.QMessageBox.information(self, 'Chọn sinh viên', 'Chọn sinh viên trong bảng để sửa.')
            return
        try:
            conduct_text = self.conductEdit.text().strip()
            if conduct_text and not self.conductEdit.hasAcceptableInput():
                raise ValueError('Điểm rèn luyện phải từ 0 đến 100.')
            conduct = float(conduct_text) if conduct_text else None
            args = (self.studentIdEdit.text(), self.fullNameEdit.text(), self.subjectCombo.currentData(), self.form_scores(), conduct)
            code = self.db.update_record(self.selected_code, *args) if editing else self.db.add_record(*args)
        except (ValueError, sqlite3.Error) as error:
            QtWidgets.QMessageBox.warning(self, 'Không lưu được', str(error))
            return
        self.reload_data(code)
        self.statusBar().showMessage('Đã lưu vào SQLite.', 4000)

    def add_record(self):
        self.save_record(False)

    def edit_record(self):
        if not self.selected_code:
            return
        if self.form_mode == 'view':
            self.set_form_mode('edit')
            self.regularScoreSpin.setFocus()
            self.regularScoreSpin.selectAll()
        elif self.form_mode == 'edit':
            self.save_record(True)

    def delete_record(self):
        if not self.selected_code:
            return
        code = self.selected_code
        choice = QtWidgets.QMessageBox(self)
        choice.setWindowTitle('Xóa dữ liệu')
        choice.setText(f'Chọn dữ liệu cần xóa của {code}:')
        grade_button = choice.addButton('Điểm môn đang chọn', QtWidgets.QMessageBox.DestructiveRole)
        student_button = choice.addButton('Sinh viên và toàn bộ điểm', QtWidgets.QMessageBox.DestructiveRole)
        choice.addButton('Hủy', QtWidgets.QMessageBox.RejectRole)
        choice.exec_()
        try:
            if choice.clickedButton() == grade_button:
                self.db.delete_grade(code, self.subjectCombo.currentData())
            elif choice.clickedButton() == student_button:
                self.db.delete_student(code)
            else:
                return
        except sqlite3.Error as error:
            QtWidgets.QMessageBox.warning(self, 'Không xóa được', str(error))
            return
        self.reload_data()

    def fill_table(self, table, rows):
        table.setSortingEnabled(False)
        table.blockSignals(True)
        table.setRowCount(0)
        for row_number, values in enumerate(rows):
            table.insertRow(row_number)
            for column, value in enumerate(values):
                if value is None:
                    text = '—'
                elif table is self.studentsTable and column in (3, 4, 5):
                    text = f'{value:.2f}'
                else:
                    text = f'{value:.1f}' if isinstance(value, float) else str(value)
                item = QtWidgets.QTableWidgetItem(text)
                item.setData(QtCore.Qt.UserRole, value)
                item.setToolTip(text)
                if ((table is self.studentsTable and 3 <= column <= 6) or
                        (table is self.summaryTable and 3 <= column < len(values) - 1)):
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                if value in CATEGORIES:
                    item.setBackground(QtGui.QColor(COLORS[CATEGORIES.index(value)]))
                table.setItem(row_number, column, item)
        table.blockSignals(False)

    def reload_data(self, code=None):
        if not isinstance(code, str):
            code = self.selected_code
        rows = []
        for number, student in enumerate(self.db.grade_rows(self.subjectCombo.currentData()), 1):
            scores = [student[key] for key in ('regular', 'midterm', 'final')]
            total = self.policy.course_score(*scores)
            rows.append([number, student['code'], student['name'], *scores, total, self.policy.classify(total)])
        self.fill_table(self.studentsTable, rows)
        subjects = self.db.subjects()
        headers = ['STT', 'Mã SV', 'Họ tên', *['\n'.join(textwrap.wrap(s['name'], 12)) for s in subjects], 'Điểm TBC\nhọc kỳ', 'Điểm rèn\nluyện', 'Xếp loại']
        self.summaryTable.setColumnCount(len(headers))
        self.summaryTable.setHorizontalHeaderLabels(headers)
        data = self.db.summary(self.policy)
        self.fill_table(self.summaryTable, [[n, s['code'], s['name'], *s['scores'], s['average'], s['conduct'], s['classification']] for n, s in enumerate(data, 1)])
        self.totalStudentsLabel.setText(str(len(data)))
        self.update_statistics(data)
        self.clear_form()
        self.filter_students(self.searchEdit.text())
        self.filter_summary_students(self.summarySearchEdit.text())
        for row, values in enumerate(rows):
            if values[1] == code and not self.studentsTable.isRowHidden(row):
                self.studentsTable.selectRow(row)
                self.select_student()
                break
        self.resize_summary_columns()

    def update_statistics(self, data):
        counts = Counter(row['classification'] for row in data)
        total = len(data)
        for name, label in zip(('excellent', 'good', 'fair', 'average', 'weak'), CATEGORIES):
            count = counts[label]
            getattr(self, name + 'LegendLabel').setText(f'{label}: {count} ({count / total * 100 if total else 0:.1f}%)')
        missing = counts['Chưa đủ điểm']
        self.totalStudentsCaption.setText('Tổng sinh viên')
        self.missingLegendLabel.setText(f'Chưa đủ điểm: {missing}')
        pixmap = QtGui.QPixmap(180, 180)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        start = 90 * 16
        for category, color in zip(CATEGORIES, COLORS):
            span = round(360 * 16 * counts[category] / total) if total else 360 * 16
            painter.setBrush(QtGui.QColor(color if total else '#bbc3cc'))
            painter.drawPie(5, 5, 170, 170, start, span)
            start += span
            if not total:
                break
        painter.setBrush(QtGui.QColor('white'))
        painter.drawEllipse(40, 40, 100, 100)
        painter.setPen(QtGui.QColor('#333333'))
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, str(total) + ' SV')
        painter.end()
        self.resultsChart.setPixmap(pixmap)
        self.resultsChart.setToolTip(' | '.join(f'{label}: {counts[label]}' for label in CATEGORIES))

    def refresh(self):
        self.searchEdit.clear()
        self.reload_data()

    def export_table(self, table, title):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Xuất bảng điểm', 'Bang_diem_K10TIN_HK5.xlsx', 'Excel (*.xlsx)')
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        headers = [table.horizontalHeaderItem(c).text().replace('\n', ' ') for c in range(table.columnCount())]
        rows = [[table.item(r, c).data(QtCore.Qt.UserRole) for c in range(table.columnCount())]
                for r in range(table.rowCount()) if not table.isRowHidden(r)]
        try:
            export_workbook(path, title + ' — K10TIN — Học kỳ 5', headers, rows)
        except (OSError, ValueError) as error:
            QtWidgets.QMessageBox.warning(self, 'Không xuất được Excel', str(error))
            return
        self.statusBar().showMessage('Đã xuất Excel: ' + path, 6000)

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)


if __name__ == "__main__":
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    login = LoginDialog()
    if login.exec_() != QtWidgets.QDialog.Accepted:
        sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
