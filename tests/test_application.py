import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook
from PyQt5 import QtWidgets

from database import Database, SUBJECT_NAMES
from grading import GradePolicy
from main import MainWindow


class GradingTests(unittest.TestCase):
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
            self.assertEqual(workbook.active.cell(4, 10).value, 'Chưa đủ điểm')
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
