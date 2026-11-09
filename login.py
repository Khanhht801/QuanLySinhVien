"""Administrator sign-in dialog, loaded from the Qt Designer form."""

from pathlib import Path

from PyQt5 import QtCore, QtWidgets, uic

import resources_rc  # noqa: F401 - register the application icon


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).with_name('login.ui')), self)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinMaxButtonsHint)
        self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
        self.loginButton.clicked.connect(self.authenticate)
        self.cancelButton.clicked.connect(self.reject)
        self.showPasswordCheck.toggled.connect(self.toggle_password)
        self.usernameEdit.textChanged.connect(self.clear_error)
        self.passwordEdit.textChanged.connect(self.clear_error)
        self.usernameEdit.setFocus()

    def toggle_password(self, visible):
        self.passwordEdit.setEchoMode(
            QtWidgets.QLineEdit.Normal if visible else QtWidgets.QLineEdit.Password
        )

    def clear_error(self):
        self.errorLabel.clear()

    def authenticate(self):
        username = self.usernameEdit.text()
        password = self.passwordEdit.text()
        if not username or not password:
            self.errorLabel.setText('Vui lòng nhập tài khoản và mật khẩu.')
            (self.usernameEdit if not username else self.passwordEdit).setFocus()
            return
        if username == 'Admin' and password == '123456Ab':
            self.passwordEdit.clear()
            self.accept()
            return
        self.passwordEdit.clear()
        self.errorLabel.setText('Tài khoản hoặc mật khẩu không đúng.')
        self.passwordEdit.setFocus()
