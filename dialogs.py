"""Management dialogs using the same PyQt5 widgets as the Designer form."""
import sqlite3
from PyQt5 import QtCore, QtWidgets
from grading import GradePolicy


class SubjectsDialog(QtWidgets.QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.db = database
        self.subject_id = None
        self.setWindowTitle('Danh mục môn học — K10TIN')
        self.resize(540, 380)
        root = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Môn học', 'Số tín chỉ'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        root.addWidget(self.table)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit()
        self.credits = QtWidgets.QSpinBox()
        self.credits.setRange(1, 30)
        form.addRow('Tên môn:', self.name)
        form.addRow('Số tín chỉ:', self.credits)
        root.addLayout(form)
        buttons = QtWidgets.QHBoxLayout()
        for text, handler in [('Nhập mới', self.clear), ('Thêm', self.add), ('Sửa', self.update), ('Xóa', self.delete), ('Đóng', self.accept)]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        root.addLayout(buttons)
        self.table.itemSelectionChanged.connect(self.select)
        self.reload()

    def reload(self):
        self.table.setRowCount(0)
        for row, subject in enumerate(self.db.subjects()):
            self.table.insertRow(row)
            name = QtWidgets.QTableWidgetItem(subject['name'])
            name.setData(QtCore.Qt.UserRole, subject['id'])
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(subject['credits'])))
        self.clear()

    def clear(self):
        self.table.clearSelection()
        self.subject_id = None
        self.name.clear()
        self.credits.setValue(3)
        self.name.setFocus()

    def select(self):
        if not self.table.selectedItems():
            return
        row = self.table.currentRow()
        self.subject_id = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        self.name.setText(self.table.item(row, 0).text())
        self.credits.setValue(int(self.table.item(row, 1).text()))

    def save(self, subject_id):
        try:
            self.db.save_subject(self.name.text(), self.credits.value(), subject_id)
        except (ValueError, sqlite3.Error) as error:
            message = 'Tên môn đã tồn tại.' if isinstance(error, sqlite3.IntegrityError) else str(error)
            QtWidgets.QMessageBox.warning(self, 'Không lưu được môn học', message)
            return
        self.reload()

    def add(self):
        self.save(None)

    def update(self):
        if self.subject_id is None:
            QtWidgets.QMessageBox.information(self, 'Chọn môn học', 'Chọn một môn trong bảng để sửa.')
            return
        self.save(self.subject_id)

    def delete(self):
        if self.subject_id is None:
            return
        answer = QtWidgets.QMessageBox.question(self, 'Xóa môn học', f'Xóa môn “{self.name.text()}”?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        try:
            self.db.delete_subject(self.subject_id)
        except (ValueError, sqlite3.Error) as error:
            QtWidgets.QMessageBox.warning(self, 'Không xóa được môn học', str(error))
            return
        self.reload()


class PolicyDialog(QtWidgets.QDialog):
    def __init__(self, policy, parent=None):
        super().__init__(parent)
        self.result_policy = None
        self.setWindowTitle('Quy định tính điểm — K10TIN')
        self.resize(420, 430)
        root = QtWidgets.QVBoxLayout(self)
        notice = QtWidgets.QLabel('Nhập quy định thực tế của lớp. Các giá trị gợi ý chưa được áp dụng cho tới khi bấm Lưu.')
        notice.setWordWrap(True)
        root.addWidget(notice)
        form = QtWidgets.QFormLayout()
        self.fields = {}
        values = policy.to_dict() if policy else dict(regular_weight=20, midterm_weight=30, final_weight=50,
            course_digits=1, average_digits=2, excellent=9, good=8, fair=6.5, average=5, credit_weighted=True)
        for key, caption in [('regular_weight', 'TX (%):'), ('midterm_weight', 'Giữa kỳ (%):'), ('final_weight', 'Cuối kỳ (%):'),
                             ('course_digits', 'Chữ số lẻ điểm môn:'), ('average_digits', 'Chữ số lẻ điểm học kỳ:'),
                             ('excellent', 'Xuất sắc từ:'), ('good', 'Giỏi từ:'), ('fair', 'Khá từ:'), ('average', 'Trung bình từ:')]:
            if key.endswith('digits'):
                field = QtWidgets.QSpinBox(); field.setRange(0, 2)
            else:
                field = QtWidgets.QDoubleSpinBox(); field.setRange(0, 100 if key.endswith('weight') else 10); field.setDecimals(2)
            field.setValue(values[key])
            self.fields[key] = field
            form.addRow(caption, field)
        self.weighted = QtWidgets.QCheckBox('Tính điểm học kỳ theo số tín chỉ')
        self.weighted.setChecked(values['credit_weighted'])
        form.addRow(self.weighted)
        root.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText('Lưu quy định')
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText('Hủy')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def save(self):
        try:
            self.result_policy = GradePolicy(**{key: field.value() for key, field in self.fields.items()}, credit_weighted=self.weighted.isChecked())
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Quy định chưa hợp lệ', str(error))
            return
        self.accept()
