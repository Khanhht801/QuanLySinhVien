import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtTest import QTest

from database import Database, SUBJECT_NAMES
from grading import GradePolicy
from main import MainWindow


class GradingTests(unittest.TestCase):
    def test_conduct_is_per_semester_and_survives_student_code_change(self):
        db = Database(':memory:')
        subjects = db.subjects()
        db.add_record('SV001', 'Nguyễn Văn An', subjects[0]['id'], (8, 7, 9), 92.5)
        db.add_record('SV001', 'Nguyễn Văn An', subjects[1]['id'], (8, 7, 9))
        self.assertEqual(db.conduct_score('SV001'), 92.5)
        db.update_record('SV001', 'SV002', 'Nguyễn Văn An', subjects[0]['id'], (8, 7, 9))
        self.assertEqual(db.conduct_score('SV002'), 92.5)
        with self.assertRaises(ValueError):
            db.update_record('SV002', 'SV002', 'Nguyễn Văn An', subjects[0]['id'], (8, 7, 9), 101)
        self.assertEqual(db.conduct_score('SV002'), 92.5)
        db.delete_student('SV002')
        self.assertEqual(db.connection.execute('SELECT count(*) FROM conduct_scores').fetchone()[0], 0)
        db.close()

    def test_formula_and_boundaries(self):
        policy = GradePolicy()
        self.assertEqual(policy.course_score(8, 7, 9), 8.2)
        self.assertEqual(policy.course_score(0, 0, 1), 0.5)
        for score, expected in [(0, 'Kém'), (3.9, 'Kém'), (4, 'Trung bình yếu'),
                                (5.4, 'Trung bình yếu'), (5.5, 'Trung bình'),
                                (6.9, 'Trung bình'), (7, 'Khá'), (8.4, 'Khá'),
                                (8.5, 'Giỏi'), (10, 'Giỏi'), (None, 'Chưa đủ điểm')]:
            self.assertEqual(policy.classify(score), expected)
        for score in [-1, 11, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                policy.course_score(score, 5, 5)

    def test_persistence_transactions_and_semester(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite3'
            db = Database(path)
            self.assertEqual(tuple(s['name'] for s in db.subjects()), SUBJECT_NAMES)
            subjects = db.subjects()
            db.add_record('sv001', 'Nguyễn Văn An', subjects[0]['id'], (8, 7, 9))
            self.assertIsNone(db.summary(db.policy())[0]['average'])
            for subject in subjects[1:]:
                db.add_record('SV001', 'Nguyễn Văn An', subject['id'], (8, 8, 8))
            self.assertEqual(db.summary(db.policy())[0]['average'], 8)
            with self.assertRaises(sqlite3.IntegrityError):
                db.update_record('SV001', 'SV002', 'Tên khác', 99999, (1, 2, 3))
            self.assertIsNotNone(db.student('SV001'))
            self.assertIsNone(db.student('SV002'))
            db.update_record('SV001', 'SV002', 'Nguyễn Văn An', subjects[0]['id'], (9, 9, 9))
            self.assertEqual(db.grade('SV002', subjects[0]['id'])['semester'], 5)
            db.close()
            db = Database(path)
            self.assertEqual(db.grade('SV002', subjects[0]['id'])['final'], 9)
            db.delete_grade('SV002', subjects[0]['id'])
            self.assertIsNone(db.summary(db.policy())[0]['average'])
            db.delete_student('SV002')
            self.assertEqual(db.connection.execute('SELECT count(*) FROM grades').fetchone()[0], 0)
            db.close()


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_summary_dashboard_layout(self):
        window = MainWindow(':memory:')
        window.show()
        window.mainTabs.setCurrentWidget(window.summaryTab)
        for width in (860, 1160, 1600):
            window.resize(width, 800)
            self.app.processEvents()
            self.assertLessEqual(window.summaryContent.width(), window.summaryScroll.viewport().width())
            self.assertLess(window.summaryBottom.x(), window.summaryGradesCard.x())
            self.assertLess(window.statisticsCard.y(), window.summaryActionsCard.y())
            self.assertIsNone(window.findChild(QtWidgets.QWidget, 'subjectsCard'))
            self.assertTrue(window.summaryActionsCardHeader.isHidden())
            self.assertTrue(window.totalStudentsCard.isHidden())
            self.assertEqual(window.summaryTable.verticalScrollBarPolicy(), QtCore.Qt.ScrollBarAlwaysOn)
        subject = window.db.subjects()[0]['id']
        for number in range(50):
            window.db.add_record(f'SV{number:03}', f'Sinh viên {number}', subject, (8, 8, 8))
        window.reload_data()
        self.app.processEvents()
        self.assertGreater(window.summaryTable.verticalScrollBar().maximum(), 0)
        window.summaryTable.verticalScrollBar().setValue(window.summaryTable.verticalScrollBar().maximum())
        self.assertEqual(window.summaryTable.item(49, 1).text(), 'SV049')
        window.close()

    def test_score_inputs_ignore_wheel_and_increment_keys(self):
        window = MainWindow(':memory:')
        window.show()
        window.studentIdEdit.setText('SV001')
        window.fullNameEdit.setText('Nguyễn Văn An')
        for mode in ('new', 'edit'):
            if mode == 'edit':
                window.addButton.click()
                window.editButton.click()
            for spin in window.score_spins():
                spin.setValue(9.25)
                spin.setFocus()
                self.app.processEvents()
                for target in (spin, spin.lineEdit()):
                    wheel = QtGui.QWheelEvent(QtCore.QPointF(5, 5), QtCore.QPointF(5, 5),
                                              QtCore.QPoint(), QtCore.QPoint(0, 120),
                                              QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
                                              QtCore.Qt.NoScrollPhase, False)
                    QtWidgets.QApplication.sendEvent(target, wheel)
                    QTest.keyClick(target, QtCore.Qt.Key_Up)
                    QTest.keyClick(target, QtCore.Qt.Key_Down)
                    self.assertEqual(spin.value(), 9.25)
                spin.selectAll()
                QTest.keyClicks(spin.lineEdit(), '8.15')
                self.assertEqual(spin.value(), 8.15)
        window.close()

    def test_click_score_selects_value_for_typing(self):
        window = MainWindow(':memory:')
        window.show()
        self.app.processEvents()
        for spin in window.score_spins():
            spin.setValue(0)
            QTest.mouseClick(spin.lineEdit(), QtCore.Qt.LeftButton)
            self.app.processEvents()
            QTest.keyClicks(spin.lineEdit(), '9.25')
            self.assertEqual(spin.value(), 9.25)
            QTest.mouseClick(spin.lineEdit(), QtCore.Qt.LeftButton)
            self.app.processEvents()
            QTest.keyClicks(spin.lineEdit(), '8.15')
            self.assertEqual(spin.value(), 8.15)
        window.close()

    def test_conduct_score_save_edit_switch_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite3'
            window = MainWindow(path)
            self.assertEqual(window.conductLabel.text(), 'Điểm rèn luyện:')
            self.assertEqual(window.conductEdit.placeholderText(), '0–100')
            window.studentIdEdit.setText('SV001')
            window.fullNameEdit.setText('Nguyễn Văn An')
            window.conductEdit.setText('92.5')
            window.addButton.click()
            self.assertEqual(window.studentsTable.columnCount(), 8)
            self.assertEqual(window.totalCaption.text(), 'Điểm TBC môn học:')
            self.assertEqual(window.studentsTable.horizontalHeaderItem(6).text(), 'Điểm TBC\nmôn học')
            self.assertEqual(window.summaryTable.horizontalHeaderItem(8).text(), 'Điểm TBC\nhọc kỳ')
            self.assertEqual(window.summaryTable.horizontalHeaderItem(9).text(), 'Điểm rèn\nluyện')
            self.assertEqual(window.summaryTable.item(0, 9).text(), '92.5')
            for column in range(3, 7):
                self.assertEqual(window.studentsTable.item(0, column).textAlignment(), int(QtCore.Qt.AlignCenter))
            for column in range(3, 10):
                self.assertEqual(window.summaryTable.item(0, column).textAlignment(), int(QtCore.Qt.AlignCenter))
            window.filterSubjectCombo.setCurrentIndex(1)
            self.assertEqual(window.conductEdit.text(), '92.5')
            window.editButton.click()
            window.conductEdit.setText('85')
            window.editButton.click()
            output = Path(directory) / 'summary.xlsx'
            with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(output), '')):
                window.summaryExportButton.click()
            workbook = load_workbook(output)
            self.assertEqual(workbook.active.cell(3, 9).value, 'Điểm TBC học kỳ')
            self.assertEqual(workbook.active.cell(3, 10).value, 'Điểm rèn luyện')
            self.assertEqual(workbook.active.cell(4, 10).value, 85)
            workbook.close()
            window.close()
            window = MainWindow(path)
            window.studentsTable.selectRow(0)
            self.assertEqual(window.conductEdit.text(), '85')
            window.editButton.click()
            window.conductEdit.clear()
            window.editButton.click()
            self.assertEqual(window.summaryTable.item(0, 9).text(), '—')
            window.close()

    def test_enter_and_reopen_decimal_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite3'
            window = MainWindow(path)
            window.show()
            window.studentIdEdit.setText('SV001')
            window.fullNameEdit.setText('Nguyễn Văn An')
            for spin, text in zip(window.score_spins(), ('9.25', '9.00', '8.15')):
                self.assertEqual(spin.buttonSymbols(), QtWidgets.QAbstractSpinBox.NoButtons)
                self.assertEqual(spin.singleStep(), 0.1)
                spin.setFocus()
                self.app.processEvents()
                spin.selectAll()
                QTest.keyClicks(spin.lineEdit(), text)
                self.assertTrue(spin.hasAcceptableInput())
            window.addButton.click()
            self.assertEqual([window.studentsTable.item(0, col).text() for col in (3, 4, 5)],
                             ['9.25', '9.00', '8.15'])
            window.close()
            window = MainWindow(path)
            window.studentsTable.selectRow(0)
            self.assertEqual([spin.value() for spin in window.score_spins()], [9.25, 9.0, 8.15])
            self.assertEqual(window.midtermScoreSpin.text(), '9.00')
            window.editButton.click()
            self.assertTrue(all(spin.buttonSymbols() == QtWidgets.QAbstractSpinBox.NoButtons
                                for spin in window.score_spins()))
            window.close()

    def test_buttons_subject_switch_search_export_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / 'test.sqlite3'
            window = MainWindow(database_path)
            self.assertEqual([spin.value() for spin in window.score_spins()], [0, 0, 0])
            window.studentIdEdit.setText('SV001')
            window.fullNameEdit.setText('Nguyễn Văn An')
            for spin, value in zip(window.score_spins(), (8, 7, 9)):
                spin.setValue(value)
            window.addButton.click()
            self.assertEqual(window.studentsTable.rowCount(), 1)
            self.assertEqual(window.totalScoreLabel.text(), '8.2')
            self.assertTrue(window.finalScoreSpin.isReadOnly())
            self.assertTrue(window.fullNameEdit.isReadOnly())
            self.assertFalse(window.addButton.isEnabled())
            window.editButton.click()
            self.assertEqual(window.editButton.text(), 'Xác nhận')
            self.assertFalse(window.finalScoreSpin.isReadOnly())
            self.assertFalse(window.subjectCombo.isEnabled())
            window.finalScoreSpin.setValue(10)
            self.assertEqual(window.db.grade('SV001', window.subjectCombo.currentData())['final'], 9)
            window.editButton.click()
            self.assertEqual(window.db.grade('SV001', window.subjectCombo.currentData())['final'], 10)
            self.assertTrue(window.finalScoreSpin.isReadOnly())
            self.assertEqual(window.editButton.text(), 'Sửa điểm')
            self.assertTrue(window.subjectCombo.isEnabled())
            window.filterSubjectCombo.setCurrentIndex(1)
            self.assertEqual(window.subjectCombo.currentIndex(), 1)
            self.assertEqual(window.regularScoreSpin.value(), 0)
            window.editButton.click()
            for spin in window.score_spins():
                spin.setValue(9)
            window.editButton.click()
            window.searchEdit.setText('nguyen van an')
            self.assertFalse(window.studentsTable.isRowHidden(0))
            window.searchEdit.setText('nobody')
            self.assertTrue(window.studentsTable.isRowHidden(0))
            self.assertIsNone(window.selected_code)
            window.refreshButton.click()
            output = Path(directory) / 'grades.xlsx'
            with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(output), '')):
                window.summaryExportButton.click()
            workbook = load_workbook(output)
            self.assertEqual(workbook.active.cell(4, 3).value, 'Nguyễn Văn An')
            self.assertEqual(workbook.active.cell(4, 4).value, 8.7)
            self.assertEqual(workbook.active.cell(4, 5).value, 9)
            self.assertEqual(workbook.active.cell(4, 11).value, 'Chưa đủ điểm')
            workbook.close()
            window.close()
            window = MainWindow(database_path)
            self.assertEqual(window.studentsTable.item(0, 6).text(), '8.7')
            window.close()

    def test_cancel_and_failed_confirmation_keep_saved_scores(self):
        window = MainWindow(':memory:')
        subject_id = window.subjectCombo.currentData()
        window.db.add_record('SV001', 'Nguyễn Văn An', subject_id, (8, 7, 9))
        window.reload_data('SV001')
        window.editButton.click()
        window.finalScoreSpin.setValue(5)
        window.fullNameEdit.clear()
        with patch.object(QtWidgets.QMessageBox, 'warning') as warning:
            window.editButton.click()
            warning.assert_called_once()
        self.assertEqual(window.form_mode, 'edit')
        self.assertEqual(window.editButton.text(), 'Xác nhận')
        self.assertEqual(window.db.grade('SV001', subject_id)['final'], 9)
        window.newButton.click()
        self.assertEqual(window.form_mode, 'new')
        self.assertTrue(window.addButton.isEnabled())
        self.assertFalse(window.editButton.isEnabled())
        self.assertTrue(window.subjectCombo.isEnabled())
        self.assertEqual(window.db.grade('SV001', subject_id)['final'], 9)
        window.studentsTable.selectRow(0)
        self.assertTrue(window.finalScoreSpin.isReadOnly())
        self.assertEqual(window.finalScoreSpin.value(), 9)
        window.close()


if __name__ == '__main__':
    unittest.main()
