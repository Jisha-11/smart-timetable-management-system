from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import check_password_hash
import sqlite3
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from timetable_generator import TimetableGenerator, generate_all_timetables

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('timetable.db')
    conn.row_factory = sqlite3.Row
    return conn

# Login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        elif role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            session['section'] = user['section']
            
            flash(f'Welcome, {user["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db()
    
    # Get statistics
    stats = {
        'faculties': conn.execute('SELECT COUNT(*) as count FROM faculties').fetchone()['count'],
        'subjects': conn.execute('SELECT COUNT(*) as count FROM subjects').fetchone()['count'],
        'pending_feedback': conn.execute("SELECT COUNT(*) as count FROM feedback WHERE status='pending'").fetchone()['count'],
    }
    
    # Get recent feedback
    feedback = conn.execute('''
        SELECT f.*, u.name as user_name, u.role 
        FROM feedback f 
        JOIN users u ON f.user_id = u.id 
        ORDER BY f.timestamp DESC LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats, feedback=feedback)

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if session.get('role') != 'faculty':
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get faculty details
    faculty = conn.execute('''
        SELECT * FROM faculties WHERE user_id = ?
    ''', (session['user_id'],)).fetchone()
    
    # Get assigned subjects
    subjects = conn.execute('''
        SELECT DISTINCT s.name, s.code, sf.section
        FROM subjects s
        JOIN subject_faculty sf ON s.id = sf.subject_id
        WHERE sf.faculty_id = ?
        ORDER BY sf.section
    ''', (faculty['id'],)).fetchall()
    
    conn.close()
    
    return render_template('faculty_dashboard.html', faculty=faculty, subjects=subjects)

@app.route('/faculty/my-timetable')
@login_required
def faculty_my_timetable():
    if session.get('role') != 'faculty':
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get faculty details
    faculty = conn.execute('''
        SELECT * FROM faculties WHERE user_id = ?
    ''', (session['user_id'],)).fetchone()
    
    if not faculty:
        conn.close()
        flash('Faculty details not found', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    # Get faculty's timetable across all sections
    timetable_data = conn.execute('''
        SELECT t.*, s.name as subject_name, s.code, f.name as faculty_name
        FROM timetable t
        LEFT JOIN subjects s ON t.subject_id = s.id
        LEFT JOIN faculties f ON t.faculty_id = f.id
        WHERE t.faculty_id = ?
        ORDER BY 
            CASE t.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END,
            t.time_slot
    ''', (faculty['id'],)).fetchall()
    
    conn.close()
    
    # Organize timetable
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    display_slots = [
        '08:30-09:30',
        '09:30-10:30',
        'BREAK',
        '10:45-11:45',
        '11:45-12:45',
        'LUNCH',
        '13:30-14:30',
        '14:30-15:30',
        '15:30-16:30',
    ]
    
    organized_tt = {}
    lab_merged_slots = {}
    
    for day in days:
        organized_tt[day] = {}
        lab_merged_slots[day] = set()
        for slot in display_slots:
            organized_tt[day][slot] = []
    
    # Fill in the timetable - ONLY ONE CLASS PER TIME SLOT
    for entry in timetable_data:
        day = entry['day']
        time_slot = entry['time_slot']
        
        # For labs (2-hour slots)
        if entry['is_lab']:
            if time_slot == '08:30-10:30':
                # Only add if slot is empty (faculty can only teach one class at a time)
                if not organized_tt[day]['08:30-09:30']:
                    organized_tt[day]['08:30-09:30'].append(entry)
                    lab_merged_slots[day].add('08:30-09:30')
            elif time_slot == '10:45-12:45':
                if not organized_tt[day]['10:45-11:45']:
                    organized_tt[day]['10:45-11:45'].append(entry)
                    lab_merged_slots[day].add('10:45-11:45')
            elif time_slot == '13:30-15:30':
                if not organized_tt[day]['13:30-14:30']:
                    organized_tt[day]['13:30-14:30'].append(entry)
                    lab_merged_slots[day].add('13:30-14:30')
        else:
            # Theory classes - only add if slot is empty
            if time_slot in organized_tt[day] and not organized_tt[day][time_slot]:
                organized_tt[day][time_slot].append(entry)
    
    return render_template('faculty_my_timetable.html', timetable=organized_tt, 
                         days=days, time_slots=display_slots, faculty=faculty, 
                         lab_merged_slots=lab_merged_slots)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
    
    section = session.get('section')
    
    return render_template('student_dashboard.html', section=section)

@app.route('/view-timetable/<section>')
@login_required
def view_timetable(section):
    conn = get_db()
    
    # Get timetable for the section
    timetable_data = conn.execute('''
        SELECT t.*, s.name as subject_name, s.code, f.name as faculty_name
        FROM timetable t
        LEFT JOIN subjects s ON t.subject_id = s.id
        LEFT JOIN faculties f ON t.faculty_id = f.id
        WHERE t.section = ?
        ORDER BY 
            CASE t.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END,
            t.time_slot
    ''', (section,)).fetchall()
    
    conn.close()
    
    # Organize timetable by day and time
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    # Individual time slots
    display_slots = [
        '08:30-09:30',
        '09:30-10:30',
        'BREAK',
        '10:45-11:45',
        '11:45-12:45',
        'LUNCH',
        '13:30-14:30',
        '14:30-15:30',
        '15:30-16:30',
    ]
    
    organized_tt = {}
    lab_merged_slots = {}  # Track which slots should be merged for labs
    
    for day in days:
        organized_tt[day] = {}
        lab_merged_slots[day] = set()
        for slot in display_slots:
            organized_tt[day][slot] = []
    
    # Fill in the timetable
    for entry in timetable_data:
        day = entry['day']
        time_slot = entry['time_slot']
        
        # For labs (2-hour slots)
        if entry['is_lab']:
            if time_slot == '08:30-10:30':
                # Add to first slot only, mark for merge
                organized_tt[day]['08:30-09:30'].append(entry)
                lab_merged_slots[day].add('08:30-09:30')
            elif time_slot == '10:45-12:45':
                organized_tt[day]['10:45-11:45'].append(entry)
                lab_merged_slots[day].add('10:45-11:45')
            elif time_slot == '13:30-15:30':
                organized_tt[day]['13:30-14:30'].append(entry)
                lab_merged_slots[day].add('13:30-14:30')
        else:
            # Theory classes - add to their specific slot
            if time_slot in organized_tt[day]:
                organized_tt[day][time_slot].append(entry)
    
    return render_template('view_timetable.html', section=section, timetable=organized_tt, 
                         days=days, time_slots=display_slots, lab_merged_slots=lab_merged_slots)

@app.route('/generate-timetable/<section>')
@admin_required
def generate_timetable(section):
    generator = TimetableGenerator()
    success, message = generator.generate_timetable(section)
    
    if success:
        flash(f'Timetable generated successfully for {section}', 'success')
    else:
        flash(f'Failed to generate timetable for {section}: {message}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/generate-all-timetables')
@admin_required
def generate_all():
    results = generate_all_timetables()
    
    success_count = sum(1 for r in results.values() if r['success'])
    total_count = len(results)
    
    flash(f'Generated {success_count}/{total_count} timetables successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/download-timetable/<section>')
@login_required
def download_timetable(section):
    conn = get_db()
    
    # Get timetable data
    timetable_data = conn.execute('''
        SELECT t.*, s.name as subject_name, s.code, f.name as faculty_name
        FROM timetable t
        LEFT JOIN subjects s ON t.subject_id = s.id
        LEFT JOIN faculties f ON t.faculty_id = f.id
        WHERE t.section = ?
        ORDER BY 
            CASE t.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END,
            t.time_slot
    ''', (section,)).fetchall()
    
    conn.close()
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                           rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    elements = []
    
    # Title
    styles = getSampleStyleSheet()
    title = Paragraph(f"<b>Class Timetable - Section {section}</b>", styles['Title'])
    elements.append(title)
    subtitle = Paragraph("CSE Department | Academic Year 2024-25", styles['Normal'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.3*inch))
    
    # Organize timetable by day and time
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    display_slots = [
        '08:30-09:30',
        '09:30-10:30',
        'BREAK',
        '10:45-11:45',
        '11:45-12:45',
        'LUNCH',
        '13:30-14:30',
        '14:30-15:30',
        '15:30-16:30',
    ]
    
    organized_tt = {}
    lab_merged_slots = {}
    
    for day in days:
        organized_tt[day] = {}
        lab_merged_slots[day] = set()
        for slot in display_slots:
            organized_tt[day][slot] = []
    
    # Fill in the timetable
    for entry in timetable_data:
        day = entry['day']
        time_slot = entry['time_slot']
        
        # For labs (2-hour slots)
        if entry['is_lab']:
            if time_slot == '08:30-10:30':
                organized_tt[day]['08:30-09:30'].append(entry)
                lab_merged_slots[day].add('08:30-09:30')
            elif time_slot == '10:45-12:45':
                organized_tt[day]['10:45-11:45'].append(entry)
                lab_merged_slots[day].add('10:45-11:45')
            elif time_slot == '13:30-15:30':
                organized_tt[day]['13:30-14:30'].append(entry)
                lab_merged_slots[day].add('13:30-14:30')
        else:
            if time_slot in organized_tt[day]:
                organized_tt[day][time_slot].append(entry)
    
    # Build table data - HORIZONTAL FORMAT
    table_data = []
    
    # Header row
    header = ['Day', '8:30-9:30 AM', '9:30-10:30 AM', 'Break', '10:45-11:45 AM', 
              '11:45-12:45 PM', 'Lunch', '1:30-2:30 PM', '2:30-3:30 PM', '3:30-4:30 PM']
    table_data.append(header)
    
    # Data rows - one per day
    for day in days:
        row = [day]
        
        # Track if we should skip next cell (for merged lab cells)
        skip_next = False
        
        time_slots_to_process = [
            '08:30-09:30', '09:30-10:30', 'BREAK',
            '10:45-11:45', '11:45-12:45', 'LUNCH',
            '13:30-14:30', '14:30-15:30', '15:30-16:30'
        ]
        
        for i, slot in enumerate(time_slots_to_process):
            if slot == 'BREAK':
                row.append('☕')
                continue
            elif slot == 'LUNCH':
                row.append('🍽️')
                continue
            
            # Check if previous slot was a lab that should merge
            if skip_next:
                skip_next = False
                continue
            
            # Check if this is a lab slot (should merge with next)
            if slot in lab_merged_slots[day]:
                # This is a lab - will span 2 cells
                entries = organized_tt[day][slot]
                if entries:
                    cell_text = ""
                    for entry in entries:
                        if entry['batch']:
                            cell_text += f"{entry['subject_name']}\n{entry['faculty_name']}\n({entry['batch']})\n{entry['room']}\nLab (2hrs)\n\n"
                        else:
                            cell_text += f"{entry['subject_name']}\n{entry['faculty_name']}\n\n"
                    row.append(cell_text.strip())
                else:
                    row.append('-')
                skip_next = True  # Skip next cell since this lab spans 2 hours
            else:
                # Regular theory class
                entries = organized_tt[day][slot]
                if day == 'Wednesday' and slot in ['13:30-14:30', '14:30-15:30', '15:30-16:30']:
                    row.append('Sports/\nCultural')
                elif entries:
                    cell_text = ""
                    for entry in entries:
                        if entry['batch']:
                            cell_text += f"{entry['subject_name']}\n{entry['faculty_name']}\n({entry['batch']})\n\n"
                        else:
                            cell_text += f"{entry['subject_name']}\n{entry['faculty_name']}\n\n"
                    row.append(cell_text.strip())
                else:
                    row.append('-')
        
        table_data.append(row)
    
    # Create table with proper column widths
    col_widths = [0.8*inch] + [1.1*inch]*9
    
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b35')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Day column styling
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#fff3e0')),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.HexColor('#ff6b35')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        
        # Break columns styling
        ('BACKGROUND', (3, 1), (3, -1), colors.HexColor('#fff9c4')),
        ('BACKGROUND', (6, 1), (6, -1), colors.HexColor('#fff9c4')),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (6, 1), (6, -1), 'CENTER'),
        ('FONTSIZE', (3, 1), (3, -1), 14),
        ('FONTSIZE', (6, 1), (6, -1), 14),
        
        # Data cells styling
        ('BACKGROUND', (1, 1), (-1, -1), colors.beige),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (1, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.HexColor('#ffe0b2'), colors.beige]),
    ]))
    
    elements.append(t)
    
    # Add legend
    elements.append(Spacer(1, 0.2*inch))
    legend_text = """
    <b>Important Notes:</b><br/>
    • College timings: 8:30 AM - 4:30 PM<br/>
    • Morning Break: 10:30 AM - 10:45 AM<br/>
    • Lunch Break: 12:45 PM - 1:30 PM<br/>
    • Wednesday Half Day: Sports/Cultural Activities after 12:45 PM<br/>
    • Lab sessions are 2 hours long (shown in merged cells)<br/>
    """
    legend = Paragraph(legend_text, styles['Normal'])
    elements.append(legend)
    
    doc.build(elements)
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'timetable_{section}.pdf', 
                     mimetype='application/pdf')

@app.route('/submit-feedback', methods=['POST'])
@login_required
def submit_feedback():
    message = request.form.get('message')
    feedback_type = request.form.get('type', 'feedback')
    
    conn = get_db()
    conn.execute('''
        INSERT INTO feedback (user_id, message, type)
        VALUES (?, ?, ?)
    ''', (session['user_id'], message, feedback_type))
    conn.commit()
    conn.close()
    
    flash('Feedback submitted successfully', 'success')
    return redirect(request.referrer)

@app.route('/admin/mark-feedback-resolved/<int:feedback_id>')
@admin_required
def mark_feedback_resolved(feedback_id):
    conn = get_db()
    conn.execute("UPDATE feedback SET status='resolved' WHERE id=?", (feedback_id,))
    conn.commit()
    conn.close()
    
    flash('Feedback marked as resolved', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/send-notification', methods=['POST'])
@admin_required
def send_notification():
    title = request.form.get('title')
    message = request.form.get('message')
    target_role = request.form.get('target_role', 'all')
    
    conn = get_db()
    conn.execute('''
        INSERT INTO notifications (title, message, target_role)
        VALUES (?, ?, ?)
    ''', (title, message, target_role))
    conn.commit()
    conn.close()
    
    flash('Notification sent successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/get-notifications')
@login_required
def get_notifications():
    role = session.get('role')
    conn = get_db()
    
    notifications = conn.execute('''
        SELECT * FROM notifications 
        WHERE target_role IN (?, 'all')
        ORDER BY timestamp DESC
        LIMIT 5
    ''', (role,)).fetchall()
    
    conn.close()
    
    return jsonify([dict(n) for n in notifications])

if __name__ == '__main__':
    app.run(debug=True, port=5000)