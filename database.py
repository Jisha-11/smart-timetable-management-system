import sqlite3
from werkzeug.security import generate_password_hash
import os

def init_database():
    """Initialize the database with tables and sample data"""
    
    # Remove existing database to start fresh
    if os.path.exists('timetable.db'):
        os.remove('timetable.db')
    
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    
    # Users table (for login)
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            section TEXT
        )
    ''')
    
    # Faculties table
    cursor.execute('''
        CREATE TABLE faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            max_hours INTEGER DEFAULT 20,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Subjects table
    cursor.execute('''
        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            semester INTEGER NOT NULL,
            type TEXT NOT NULL,
            theory_hours INTEGER DEFAULT 0,
            lab_hours INTEGER DEFAULT 0
        )
    ''')
    
    # Subject-Faculty mapping
    cursor.execute('''
        CREATE TABLE subject_faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (faculty_id) REFERENCES faculties(id)
        )
    ''')
    
    # Timetable table
    cursor.execute('''
        CREATE TABLE timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            day TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            subject_id INTEGER,
            faculty_id INTEGER,
            room TEXT,
            batch TEXT,
            is_lab INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES subjects(id),
            FOREIGN KEY (faculty_id) REFERENCES faculties(id)
        )
    ''')
    
    # Labs table
    cursor.execute('''
        CREATE TABLE labs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER DEFAULT 20
        )
    ''')
    
    # Feedback table
    cursor.execute('''
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Notifications table
    cursor.execute('''
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            target_role TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample users
    users = [
        ('admin', generate_password_hash('admin123'), 'admin', 'Administrator', None),
        ('faculty1', generate_password_hash('fac123'), 'faculty', 'Dr. Rajesh Kumar', None),
        ('faculty2', generate_password_hash('fac123'), 'faculty', 'Dr. Priya Sharma', None),
        ('faculty3', generate_password_hash('fac123'), 'faculty', 'Prof. Amit Singh', None),
        ('faculty4', generate_password_hash('fac123'), 'faculty', 'Dr. Sneha Reddy', None),
        ('faculty5', generate_password_hash('fac123'), 'faculty', 'Prof. Arjun Mehta', None),
        ('faculty6', generate_password_hash('fac123'), 'faculty', 'Dr. Kavita Iyer', None),
        ('faculty7', generate_password_hash('fac123'), 'faculty', 'Prof. Vikram Nair', None),
        ('faculty8', generate_password_hash('fac123'), 'faculty', 'Dr. Anjali Desai', None),
        ('student1', generate_password_hash('stu123'), 'student', 'Rahul Verma', '3A'),
        ('student2', generate_password_hash('stu123'), 'student', 'Ananya Desai', '5B'),
        ('student3', generate_password_hash('stu123'), 'student', 'Vikram Patel', '7A'),
    ]
    
    cursor.executemany('INSERT INTO users (username, password, role, name, section) VALUES (?, ?, ?, ?, ?)', users)
    
    # Insert sample faculties
    faculties = [
        ('Dr. Rajesh Kumar', 'rajesh@college.edu', 20, 2),
        ('Dr. Priya Sharma', 'priya@college.edu', 20, 3),
        ('Prof. Amit Singh', 'amit@college.edu', 20, 4),
        ('Dr. Sneha Reddy', 'sneha@college.edu', 20, 5),
        ('Prof. Arjun Mehta', 'arjun@college.edu', 20, 6),
        ('Dr. Kavita Iyer', 'kavita@college.edu', 20, 7),
        ('Prof. Vikram Nair', 'vikram@college.edu', 20, 8),
        ('Dr. Anjali Desai', 'anjali@college.edu', 20, 9),
    ]
    
    cursor.executemany('INSERT INTO faculties (name, email, max_hours, user_id) VALUES (?, ?, ?, ?)', faculties)
    
    # Insert MORE REALISTIC subjects for Semester 3
    subjects_sem3 = [
        ('Data Structures', 'CS301', 3, 'theory', 4, 0),
        ('Data Structures Lab', 'CS301L', 3, 'lab', 0, 2),
        ('Database Management Systems', 'CS302', 3, 'theory', 4, 0),
        ('DBMS Lab', 'CS302L', 3, 'lab', 0, 2),
        ('Computer Organization', 'CS303', 3, 'theory', 4, 0),
        ('Digital Logic Lab', 'CS303L', 3, 'lab', 0, 2),
        ('Discrete Mathematics', 'CS304', 3, 'theory', 4, 0),
        ('Web Technologies', 'CS305', 3, 'theory', 3, 0),
        ('Web Technologies Lab', 'CS305L', 3, 'lab', 0, 2),
    ]
    
    # Insert MORE subjects for Semester 5
    subjects_sem5 = [
        ('Operating Systems', 'CS501', 5, 'theory', 4, 0),
        ('OS Lab', 'CS501L', 5, 'lab', 0, 2),
        ('Computer Networks', 'CS502', 5, 'theory', 4, 0),
        ('Networks Lab', 'CS502L', 5, 'lab', 0, 2),
        ('Software Engineering', 'CS503', 5, 'theory', 4, 0),
        ('Machine Learning', 'CS504', 5, 'theory', 3, 0),
        ('ML Lab', 'CS504L', 5, 'lab', 0, 2),
        ('Compiler Design', 'CS505', 5, 'theory', 4, 0),
        ('Design Patterns Lab', 'CS505L', 5, 'lab', 0, 2),
    ]
    
    # Insert MORE subjects for Semester 7
    subjects_sem7 = [
        ('Artificial Intelligence', 'CS701', 7, 'theory', 4, 0),
        ('AI Lab', 'CS701L', 7, 'lab', 0, 2),
        ('Cloud Computing', 'CS702', 7, 'theory', 4, 0),
        ('Cloud Lab', 'CS702L', 7, 'lab', 0, 2),
        ('Cyber Security', 'CS703', 7, 'theory', 4, 0),
        ('Big Data Analytics', 'CS704', 7, 'theory', 3, 0),
        ('Big Data Lab', 'CS704L', 7, 'lab', 0, 2),
        ('Project Work', 'CS705', 7, 'theory', 2, 0),
        ('Seminar', 'CS706', 7, 'theory', 1, 0),
    ]
    
    all_subjects = subjects_sem3 + subjects_sem5 + subjects_sem7
    cursor.executemany('INSERT INTO subjects (name, code, semester, type, theory_hours, lab_hours) VALUES (?, ?, ?, ?, ?, ?)', all_subjects)
    
    # Insert sample labs
    labs = [
        ('CSE Lab 1', 60),
        ('CSE Lab 2', 60),
        ('CSE Lab 3', 60),
        ('CSE Lab 4', 60),
        ('CSE Lab 5', 60),
        ('CSE Lab 6', 60),
    ]
    
    cursor.executemany('INSERT INTO labs (name, capacity) VALUES (?, ?)', labs)
    
    # Map subjects to faculties - MORE VARIETY
    sections_3 = ['3A', '3B', '3C', '3D']
    for section in sections_3:
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (1, 1, ?)', (section,))  # DS
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (2, 1, ?)', (section,))  # DS Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (3, 2, ?)', (section,))  # DBMS
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (4, 2, ?)', (section,))  # DBMS Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (5, 3, ?)', (section,))  # CO
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (6, 3, ?)', (section,))  # DL Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (7, 4, ?)', (section,))  # DM
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (8, 5, ?)', (section,))  # Web Tech
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (9, 5, ?)', (section,))  # Web Lab
    
    sections_5 = ['5A', '5B', '5C']
    for section in sections_5:
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (10, 2, ?)', (section,))  # OS
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (11, 2, ?)', (section,))  # OS Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (12, 3, ?)', (section,))  # CN
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (13, 3, ?)', (section,))  # CN Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (14, 4, ?)', (section,))  # SE
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (15, 5, ?)', (section,))  # ML
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (16, 5, ?)', (section,))  # ML Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (17, 6, ?)', (section,))  # CD
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (18, 6, ?)', (section,))  # DP Lab
    
    sections_7 = ['7A', '7B', '7C']
    for section in sections_7:
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (19, 1, ?)', (section,))  # AI
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (20, 1, ?)', (section,))  # AI Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (21, 2, ?)', (section,))  # Cloud
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (22, 2, ?)', (section,))  # Cloud Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (23, 3, ?)', (section,))  # Cyber
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (24, 4, ?)', (section,))  # Big Data
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (25, 4, ?)', (section,))  # Big Data Lab
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (26, 7, ?)', (section,))  # Project
        cursor.execute('INSERT INTO subject_faculty (subject_id, faculty_id, section) VALUES (27, 8, ?)', (section,))  # Seminar
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully with MORE realistic data!")
    print("\nSample Login Credentials:")
    print("=" * 50)
    print("Admin    : username='admin'    password='admin123'")
    print("Faculty  : username='faculty1' password='fac123'")
    print("Student  : username='student1' password='stu123'")
    print("=" * 50)

if __name__ == '__main__':
    init_database()