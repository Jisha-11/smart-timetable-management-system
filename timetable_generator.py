import sqlite3
import random
from collections import defaultdict

class TimetableGenerator:
    def __init__(self):
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        # Time slots (1 hour each)
        self.theory_slots = {
            'Monday': ['08:30-09:30', '09:30-10:30', '10:45-11:45', '11:45-12:45', '13:30-14:30', '14:30-15:30', '15:30-16:30'],
            'Tuesday': ['08:30-09:30', '09:30-10:30', '10:45-11:45', '11:45-12:45', '13:30-14:30', '14:30-15:30', '15:30-16:30'],
            'Wednesday': ['08:30-09:30', '09:30-10:30', '10:45-11:45', '11:45-12:45'],  # Half day
            'Thursday': ['08:30-09:30', '09:30-10:30', '10:45-11:45', '11:45-12:45', '13:30-14:30', '14:30-15:30', '15:30-16:30'],
            'Friday': ['08:30-09:30', '09:30-10:30', '10:45-11:45', '11:45-12:45', '13:30-14:30', '14:30-15:30', '15:30-16:30'],
        }
        
        # Lab slots (2 hours each)
        self.lab_slots = {
            'Monday': ['08:30-10:30', '10:45-12:45', '13:30-15:30'],
            'Tuesday': ['08:30-10:30', '10:45-12:45', '13:30-15:30'],
            'Wednesday': ['08:30-10:30', '10:45-12:45'],  # Half day
            'Thursday': ['08:30-10:30', '10:45-12:45', '13:30-15:30'],
            'Friday': ['08:30-10:30', '10:45-12:45', '13:30-15:30'],
        }
        
    def generate_timetable(self, section):
        """Generate timetable for a given section"""
        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()
        
        # Clear existing timetable for this section
        cursor.execute('DELETE FROM timetable WHERE section = ?', (section,))
        
        # Get semester from section
        semester = int(section[0])
        
        # Get subjects for this section
        cursor.execute('''
            SELECT s.id, s.name, s.code, s.type, s.theory_hours, s.lab_hours, 
                   sf.faculty_id, f.name as faculty_name
            FROM subjects s
            JOIN subject_faculty sf ON s.id = sf.subject_id
            JOIN faculties f ON sf.faculty_id = f.id
            WHERE s.semester = ? AND sf.section = ?
        ''', (semester, section))
        
        subjects = cursor.fetchall()
        
        if not subjects:
            conn.close()
            return False, "No subjects found for this section"
        
        # Get available labs
        cursor.execute('SELECT id, name FROM labs')
        labs = cursor.fetchall()
        
        # Initialize tracking
        faculty_schedule = defaultdict(lambda: defaultdict(set))
        section_schedule = defaultdict(set)
        lab_schedule = defaultdict(lambda: defaultdict(set))
        
        # Separate subjects by type
        lab_subjects = [s for s in subjects if s[5] > 0]  # Has lab hours
        theory_subjects = [s for s in subjects if s[4] > 0]  # Has theory hours
        
        # First allocate labs (more constrained)
        if lab_subjects:
            success = self._allocate_labs_rotation(cursor, section, lab_subjects, labs, 
                                         faculty_schedule, section_schedule, lab_schedule)
            if not success:
                conn.close()
                return False, "Failed to allocate lab sessions"
        
        # Then allocate theory classes to FILL ALL REMAINING SLOTS
        if theory_subjects:
            success = self._allocate_theory_fill_all(cursor, section, theory_subjects, 
                                                    faculty_schedule, section_schedule)
            if not success:
                conn.close()
                return False, "Failed to allocate theory classes"
        
        conn.commit()
        conn.close()
        return True, "Timetable generated successfully"
    
    def _allocate_labs_rotation(self, cursor, section, lab_subjects, labs, faculty_schedule, 
                               section_schedule, lab_schedule):
        """
        Allocate labs with ROTATION:
        - All 3 batches have lab at SAME TIME
        - Each batch has DIFFERENT subject
        - Over the week, all batches cover all subjects
        """
        
        num_batches = 3
        batch_names = [f"{section[0]}{i+1}" for i in range(num_batches)]
        
        # Track which subjects each batch has completed
        batch_completed_labs = {batch: set() for batch in batch_names}
        
        # Calculate how many lab sessions we need
        num_lab_subjects = len(lab_subjects)
        
        # We need enough lab sessions so all batches complete all subjects
        num_sessions_needed = num_lab_subjects
        
        sessions_allocated = 0
        
        # Try to allocate lab sessions
        attempts = 0
        max_attempts = 200
        
        while sessions_allocated < num_sessions_needed and attempts < max_attempts:
            attempts += 1
            
            # Pick random day and lab slot
            day = random.choice(self.days)
            available_slots = self.lab_slots[day]
            
            if not available_slots:
                continue
            
            lab_slot = random.choice(available_slots)
            
            # Check if section already has something during this time
            slot_conflict = False
            if lab_slot == '08:30-10:30':
                if '08:30-09:30' in section_schedule[day] or '09:30-10:30' in section_schedule[day] or '08:30-10:30' in section_schedule[day]:
                    slot_conflict = True
            elif lab_slot == '10:45-12:45':
                if '10:45-11:45' in section_schedule[day] or '11:45-12:45' in section_schedule[day] or '10:45-12:45' in section_schedule[day]:
                    slot_conflict = True
            elif lab_slot == '13:30-15:30':
                if '13:30-14:30' in section_schedule[day] or '14:30-15:30' in section_schedule[day] or '13:30-15:30' in section_schedule[day]:
                    slot_conflict = True
            
            if slot_conflict:
                continue
            
            # Find 3 different subjects for the 3 batches
            selected_subjects = []
            selected_faculties = set()
            
            for batch_idx in range(num_batches):
                batch = batch_names[batch_idx]
                
                # Find a subject this batch hasn't done yet
                available_subjects = []
                for subj in lab_subjects:
                    subj_id, name, code, subj_type, theory_hours, lab_hours, faculty_id, faculty_name = subj
                    
                    # Check if batch hasn't done this subject yet
                    if subj_id not in batch_completed_labs[batch]:
                        # Check if faculty is available
                        if faculty_id not in selected_faculties and lab_slot not in faculty_schedule[faculty_id][day]:
                            available_subjects.append(subj)
                
                if available_subjects:
                    # Pick one subject
                    chosen = random.choice(available_subjects)
                    selected_subjects.append(chosen)
                    selected_faculties.add(chosen[6])  # faculty_id
                elif len(lab_subjects) > 0:
                    # If batch has done all subjects, repeat one
                    available_subjects = []
                    for subj in lab_subjects:
                        subj_id, name, code, subj_type, theory_hours, lab_hours, faculty_id, faculty_name = subj
                        if faculty_id not in selected_faculties and lab_slot not in faculty_schedule[faculty_id][day]:
                            available_subjects.append(subj)
                    
                    if available_subjects:
                        chosen = random.choice(available_subjects)
                        selected_subjects.append(chosen)
                        selected_faculties.add(chosen[6])
            
            # Need exactly 3 subjects (one per batch)
            if len(selected_subjects) != 3:
                continue
            
            # Find 3 available lab rooms
            available_labs = []
            for lab in labs:
                lab_id, lab_name = lab
                if lab_slot not in lab_schedule[lab_name][day]:
                    available_labs.append((lab_id, lab_name))
            
            if len(available_labs) < 3:
                continue
            
            # SUCCESS! Allocate all 3 batches with different subjects
            for batch_idx in range(3):
                batch = batch_names[batch_idx]
                subject = selected_subjects[batch_idx]
                lab_id, lab_name = available_labs[batch_idx]
                
                subj_id, name, code, subj_type, theory_hours, lab_hours, faculty_id, faculty_name = subject
                
                cursor.execute('''
                    INSERT INTO timetable (section, day, time_slot, subject_id, 
                                         faculty_id, room, batch, is_lab)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (section, day, lab_slot, subj_id, faculty_id, lab_name, batch))
                
                # Mark resources as busy
                lab_schedule[lab_name][day].add(lab_slot)
                faculty_schedule[faculty_id][day].add(lab_slot)
                
                # Track that this batch completed this subject
                batch_completed_labs[batch].add(subj_id)
            
            # Mark section time as busy
            section_schedule[day].add(lab_slot)
            
            # Block individual hour slots
            if lab_slot == '08:30-10:30':
                section_schedule[day].add('08:30-09:30')
                section_schedule[day].add('09:30-10:30')
            elif lab_slot == '10:45-12:45':
                section_schedule[day].add('10:45-11:45')
                section_schedule[day].add('11:45-12:45')
            elif lab_slot == '13:30-15:30':
                section_schedule[day].add('13:30-14:30')
                section_schedule[day].add('14:30-15:30')
            
            sessions_allocated += 1
        
        # Check if all batches got all subjects at least once
        for batch in batch_names:
            if len(batch_completed_labs[batch]) < num_lab_subjects:
                print(f"Warning: Batch {batch} only completed {len(batch_completed_labs[batch])}/{num_lab_subjects} lab subjects")
        
        return True
    
    def _allocate_theory_fill_all(self, cursor, section, theory_subjects, faculty_schedule, section_schedule):
        """Allocate theory classes to FILL ALL EMPTY SLOTS - NO CONSECUTIVE SAME TEACHER"""
        
        # Track what was taught in previous slot for each day
        previous_slot_subject = {}  # day -> (subject_id, faculty_id)
        
        # First, allocate the required hours for each subject
        theory_slots_needed = []
        
        for subject in theory_subjects:
            subj_id, name, code, subj_type, theory_hours, lab_hours, faculty_id, faculty_name = subject
            
            for _ in range(theory_hours):
                theory_slots_needed.append({
                    'subject_id': subj_id,
                    'faculty_id': faculty_id,
                    'name': name
                })
        
        random.shuffle(theory_slots_needed)
        
        # Define consecutive slot pairs
        consecutive_pairs = {
            '08:30-09:30': '09:30-10:30',
            '09:30-10:30': '08:30-09:30',
            '10:45-11:45': '11:45-12:45',
            '11:45-12:45': '10:45-11:45',
            '13:30-14:30': '14:30-15:30',
            '14:30-15:30': '13:30-14:30',
            '15:30-16:30': '14:30-15:30',
        }
        
        # Allocate required theory slots
        for slot_info in theory_slots_needed:
            allocated = False
            attempts = 0
            max_attempts = 100
            
            while not allocated and attempts < max_attempts:
                attempts += 1
                
                day = random.choice(self.days)
                available_slots = self.theory_slots[day]
                
                if not available_slots:
                    continue
                
                time_slot = random.choice(available_slots)
                
                # Check if faculty is free
                if time_slot in faculty_schedule[slot_info['faculty_id']][day]:
                    continue
                
                # Check if section is free
                if time_slot in section_schedule[day]:
                    continue
                
                # NEW: Check if previous consecutive slot has same teacher
                if time_slot in consecutive_pairs:
                    adjacent_slot = consecutive_pairs[time_slot]
                    key = f"{day}_{adjacent_slot}"
                    if key in previous_slot_subject:
                        prev_faculty = previous_slot_subject[key]
                        if prev_faculty == slot_info['faculty_id']:
                            # Same teacher in consecutive slot, skip this
                            continue
                
                # Allocate the slot
                cursor.execute('''
                    INSERT INTO timetable (section, day, time_slot, subject_id, 
                                         faculty_id, room, batch, is_lab)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ''', (section, day, time_slot, slot_info['subject_id'], 
                      slot_info['faculty_id'], 'Classroom', None))
                
                faculty_schedule[slot_info['faculty_id']][day].add(time_slot)
                section_schedule[day].add(time_slot)
                
                # Track this slot's teacher
                key = f"{day}_{time_slot}"
                previous_slot_subject[key] = slot_info['faculty_id']
                
                allocated = True
        
        # NOW FILL ALL REMAINING EMPTY SLOTS - also avoid consecutive same teacher
        subject_cycle = []
        for subject in theory_subjects:
            subj_id, name, code, subj_type, theory_hours, lab_hours, faculty_id, faculty_name = subject
            subject_cycle.append({
                'subject_id': subj_id,
                'faculty_id': faculty_id,
                'name': name
            })
        
        if not subject_cycle:
            return True
        
        cycle_index = 0
        
        # Go through all days and slots to find empty ones
        for day in self.days:
            for time_slot in self.theory_slots[day]:
                # If slot is empty, fill it
                if time_slot not in section_schedule[day]:
                    # Cycle through subjects to find one whose faculty is free AND not consecutive
                    attempts = 0
                    while attempts < len(subject_cycle) * 3:
                        slot_info = subject_cycle[cycle_index % len(subject_cycle)]
                        cycle_index += 1
                        attempts += 1
                        
                        # Check if this faculty is available
                        if time_slot in faculty_schedule[slot_info['faculty_id']][day]:
                            continue
                        
                        # NEW: Check consecutive slots
                        if time_slot in consecutive_pairs:
                            adjacent_slot = consecutive_pairs[time_slot]
                            key = f"{day}_{adjacent_slot}"
                            if key in previous_slot_subject:
                                prev_faculty = previous_slot_subject[key]
                                if prev_faculty == slot_info['faculty_id']:
                                    # Same teacher in consecutive slot, try next subject
                                    continue
                        
                        # Allocate it!
                        cursor.execute('''
                            INSERT INTO timetable (section, day, time_slot, subject_id, 
                                                 faculty_id, room, batch, is_lab)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        ''', (section, day, time_slot, slot_info['subject_id'], 
                              slot_info['faculty_id'], 'Classroom', None))
                        
                        faculty_schedule[slot_info['faculty_id']][day].add(time_slot)
                        section_schedule[day].add(time_slot)
                        
                        # Track this slot's teacher
                        key = f"{day}_{time_slot}"
                        previous_slot_subject[key] = slot_info['faculty_id']
                        
                        break
        
        return True

def generate_all_timetables():
    """Generate timetables for all sections"""
    sections = ['3A', '3B', '3C', '3D', '5A', '5B', '5C', '7A', '7B', '7C']
    generator = TimetableGenerator()
    
    results = {}
    for section in sections:
        success, message = generator.generate_timetable(section)
        results[section] = {'success': success, 'message': message}
        if success:
            print(f"✓ Timetable generated for {section}")
        else:
            print(f"✗ Failed to generate timetable for {section}: {message}")
    
    return results