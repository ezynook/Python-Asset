from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
import requests
import pandas as pd
from datetime import datetime
import io
import os
import sqlite3
from io import BytesIO
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # เปลี่ยนเป็น secret key ที่ปลอดภัยในการ deploy จริง

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อนใช้งาน'

# Ollama API Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # สามารถเปลี่ยนเป็น model อื่นได้

# ข้อมูลจังหวัดทั้งหมดในประเทศไทย (77 จังหวัด)
PROVINCES_DATA = {
    # ภาคกลาง
    'กรุงเทพมหานคร': {'region': 'กลาง', 'multiplier': 1.8},
    'สมุทรปราการ': {'region': 'กลาง', 'multiplier': 1.4},
    'นนทบุรี': {'region': 'กลาง', 'multiplier': 1.4},
    'ปทุมธานี': {'region': 'กลาง', 'multiplier': 1.3},
    'นครปฐม': {'region': 'กลาง', 'multiplier': 1.2},
    'สมุทรสาคร': {'region': 'กลาง', 'multiplier': 1.2},
    'สมุทรสงคราม': {'region': 'กลาง', 'multiplier': 1.0},
    'พระนครศรีอยุธยา': {'region': 'กลาง', 'multiplier': 1.1},
    'อ่างทอง': {'region': 'กลาง', 'multiplier': 0.9},
    'ลพบุรี': {'region': 'กลาง', 'multiplier': 0.9},
    'สิงห์บุรี': {'region': 'กลาง', 'multiplier': 0.85},
    'ชัยนาท': {'region': 'กลาง', 'multiplier': 0.85},
    'สระบุรี': {'region': 'กลาง', 'multiplier': 1.0},
    'ชลบุรี': {'region': 'กลาง', 'multiplier': 1.3},
    'ระยอง': {'region': 'กลาง', 'multiplier': 1.2},
    'จันทบุรี': {'region': 'กลาง', 'multiplier': 1.0},
    'ตราด': {'region': 'กลาง', 'multiplier': 1.0},
    'ฉะเชิงเทรา': {'region': 'กลาง', 'multiplier': 1.0},
    'ปราจีนบุรี': {'region': 'กลาง', 'multiplier': 0.9},
    'นครนายก': {'region': 'กลาง', 'multiplier': 0.95},
    'สระแก้ว': {'region': 'กลาง', 'multiplier': 0.85},
    'กาญจนบุรี': {'region': 'กลาง', 'multiplier': 0.95},
    'สุพรรณบุรี': {'region': 'กลาง', 'multiplier': 0.9},
    'ราชบุรี': {'region': 'กลาง', 'multiplier': 0.95},
    'เพชรบุรี': {'region': 'กลาง', 'multiplier': 1.0},
    'ประจวบคีรีขันธ์': {'region': 'กลาง', 'multiplier': 1.05},

    # ภาคเหนือ
    'เชียงใหม่': {'region': 'เหนือ', 'multiplier': 1.4},
    'ลำพูน': {'region': 'เหนือ', 'multiplier': 0.9},
    'ลำปาง': {'region': 'เหนือ', 'multiplier': 0.95},
    'อุตรดิตถ์': {'region': 'เหนือ', 'multiplier': 0.85},
    'แพร่': {'region': 'เหนือ', 'multiplier': 0.85},
    'น่าน': {'region': 'เหนือ', 'multiplier': 0.85},
    'พะเยา': {'region': 'เหนือ', 'multiplier': 0.85},
    'เชียงราย': {'region': 'เหนือ', 'multiplier': 1.0},
    'แม่ฮ่องสอน': {'region': 'เหนือ', 'multiplier': 0.9},
    'นครสวรรค์': {'region': 'เหนือ', 'multiplier': 0.9},
    'อุทัยธานี': {'region': 'เหนือ', 'multiplier': 0.8},
    'กำแพงเพชร': {'region': 'เหนือ', 'multiplier': 0.85},
    'ตาก': {'region': 'เหนือ', 'multiplier': 0.85},
    'สุโขทัย': {'region': 'เหนือ', 'multiplier': 0.85},
    'พิษณุโลก': {'region': 'เหนือ', 'multiplier': 0.9},
    'พิจิตร': {'region': 'เหนือ', 'multiplier': 0.85},
    'เพชรบูรณ์': {'region': 'เหนือ', 'multiplier': 0.85},

    # ภาคตะวันออกเหนือ (อีสาน)
    'นครราชสีมา': {'region': 'อีสาน', 'multiplier': 1.0},
    'บุรีรัมย์': {'region': 'อีสาน', 'multiplier': 0.85},
    'สุรินทร์': {'region': 'อีสาน', 'multiplier': 0.85},
    'ศรีสะเกษ': {'region': 'อีสาน', 'multiplier': 0.8},
    'อุบลราชธานี': {'region': 'อีสาน', 'multiplier': 0.9},
    'ยโสธร': {'region': 'อีสาน', 'multiplier': 0.8},
    'ชัยภูมิ': {'region': 'อีสาน', 'multiplier': 0.8},
    'อำนาจเจริญ': {'region': 'อีสาน', 'multiplier': 0.75},
    'หนองบัวลำภู': {'region': 'อีสาน', 'multiplier': 0.8},
    'ขอนแก่น': {'region': 'อีสาน', 'multiplier': 0.95},
    'อุดรธานี': {'region': 'อีสาน', 'multiplier': 0.9},
    'เลย': {'region': 'อีสาน', 'multiplier': 0.8},
    'หนองคาย': {'region': 'อีสาน', 'multiplier': 0.85},
    'มหาสารคาม': {'region': 'อีสาน', 'multiplier': 0.8},
    'ร้อยเอ็ด': {'region': 'อีสาน', 'multiplier': 0.8},
    'กาฬสินธุ์': {'region': 'อีสาน', 'multiplier': 0.75},
    'สกลนคร': {'region': 'อีสาน', 'multiplier': 0.85},
    'นครพนม': {'region': 'อีสาน', 'multiplier': 0.85},
    'มุกดาหาร': {'region': 'อีสาน', 'multiplier': 0.8},
    'บึงกาฬ': {'region': 'อีสาน', 'multiplier': 0.75},

    # ภาคใต้
    'นครศรีธรรมราช': {'region': 'ใต้', 'multiplier': 0.95},
    'กระบี่': {'region': 'ใต้', 'multiplier': 1.1},
    'พังงา': {'region': 'ใต้', 'multiplier': 1.05},
    'ภูเก็ต': {'region': 'ใต้', 'multiplier': 1.5},
    'สุราษฎร์ธานี': {'region': 'ใต้', 'multiplier': 0.95},
    'ระนอง': {'region': 'ใต้', 'multiplier': 0.85},
    'ชุมพร': {'region': 'ใต้', 'multiplier': 0.9},
    'สงขลา': {'region': 'ใต้', 'multiplier': 1.0},
    'สตูล': {'region': 'ใต้', 'multiplier': 0.85},
    'ตรัง': {'region': 'ใต้', 'multiplier': 0.9},
    'พัทลุง': {'region': 'ใต้', 'multiplier': 0.85},
    'ปัตตานี': {'region': 'ใต้', 'multiplier': 0.8},
    'ยะลา': {'region': 'ใต้', 'multiplier': 0.8},
    'นราธิวาส': {'region': 'ใต้', 'multiplier': 0.8},
}

# Upload Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# สร้างโฟลเดอร์ uploads ถ้ายังไม่มี
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# เก็บข้อมูลราคาที่อัปโหลดจาก Excel
price_database = {}

# ========================================
# Database Configuration
# ========================================

DATABASE = 'PasitDev.db'

def get_db():
    """เชื่อมต่อกับ SQLite database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def getYear():
    now = datetime.now()
    return now.strftime("%Y")

def init_db():
    """สร้างตาราง users ถ้ายังไม่มี"""
    conn = get_db()
    cursor = conn.cursor()

    # สร้างตาราง users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # สร้าง admin account เริ่มต้น (email: admin@PasitDev.com, password: admin123)
    try:
        cursor.execute('''
            INSERT INTO users (email, password, full_name, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin@PasitDev.com', generate_password_hash('admin123'), 'ผู้ดูแลระบบ', 'admin'))
        conn.commit()
        print("✅ สร้าง Admin account เริ่มต้น: admin@PasitDev.com / admin123")
    except sqlite3.IntegrityError:
        pass  # Admin account มีอยู่แล้ว

    conn.close()

# เรียกใช้ init_db เมื่อเริ่มต้น app
init_db()

# ========================================
# User Model for Flask-Login
# ========================================

class User(UserMixin):
    def __init__(self, id, email, full_name, role):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    """โหลดข้อมูลผู้ใช้จาก database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        return User(
            id=user_data['id'],
            email=user_data['email'],
            full_name=user_data['full_name'],
            role=user_data['role']
        )
    return None

def admin_required(f):
    """Decorator สำหรับตรวจสอบว่าเป็น admin หรือไม่"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_admin():
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ========================================
# Helper Functions
# ========================================

def allowed_file(filename):
    """ตรวจสอบว่าไฟล์เป็น Excel หรือไม่"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_pdf_report(evaluation_data, ai_response):

    # Register Thai fonts
    pdfmetrics.registerFont(TTFont('THSarabun', 'fonts/THSarabunNew.ttf'))
    pdfmetrics.registerFont(TTFont('THSarabun-Bold', 'fonts/THSarabunNew-Bold.ttf'))

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Title Style
    styles.add(ParagraphStyle(
        name='TitleTH',
        fontName='THSarabun-Bold',
        fontSize=26,
        leading=32,       # ระยะห่างบรรทัด
        alignment=1,      # Center
        spaceAfter=20
    ))

    # Normal text
    styles.add(ParagraphStyle(
        name='BodyTH',
        fontName='THSarabun',
        fontSize=16,
        leading=22,       # บรรทัดห่างขึ้น (อ่านง่าย)
        spaceBefore=4,
        spaceAfter=4
    ))

    # Section Header
    styles.add(ParagraphStyle(
        name='SectionTH',
        fontName='THSarabun-Bold',
        fontSize=18,
        leading=24,
        spaceBefore=12,
        spaceAfter=6
    ))

    story = []

    # Title
    story.append(Paragraph("รายงานผลการประเมินราคาอสังหาริมทรัพย์", styles["TitleTH"]))
    story.append(Spacer(1, 14))

    # AI Evaluation
    story.append(Paragraph("ผลการประเมินโดย AI", styles["SectionTH"]))
    story.append(Paragraph(ai_response, styles["BodyTH"]))
    story.append(Spacer(1, 16))

    # Property Data
    story.append(Paragraph("ข้อมูลทรัพย์สิน", styles["SectionTH"]))

    for key, value in evaluation_data.items():
        story.append(Paragraph(f"<b>{key}</b>: {value}", styles["BodyTH"]))

    story.append(Spacer(1, 20))

    doc.build(story)

    buffer.seek(0)
    return buffer

def getYear():
    now = datetime.now()
    y = now.strftime("%Y")
    return y

# ========================================
# Authentication Routes
# ========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """หน้า Login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        if not email or not password:
            flash('กรุณากรอกอีเมล์และรหัสผ่าน', 'danger')
            return render_template('login.html')

        # ตรวจสอบ user ในฐานข้อมูล
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_data = cursor.fetchone()

        if user_data and check_password_hash(user_data['password'], password):
            # Login สำเร็จ
            user = User(
                id=user_data['id'],
                email=user_data['email'],
                full_name=user_data['full_name'],
                role=user_data['role']
            )
            login_user(user, remember=remember)

            # อัปเดต last_login
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                         (datetime.now(), user_data['id']))
            conn.commit()
            conn.close()

            flash(f'ยินดีต้อนรับ {user.full_name}!', 'success')

            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('อีเมล์หรือรหัสผ่านไม่ถูกต้อง', 'danger')
            conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """หน้า Register (สมัครสมาชิก)"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')

        # Validation
        if not email or not password or not full_name:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('รหัสผ่านไม่ตรงกัน', 'danger')
            return render_template('register.html')

        if len(password) < 4:
            flash('รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร', 'danger')
            return render_template('register.html')

        # ตรวจสอบว่าอีเมล์ซ้ำหรือไม่
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('อีเมล์นี้ถูกใช้งานแล้ว', 'danger')
            conn.close()
            return render_template('register.html')

        # สร้าง account ใหม่
        hashed_password = generate_password_hash(password)
        try:
            cursor.execute('''
                INSERT INTO users (email, password, full_name, role)
                VALUES (?, ?, ?, ?)
            ''', (email, hashed_password, full_name, 'user'))
            conn.commit()
            conn.close()

            flash('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('ออกจากระบบเรียบร้อย', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """เปลี่ยนรหัสผ่าน"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if not current_password or not new_password or not confirm_password:
            flash('กรุณากรอกข้อมูลให้ครบถ้วน', 'danger')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('รหัสผ่านใหม่ไม่ตรงกัน', 'danger')
            return render_template('change_password.html')

        if len(new_password) < 4:
            flash('รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร', 'danger')
            return render_template('change_password.html')

        if current_password == new_password:
            flash('รหัสผ่านใหม่ต้องไม่เหมือนรหัสผ่านเดิม', 'danger')
            return render_template('change_password.html')

        # ตรวจสอบรหัสผ่านเดิม
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE id = ?', (current_user.id,))
        user_data = cursor.fetchone()

        if not user_data or not check_password_hash(user_data['password'], current_password):
            flash('รหัสผ่านเดิมไม่ถูกต้อง', 'danger')
            conn.close()
            return render_template('change_password.html')

        # เปลี่ยนรหัสผ่าน
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password = ? WHERE id = ?',
                      (hashed_password, current_user.id))
        conn.commit()
        conn.close()

        flash('เปลี่ยนรหัสผ่านสำเร็จ!', 'success')
        return redirect(url_for('index'))

    return render_template('change_password.html')

@app.route('/admin')
@admin_required
def admin():
    """หน้า Admin Panel - จัดการผู้ใช้"""
    conn = get_db()
    cursor = conn.cursor()

    # ดึงข้อมูลผู้ใช้ทั้งหมด
    cursor.execute('''
        SELECT id, email, full_name, role, created_at, last_login
        FROM users
        ORDER BY created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """ลบผู้ใช้ (Admin เท่านั้น)"""
    if user_id == current_user.id:
        flash('ไม่สามารถลบบัญชีตัวเองได้', 'danger')
        return redirect(url_for('admin'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    flash('ลบผู้ใช้เรียบร้อย', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/toggle-role/<int:user_id>', methods=['POST'])
@admin_required
def toggle_role(user_id):
    """เปลี่ยน Role ผู้ใช้ระหว่าง user และ admin"""
    if user_id == current_user.id:
        flash('ไม่สามารถเปลี่ยน role ของตัวเองได้', 'danger')
        return redirect(url_for('admin'))

    conn = get_db()
    cursor = conn.cursor()

    # ดึง role ปัจจุบัน
    cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        current_role = user_data['role']
        new_role = 'admin' if current_role == 'user' else 'user'

        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        flash(f'เปลี่ยน Role เป็น {new_role} เรียบร้อย', 'success')

    conn.close()
    return redirect(url_for('admin'))

# ========================================
# Main Routes
# ========================================

@app.route('/')
@login_required
def index():
    y = getYear()
    return render_template('index.html', year=y, user=current_user)

@app.route('/api/provinces', methods=['GET'])
def get_provinces():
    """
    API สำหรับดึงข้อมูลจังหวัดทั้งหมด
    """
    provinces_list = []
    for province, data in PROVINCES_DATA.items():
        provinces_list.append({
            'name': province,
            'region': data['region'],
            'multiplier': data['multiplier']
        })

    # เรียงตามชื่อจังหวัด
    provinces_list.sort(key=lambda x: x['name'])

    return jsonify({
        'success': True,
        'provinces': provinces_list,
        'total': len(provinces_list)
    })

@app.route('/api/evaluate', methods=['POST'])
def evaluate_property():
    """
    API สำหรับประเมินราคาทรัพย์สินโดยใช้ AI
    """
    try:
        data = request.get_json()

        # ดึงข้อมูลจาก request
        property_type = data.get('property_type', '')
        location = data.get('location', '')
        area = data.get('area', '')
        bedrooms = data.get('bedrooms', '')
        bathrooms = data.get('bathrooms', '')
        age = data.get('age', '')
        condition = data.get('condition', '')
        additional_info = data.get('additional_info', '')

        # สร้าง prompt สำหรับ AI
        prompt = f"""คุณเป็นผู้เชี่ยวชาญด้านการประเมินราคาอสังหาริมทรัพย์ในประเทศไทย กรุณาประเมินราคาทรัพย์สินตามข้อมูลต่อไปนี้:

ประเภททรัพย์สิน: {property_type}
ทำเลที่ตั้ง: {location}
ขนาดพื้นที่: {area} ตารางเมตร
จำนวนห้องนอน: {bedrooms} ห้อง
จำนวนห้องน้ำ: {bathrooms} ห้อง
อายุอาคาร: {age} ปี
สภาพทรัพย์สิน: {condition}
ข้อมูลเพิ่มเติม: {additional_info}

กรุณาวิเคราะห์และให้คำแนะนำเกี่ยวกับ:
1. ราคาประเมินโดยประมาณ (บาท)
2. ปัจจัยที่ส่งผลต่อราคา
3. แนวโน้มตลาดในพื้นที่
4. คำแนะนำสำหรับผู้ซื้อหรือผู้ขาย

โปรดตอบเป็นภาษาไทยและให้รายละเอียดที่ชัดเจน"""

        # เรียก Ollama API
        ollama_response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if ollama_response.status_code == 200:
            ai_result = ollama_response.json()
            ai_response = ai_result.get('response', '')

            return jsonify({
                'success': True,
                'evaluation': ai_response,
                'property_data': {
                    'property_type': property_type,
                    'location': location,
                    'area': area,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'age': age,
                    'condition': condition
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'ไม่สามารถเชื่อมต่อกับ AI ได้'
            }), 500

    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'ไม่สามารถเชื่อมต่อกับ Ollama ได้ กรุณาตรวจสอบว่า Ollama กำลังทำงานอยู่ที่ localhost:11434'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@app.route('/api/quick-estimate', methods=['POST'])
def quick_estimate():
    """
    API สำหรับประมาณราคาแบบเร็ว (ไม่ใช้ AI)
    รองรับการเลือกจังหวัดจากข้อมูล 77 จังหวัด
    """
    try:
        data = request.get_json()

        property_type = data.get('property_type', '')
        area = float(data.get('area', 0))
        province = data.get('province', '')

        # ราคาต่อตารางเมตรโดยประมาณ (หน่วย: บาท)
        base_prices = {
            'คอนโด': 50000,
            'บ้านเดี่ยว': 35000,
            'ทาวน์เฮาส์': 30000,
            'อาคารพาณิชย์': 40000,
            'ที่ดิน': 15000
        }

        # ดึงตัวคูณจากข้อมูลจังหวัด
        location_multiplier = 1.0
        province_info = None

        if province in PROVINCES_DATA:
            province_info = PROVINCES_DATA[province]
            location_multiplier = province_info['multiplier']
        else:
            # ถ้าไม่พบจังหวัด ให้ใช้ค่า default
            location_multiplier = 1.0

        base_price = base_prices.get(property_type, 30000)
        estimated_price = area * base_price * location_multiplier
        price_per_sqm = base_price * location_multiplier

        response_data = {
            'success': True,
            'estimated_price': estimated_price,
            'price_per_sqm': price_per_sqm,
            'area': area,
            'province': province
        }

        # เพิ่มข้อมูลภูมิภาคถ้ามี
        if province_info:
            response_data['region'] = province_info['region']
            response_data['multiplier'] = location_multiplier

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@app.route('/api/check-ollama', methods=['GET'])
def check_ollama():
    """
    ตรวจสอบการเชื่อมต่อกับ Ollama
    """
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return jsonify({
                'success': True,
                'connected': True,
                'models': [model['name'] for model in models]
            })
        else:
            return jsonify({
                'success': False,
                'connected': False
            })
    except:
        return jsonify({
            'success': False,
            'connected': False,
            'error': 'ไม่สามารถเชื่อมต่อกับ Ollama ได้'
        })

@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    """
    API สำหรับดาวน์โหลดรายงาน PDF
    """
    try:
        data = request.get_json()
        evaluation_data = data.get('property_data', {})
        ai_response = data.get('evaluation', '')

        if not evaluation_data or not ai_response:
            return jsonify({
                'success': False,
                'error': 'ข้อมูลไม่ครบถ้วน'
            }), 400

        # สร้าง PDF
        pdf_buffer = generate_pdf_report(evaluation_data, ai_response)

        # ส่งไฟล์ PDF
        filename = f"property_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@app.route('/api/upload-price-data', methods=['POST'])
def upload_price_data():
    """
    API สำหรับอัปโหลดข้อมูลราคาจาก Excel
    รูปแบบไฟล์: province, property_type, base_price_per_sqm
    """
    try:
        # ตรวจสอบว่ามีไฟล์หรือไม่
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'ไม่พบไฟล์ที่อัปโหลด'
            }), 400

        file = request.files['file']

        # ตรวจสอบว่ามีชื่อไฟล์หรือไม่
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'ไม่ได้เลือกไฟล์'
            }), 400

        # ตรวจสอบประเภทไฟล์
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'รองรับเฉพาะไฟล์ .xlsx, .xls, .csv เท่านั้น'
            }), 400

        # อ่านไฟล์ Excel
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'ไม่สามารถอ่านไฟล์ได้: {str(e)}'
            }), 400

        # ตรวจสอบ columns ที่จำเป็น
        required_columns = ['province', 'property_type', 'base_price_per_sqm']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return jsonify({
                'success': False,
                'error': f'ขาด columns: {", ".join(missing_columns)}',
                'required_columns': required_columns
            }), 400

        # อัปเดตฐานข้อมูลราคา
        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                province = str(row['province']).strip()
                property_type = str(row['property_type']).strip()
                base_price = float(row['base_price_per_sqm'])

                # สร้าง key
                key = f"{province}_{property_type}"
                price_database[key] = {
                    'province': province,
                    'property_type': property_type,
                    'base_price_per_sqm': base_price
                }
                updated_count += 1

            except Exception as e:
                errors.append(f"แถว {index + 2}: {str(e)}")

        response_data = {
            'success': True,
            'message': f'อัปโหลดสำเร็จ {updated_count} รายการ',
            'updated_count': updated_count,
            'total_records': len(price_database)
        }

        if errors:
            response_data['errors'] = errors
            response_data['error_count'] = len(errors)

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@app.route('/api/get-price-data', methods=['GET'])
def get_price_data():
    """
    API สำหรับดึงข้อมูลราคาที่อัปโหลดไว้
    """
    try:
        # แปลงเป็น list
        price_list = list(price_database.values())

        return jsonify({
            'success': True,
            'data': price_list,
            'total': len(price_list)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@app.route('/api/download-template', methods=['GET'])
def download_template():
    """
    ดาวน์โหลดไฟล์ Excel template สำหรับอัปโหลดข้อมูลราคา
    """
    try:
        # สร้าง sample data
        sample_data = {
            'province': ['กรุงเทพมหานคร', 'เชียงใหม่', 'ภูเก็ต'],
            'property_type': ['คอนโด', 'บ้านเดี่ยว', 'คอนโด'],
            'base_price_per_sqm': [80000, 45000, 70000]
        }

        df = pd.DataFrame(sample_data)

        # สร้าง Excel ใน memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='ข้อมูลราคา')

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='price_data_template.xlsx'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("ระบบประเมินราคาทรัพย์สิน - มั่นใจ")
    print("=" * 60)
    print("เริ่มต้นเซิร์ฟเวอร์ที่: http://localhost:5000")
    print("กรุณาตรวจสอบว่า Ollama กำลังทำงานที่: http://localhost:11434")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=8089)
