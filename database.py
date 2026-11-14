"""SQLite persistence. Transactions keep student details and scores consistent."""
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys

from grading import GradePolicy

CLASS_NAME = 'K10TIN'
SEMESTER = 5
SUBJECT_NAMES = ('Lập trình Python', 'Lập trình web nâng cao', 'AutoCAD',
                 'Lắp ráp và cài đặt máy tính', 'Chăm sóc khách hàng')
if getattr(sys, 'frozen', False):
    # Keep installed application data outside the bundle and its update folders.
    DEFAULT_DB = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'QLSV' / 'k10tin.sqlite3'
else:
    DEFAULT_DB = Path(__file__).resolve().parent / 'data' / 'k10tin.sqlite3'


class Database:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path) if str(path) != ':memory:' else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.connection.execute('PRAGMA busy_timeout = 5000')
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS students (
                code TEXT PRIMARY KEY COLLATE NOCASE,
                name TEXT NOT NULL CHECK(length(trim(name)) > 0),
                class_name TEXT NOT NULL DEFAULT 'K10TIN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(trim(name)) > 0),
                credits INTEGER NOT NULL CHECK(credits BETWEEN 1 AND 30)
            );
            CREATE TABLE IF NOT EXISTS grades (
                student_code TEXT NOT NULL REFERENCES students(code) ON DELETE CASCADE ON UPDATE CASCADE,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
                semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 10),
                regular REAL NOT NULL CHECK(regular BETWEEN 0 AND 10),
                midterm REAL NOT NULL CHECK(midterm BETWEEN 0 AND 10),
                final REAL NOT NULL CHECK(final BETWEEN 0 AND 10),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(student_code, subject_id, semester)
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS conduct_scores (
                student_code TEXT NOT NULL REFERENCES students(code) ON DELETE CASCADE ON UPDATE CASCADE,
                semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 10),
                score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
                PRIMARY KEY(student_code, semester)
            );
            PRAGMA user_version = 1;
        ''')
        # Keep earlier semesters and their subject records intact.
        if self.connection.execute("SELECT 1 FROM settings WHERE key='semester5_initialized'").fetchone() is None:
            with self.connection:
                self.connection.executemany('INSERT OR IGNORE INTO subjects(name, credits) VALUES (?, ?)',
                                            [(name, 1) for name in SUBJECT_NAMES])
                self.connection.execute("INSERT INTO settings VALUES ('semester5_initialized','true')")

    @staticmethod
    def student_values(code, name):
        code = code.strip().upper()
        name = ' '.join(name.split())
        if not re.fullmatch(r'[A-Z0-9_-]{1,30}', code):
            raise ValueError('Mã sinh viên cần 1–30 ký tự: chữ không dấu, số, dấu gạch ngang hoặc gạch dưới.')
        if not 2 <= len(name) <= 150:
            raise ValueError('Họ tên cần từ 2 đến 150 ký tự.')
        return code, name

    @staticmethod
    def score_values(scores):
        if scores is None:
            return None
        if len(scores) != 3 or not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 10 for v in scores):
            raise ValueError('Nhập đủ ba điểm TX, ĐK, CK trong khoảng 0–10.')
        return tuple(scores)

    def subjects(self):
        rows = {row['name']: dict(row) for row in self.connection.execute('SELECT * FROM subjects')}
        return [rows[name] for name in SUBJECT_NAMES]

    def student(self, code):
        row = self.connection.execute('SELECT * FROM students WHERE code=?', (code,)).fetchone()
        return dict(row) if row else None

    def students(self):
        return [dict(row) for row in self.connection.execute('SELECT * FROM students ORDER BY code COLLATE NOCASE')]

    def next_student_code(self):
        codes = {row['code'].upper() for row in self.students()}
        number = 1
        while f'SV{number:03d}' in codes:
            number += 1
        return f'SV{number:03d}'

    def _insert_grade(self, code, subject_id, scores, replace=False):
        values = self.score_values(scores)
        sql = '''INSERT INTO grades(student_code,subject_id,semester,regular,midterm,final)
                 VALUES (?,?,?,?,?,?)'''
        if replace:
            sql += ''' ON CONFLICT(student_code,subject_id,semester) DO UPDATE SET
                       regular=excluded.regular,midterm=excluded.midterm,final=excluded.final,updated_at=CURRENT_TIMESTAMP'''
        self.connection.execute(sql, (code, subject_id, SEMESTER, *values))

    @staticmethod
    def validate_conduct(score):
        if score is not None and (not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100):
            raise ValueError('Điểm rèn luyện phải từ 0 đến 100.')

    def _save_conduct(self, code, score):
        if score is None:
            self.connection.execute('DELETE FROM conduct_scores WHERE student_code=? AND semester=?', (code, SEMESTER))
        else:
            self.connection.execute('''INSERT INTO conduct_scores(student_code, semester, score) VALUES (?, ?, ?)
                ON CONFLICT(student_code, semester) DO UPDATE SET score=excluded.score''', (code, SEMESTER, score))

    def conduct_score(self, code):
        row = self.connection.execute('SELECT score FROM conduct_scores WHERE student_code=? AND semester=?', (code, SEMESTER)).fetchone()
        return row['score'] if row else None

    def add_record(self, code, name, subject_id, scores=None, conduct=None):
        code, name = self.student_values(code, name)
        self.score_values(scores)
        self.validate_conduct(conduct)
        existing = self.student(code)
        if existing and existing['name'] != name:
            raise ValueError('Mã sinh viên này đã có tên khác. Dùng Sửa để thay đổi thông tin.')
        if existing and scores is None:
            raise ValueError('Sinh viên đã tồn tại. Nhập điểm môn khác hoặc dùng Sửa.')
        if existing and self.grade(code, subject_id):
            raise ValueError('Sinh viên đã có điểm môn này. Dùng Sửa để cập nhật.')
        with self.connection:
            if not existing:
                self.connection.execute('INSERT INTO students(code,name,class_name) VALUES (?,?,?)', (code, name, CLASS_NAME))
            if scores is not None:
                self._insert_grade(code, subject_id, scores)
            if conduct is not None:
                self._save_conduct(code, conduct)
        return code

    def update_record(self, original_code, code, name, subject_id, scores=None, conduct=...):
        code, name = self.student_values(code, name)
        self.score_values(scores)
        if conduct is not ...:
            self.validate_conduct(conduct)
        if not self.student(original_code):
            raise ValueError('Sinh viên được chọn không còn tồn tại. Hãy làm mới.')
        other = self.student(code)
        if other and other['code'].casefold() != original_code.casefold():
            raise ValueError('Mã sinh viên mới đã được sử dụng.')
        with self.connection:
            self.connection.execute('UPDATE students SET code=?,name=?,class_name=? WHERE code=?',
                                    (code, name, CLASS_NAME, original_code))
            if scores is not None:
                self._insert_grade(code, subject_id, scores, replace=True)
            if conduct is not ...:
                self._save_conduct(code, conduct)
        return code

    def grade(self, code, subject_id):
        row = self.connection.execute('SELECT * FROM grades WHERE student_code=? AND subject_id=? AND semester=?',
                                      (code, subject_id, SEMESTER)).fetchone()
        return dict(row) if row else None

    def grade_rows(self, subject_id):
        return [dict(row) for row in self.connection.execute('''
            SELECT s.code,s.name,s.class_name,g.regular,g.midterm,g.final
            FROM students s LEFT JOIN grades g ON s.code=g.student_code AND g.subject_id=? AND g.semester=?
            ORDER BY s.code COLLATE NOCASE''', (subject_id, SEMESTER))]

    def delete_grade(self, code, subject_id):
        with self.connection:
            self.connection.execute('DELETE FROM grades WHERE student_code=? AND subject_id=? AND semester=?',
                                    (code, subject_id, SEMESTER))

    def delete_student(self, code):
        with self.connection:
            self.connection.execute('DELETE FROM students WHERE code=?', (code,))

    def save_subject(self, name, credits, subject_id=None):
        name = ' '.join(name.split())
        if not 2 <= len(name) <= 100 or not isinstance(credits, int) or not 1 <= credits <= 30:
            raise ValueError('Tên môn cần 2–100 ký tự; số tín chỉ từ 1 đến 30.')
        with self.connection:
            if subject_id is None:
                cursor = self.connection.execute('INSERT INTO subjects(name,credits) VALUES (?,?)', (name, credits))
                return cursor.lastrowid
            cursor = self.connection.execute('UPDATE subjects SET name=?,credits=? WHERE id=?', (name, credits, subject_id))
            if cursor.rowcount != 1:
                raise ValueError('Môn học không còn tồn tại.')
        return subject_id

    def delete_subject(self, subject_id):
        if len(self.subjects()) <= 1:
            raise ValueError('Cần giữ lại ít nhất một môn học.')
        if self.connection.execute('SELECT 1 FROM grades WHERE subject_id=? LIMIT 1', (subject_id,)).fetchone():
            raise ValueError('Môn học đã có điểm, không thể xóa. Có thể đổi tên hoặc số tín chỉ.')
        with self.connection:
            self.connection.execute('DELETE FROM subjects WHERE id=?', (subject_id,))

    def policy(self):
        return GradePolicy()

    def save_policy(self, policy):
        with self.connection:
            self.connection.execute("INSERT INTO settings(key,value) VALUES ('grading_policy',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                    (json.dumps(policy.to_dict()),))

    def summary(self, policy):
        subjects = self.subjects()
        grades = {(row['student_code'], row['subject_id']): dict(row) for row in self.connection.execute('SELECT * FROM grades WHERE semester=?', (SEMESTER,))}
        result = []
        for student in self.students():
            scores = []
            for subject in subjects:
                grade = grades.get((student['code'], subject['id']))
                scores.append(policy.course_score(grade['regular'], grade['midterm'], grade['final']) if grade and policy else None)
            average = policy.semester_score(list(zip(scores, [s['credits'] for s in subjects]))) if policy else None
            result.append({**student, 'scores': scores, 'average': average, 'conduct': self.conduct_score(student['code']),
                           'classification': policy.classify(average) if policy else 'Chưa đủ điểm'})
        return result

    def backup(self, path):
        destination_path = Path(path).resolve()
        if self.path and destination_path == self.path.resolve():
            raise ValueError('Chọn file khác với cơ sở dữ liệu đang sử dụng.')
        with sqlite3.connect(str(destination_path)) as destination:
            self.connection.backup(destination)

    def close(self):
        self.connection.close()
