import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtTest import QTest

from login import LoginDialog


class LoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.dialog = LoginDialog()
        self.dialog.show()
        self.app.processEvents()

    def tearDown(self):
        self.dialog.close()

    def test_invalid_credentials_and_required_fields(self):
        for username, password in [('', ''), ('Admin', ''), ('', '123456Ab'),
                                   ('admin', '123456Ab'), ('Admin', '123456ab'),
                                   ('Admin', 'wrong'), ('Admin', '123456Ab ')]:
            with self.subTest(username=username, password=password):
                self.dialog.usernameEdit.setText(username)
                self.dialog.passwordEdit.setText(password)
                self.dialog.loginButton.click()
                self.assertTrue(self.dialog.isVisible())
                self.assertEqual(self.dialog.result(), QtWidgets.QDialog.Rejected)
                self.assertTrue(self.dialog.errorLabel.text())

    def test_correct_credentials_accept_on_click_and_enter(self):
        for use_enter in (False, True):
            with self.subTest(use_enter=use_enter):
                self.dialog.show()
                self.dialog.usernameEdit.setText('Admin')
                self.dialog.passwordEdit.setText('123456Ab')
                if use_enter:
                    self.dialog.passwordEdit.setFocus()
                    QTest.keyClick(self.dialog.passwordEdit, QtCore.Qt.Key_Return)
                else:
                    self.dialog.loginButton.click()
                self.assertEqual(self.dialog.result(), QtWidgets.QDialog.Accepted)
                self.assertFalse(self.dialog.isVisible())
                self.assertEqual(self.dialog.passwordEdit.text(), '')

    def test_password_visibility_and_cancel(self):
        self.assertEqual(self.dialog.passwordEdit.echoMode(), QtWidgets.QLineEdit.Password)
        self.dialog.showPasswordCheck.click()
        self.assertEqual(self.dialog.passwordEdit.echoMode(), QtWidgets.QLineEdit.Normal)
        self.dialog.showPasswordCheck.click()
        self.assertEqual(self.dialog.passwordEdit.echoMode(), QtWidgets.QLineEdit.Password)
        self.dialog.cancelButton.click()
        self.assertEqual(self.dialog.result(), QtWidgets.QDialog.Rejected)
        self.assertFalse(self.dialog.isVisible())
