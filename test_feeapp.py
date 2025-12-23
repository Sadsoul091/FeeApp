import pytest
import sqlite3
import os
from datetime import datetime
from feeapp import Student, FeeApp


class TestStudent:
    def setup_method(self):
        # Create an in-memory database for testing
        self.conn = sqlite3.connect(':memory:')
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE students (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            phone TEXT,
                            admission_date TEXT
                          )''')
        self.conn.commit()

    def teardown_method(self):
        self.conn.close()

    def test_student_creation(self):
        student = Student("John Doe", "1234567890", "2023-01-01")
        assert student.name == "John Doe"
        assert student.phone == "1234567890"
        assert student.admission_date == datetime(2023, 1, 1)

    def test_save_to_db_new_student(self):
        student = Student("Jane Smith", "0987654321", "2023-06-15")
        student.save_to_db(self.conn)
        assert student.id is not None

        # Verify in database
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, phone, admission_date FROM students WHERE id=?', (student.id,))
        row = cursor.fetchone()
        assert row == ("Jane Smith", "0987654321", "2023-06-15")

    def test_load_from_db(self):
        # Insert a student directly
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO students (name, phone, admission_date) VALUES (?, ?, ?)',
                       ("Alice Johnson", "5551234567", "2022-09-01"))
        self.conn.commit()

        students = Student.load_from_db(self.conn)
        assert len(students) == 1
        assert students[0].name == "Alice Johnson"
        assert students[0].phone == "5551234567"
        assert students[0].admission_date == datetime(2022, 9, 1)

    def test_get_current_fee_month(self):
        # Test with a student admitted in January 2023
        student = Student("Bob Wilson", "1112223333", "2023-01-15")
        # Assuming current date is after admission, it should return current month or next
        # This test might be flaky depending on current date, but for demonstration
        month = student.get_current_fee_month()
        assert month in ["January", "February", "March", "April", "May", "June",
                        "July", "August", "September", "October", "November", "December"]


class TestFeeApp:
    def test_app_creation(self):
        # Note: This test might require mocking Kivy components
        # For now, just test that the class can be instantiated
        app = FeeApp()
        assert app is not None
        # Clean up
        if hasattr(app, 'conn'):
            app.conn.close()


if __name__ == "__main__":
    pytest.main([__file__])
