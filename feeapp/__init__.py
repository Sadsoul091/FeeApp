from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from plyer import sms
from datetime import datetime
import calendar
import sqlite3
from kivy.utils import platform

class Student:
    def __init__(self, name, phone, admission_date, id=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.admission_date = datetime.strptime(admission_date, '%Y-%m-%d')

    def get_current_fee_month(self):
        now = datetime.now()
        # Assume fees are due monthly starting from admission month
        months_diff = (now.year - self.admission_date.year) * 12 + now.month - self.admission_date.month
        if months_diff < 0:
            months_diff = 0
        fee_month = self.admission_date.month + months_diff
        if fee_month > 12:
            fee_month -= 12
        return calendar.month_name[fee_month]

    def save_to_db(self, conn):
        cursor = conn.cursor()
        if self.id is None:
            cursor.execute('INSERT INTO students (name, phone, admission_date) VALUES (?, ?, ?)',
                           (self.name, self.phone, self.admission_date.strftime('%Y-%m-%d')))
            self.id = cursor.lastrowid
        else:
            cursor.execute('UPDATE students SET name=?, phone=?, admission_date=? WHERE id=?',
                           (self.name, self.phone, self.admission_date.strftime('%Y-%m-%d'), self.id))
        conn.commit()

    @staticmethod
    def load_from_db(conn):
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone, admission_date FROM students')
        rows = cursor.fetchall()
        students = []
        for row in rows:
            students.append(Student(row[1], row[2], row[3], row[0]))
        return students

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text='Fee Manager', font_size=30))

        entry_btn = Button(text='Entry', size_hint_y=0.2)
        entry_btn.bind(on_press=self.go_to_entry)
        layout.add_widget(entry_btn)

        list_btn = Button(text='Students List', size_hint_y=0.2)
        list_btn.bind(on_press=self.go_to_list)
        layout.add_widget(list_btn)

        msg_btn = Button(text='Messages', size_hint_y=0.2)
        msg_btn.bind(on_press=self.go_to_messages)
        layout.add_widget(msg_btn)

        self.add_widget(layout)

    def go_to_entry(self, instance):
        self.manager.current = 'entry'

    def go_to_list(self, instance):
        self.manager.current = 'list'

    def go_to_messages(self, instance):
        self.manager.current = 'messages'

class EntryScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        back_btn = Button(text='Back to Menu', size_hint_y=0.1)
        back_btn.bind(on_press=self.back_to_menu)
        layout.add_widget(back_btn)

        layout.add_widget(Label(text='Add Student'))

        self.name_input = TextInput(hint_text='Name', multiline=False)
        self.phone_input = TextInput(hint_text='Phone', multiline=False)
        self.date_input = TextInput(hint_text='Admission Date (YYYY-MM-DD)', multiline=False)

        layout.add_widget(self.name_input)
        layout.add_widget(self.phone_input)
        layout.add_widget(self.date_input)

        add_button = Button(text='Add Student')
        add_button.bind(on_press=self.add_student)
        layout.add_widget(add_button)

        self.add_widget(layout)

    def back_to_menu(self, instance):
        self.manager.current = 'menu'

    def add_student(self, instance):
        name = self.name_input.text
        phone = self.phone_input.text
        date = self.date_input.text
        if name and phone and date:
            try:
                student = Student(name, phone, date)
                student.save_to_db(self.app.conn)
                self.app.students.append(student)
                popup = Popup(title='Success', content=Label(text='Student list updated'), size_hint=(None, None), size=(300, 200))
                popup.open()
                self.name_input.text = ''
                self.phone_input.text = ''
                self.date_input.text = ''
                # Update the list screen if it's current
                if self.manager.current == 'list':
                    self.manager.get_screen('list').update_student_list()
                # Update the messages screen spinner
                self.manager.get_screen('messages').student_spinner.values = [s.name for s in self.app.students]
            except ValueError:
                pass  # Invalid date

class ListScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        back_btn = Button(text='Back to Menu', size_hint_y=0.1)
        back_btn.bind(on_press=self.back_to_menu)
        layout.add_widget(back_btn)

        layout.add_widget(Label(text='Students List'))

        scroll = ScrollView(size_hint=(1, 0.9))
        self.student_grid = GridLayout(cols=1, size_hint_y=None)
        self.student_grid.bind(minimum_height=self.student_grid.setter('height'))
        scroll.add_widget(self.student_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def back_to_menu(self, instance):
        self.manager.current = 'menu'

    def on_enter(self):
        self.update_student_list()

    def update_student_list(self):
        self.student_grid.clear_widgets()
        for student in self.app.students:
            student_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=120)
            student_layout.add_widget(Label(text=f'Name: {student.name}'))
            student_layout.add_widget(Label(text=f'Phone: {student.phone}'))
            student_layout.add_widget(Label(text=f'Admission: {student.admission_date.strftime("%Y-%m-%d")}'))
            student_layout.add_widget(Label(text=f'Current Month: {student.get_current_fee_month()}'))

            buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            due_button = Button(text='Send Due')
            due_button.bind(on_press=lambda x, s=student: self.send_due(s))
            buttons_layout.add_widget(due_button)

            paid_button = Button(text='Send Paid')
            paid_button.bind(on_press=lambda x, s=student: self.send_paid(s))
            buttons_layout.add_widget(paid_button)

            student_layout.add_widget(buttons_layout)
            self.student_grid.add_widget(student_layout)

    def send_due(self, student):
        month = student.get_current_fee_month()
        message = f"Dear {student.name}, your fee for {month} is due. Please pay."
        try:
            sms.send(recipient=student.phone, message=message)
            popup = Popup(title='Success', content=Label(text='Due message sent successfully'), size_hint=(None, None), size=(300, 200))
            popup.open()
        except Exception as e:
            popup = Popup(title='Error', content=Label(text='Failed to send SMS. SMS sending is only available on Android devices.'), size_hint=(None, None), size=(400, 200))
            popup.open()

    def send_paid(self, student):
        month = student.get_current_fee_month()
        message = f"Dear {student.name}, your fee for {month} has been paid. Thank you."
        try:
            sms.send(recipient=student.phone, message=message)
            popup = Popup(title='Success', content=Label(text='Paid message sent successfully'), size_hint=(None, None), size=(300, 200))
            popup.open()
        except Exception as e:
            popup = Popup(title='Error', content=Label(text='Failed to send SMS. SMS sending is only available on Android devices.'), size_hint=(None, None), size=(400, 200))
            popup.open()

class MessagesScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        back_btn = Button(text='Back to Menu', size_hint_y=0.1)
        back_btn.bind(on_press=self.back_to_menu)
        layout.add_widget(back_btn)

        layout.add_widget(Label(text='Send Custom Message'))

        self.student_spinner = Spinner(text='Select Student', values=[s.name for s in self.app.students])
        layout.add_widget(self.student_spinner)

        self.message_input = TextInput(hint_text='Enter message', multiline=True, size_hint_y=0.4)
        layout.add_widget(self.message_input)

        send_button = Button(text='Send Message')
        send_button.bind(on_press=self.send_message)
        layout.add_widget(send_button)

        self.add_widget(layout)

    def back_to_menu(self, instance):
        self.manager.current = 'menu'

    def send_message(self, instance):
        student_name = self.student_spinner.text
        message = self.message_input.text
        if student_name != 'Select Student' and message:
            student = next((s for s in self.app.students if s.name == student_name), None)
            if student:
                if platform == 'android':
                    try:
                        sms.send(recipient=student.phone, message=message)
                        popup = Popup(title='Success', content=Label(text='Message sent successfully'), size_hint=(None, None), size=(300, 200))
                        popup.open()
                        self.message_input.text = ''
                    except Exception as e:
                        popup = Popup(title='Error', content=Label(text='Failed to send SMS'), size_hint=(None, None), size=(300, 200))
                        popup.open()
                else:
                    # On Windows or other platforms, show the message in a popup
                    popup_content = BoxLayout(orientation='vertical')
                    popup_content.add_widget(Label(text=f'To: {student.phone}'))
                    popup_content.add_widget(Label(text=f'Message: {message}'))
                    popup = Popup(title='Message Preview (Windows)', content=popup_content, size_hint=(None, None), size=(400, 300))
                    popup.open()
                    self.message_input.text = ''

class FeeApp(App):
    def build(self):
        self.conn = sqlite3.connect('students.db')
        self.create_table()
        self.students = Student.load_from_db(self.conn)
        Window.size = (400, 600)

        # Root layout with background
        root = FloatLayout()
        bg = Image(source='background.jpg', allow_stretch=True, keep_ratio=False, opacity=0.3)
        root.add_widget(bg)

        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(EntryScreen(self, name='entry'))
        sm.add_widget(ListScreen(self, name='list'))
        sm.add_widget(MessagesScreen(self, name='messages'))

        root.add_widget(sm)
        return root

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS students (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            phone TEXT,
                            admission_date TEXT
                          )''')
        self.conn.commit()

    def add_student(self, instance):
        name = self.name_input.text
        phone = self.phone_input.text
        date = self.date_input.text
        if name and phone and date:
            try:
                student = Student(name, phone, date)
                student.save_to_db(self.conn)
                self.students.append(student)
                self.update_student_list()
                self.name_input.text = ''
                self.phone_input.text = ''
                self.date_input.text = ''
            except ValueError:
                pass  # Invalid date

    def on_stop(self):
        self.conn.close()

    def update_student_list(self):
        self.student_grid.clear_widgets()
        for student in self.students:
            student_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=100)
            student_layout.add_widget(Label(text=f'{student.name}\n{student.phone}\n{student.admission_date.strftime("%Y-%m-%d")}'))

            due_button = Button(text='Send Due')
            due_button.bind(on_press=lambda x, s=student: self.send_due(s))
            student_layout.add_widget(due_button)

            paid_button = Button(text='Send Paid')
            paid_button.bind(on_press=lambda x, s=student: self.send_paid(s))
            student_layout.add_widget(paid_button)

            self.student_grid.add_widget(student_layout)

    def send_due(self, student):
        month = student.get_current_fee_month()
        message = f"Dear {student.name}, your fee for {month} is due. Please pay."
        try:
            sms.send(recipient=student.phone, message=message)
        except Exception as e:
            print(f"Failed to send SMS: {e}")

    def send_paid(self, student):
        month = student.get_current_fee_month()
        message = f"Dear {student.name}, your fee for {month} has been paid. Thank you."
        try:
            sms.send(recipient=student.phone, message=message)
        except Exception as e:
            print(f"Failed to send SMS: {e}")

    def open_app(self, instance):
        popup = Popup(title='App Status', content=Label(text='The app is already open!'), size_hint=(None, None), size=(300, 200))
        popup.open()

if __name__ == '__main__':
    FeeApp().run()
