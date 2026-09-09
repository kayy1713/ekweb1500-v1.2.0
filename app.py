from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import base64
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "english_tracker_super_secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///english_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    students = db.Column(db.Text, default="") # Öğretmenler için virgülle ayrılmış öğrenci isimleri

class Assignment(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    teacher = db.Column(db.String(100), nullable=False)
    student = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)

class Submission(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    assignment_id = db.Column(db.String(36), nullable=False)
    student = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100), nullable=False)
    image_b64 = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(36), nullable=False)
    student = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100), nullable=False)
    annotated_image = db.Column(db.Text, nullable=False)
    score = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(50), nullable=False)

class HwStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(100), nullable=False)
    assignment_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(20), default="not_started")
    est_date = db.Column(db.String(50))
    days_str = db.Column(db.String(50))

# Veritabanı tablolarını oluştur
with app.app_context():
    db.create_all()

# --- HTML TEMPLATES ---

BASE_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>English Tracker Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: { 50: '#eff6ff', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8' },
                        darkbg: '#0f172a',
                        darkcard: '#1e293b',
                        darkborder: '#334155'
                    }
                }
            }
        }
        function toggleTheme() {
            document.documentElement.classList.toggle('dark');
        }
    </script>
    <style>
        body { transition: background-color 0.3s, color 0.3s; }
        .canvas-container { position: relative; display: inline-block; }
    </style>
</head>
<body class="bg-gray-50 text-gray-900 dark:bg-darkbg dark:text-gray-100 font-sans antialiased min-h-screen flex flex-col">

    {% if not session.get('user') %}
    <!-- LANDING & AUTH PAGE -->
    <div class="flex-grow flex flex-col items-center justify-center p-4 bg-gradient-to-br from-blue-900/20 via-darkbg to-slate-900">
        <div class="text-center mb-8">
            <h1 class="text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500 mb-2">English Tracker</h1>
            <p class="text-gray-400 text-sm">Interactive Learning & Assignment Platform</p>
        </div>
        
        <div class="bg-white dark:bg-darkcard shadow-2xl rounded-2xl p-8 w-full max-w-md border border-gray-200 dark:border-darkborder relative backdrop-blur-sm">
            <div class="flex justify-center space-x-3 mb-8" id="roleSelection">
                <button onclick="showAuth('teacher')" class="w-1/2 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition-all transform hover:-translate-y-0.5 shadow-lg shadow-blue-500/30">Teacher Portal</button>
                <button onclick="showAuth('student')" class="w-1/2 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-all transform hover:-translate-y-0.5 shadow-lg shadow-emerald-500/30">Student Portal</button>
            </div>

            <div id="authForms" class="hidden">
                <div class="flex justify-between border-b border-gray-200 dark:border-darkborder mb-6 pb-2">
                    <button onclick="switchTab('login')" id="tabLogin" class="text-blue-500 font-bold px-4 border-b-2 border-blue-500 pb-1">Log In</button>
                    <button onclick="switchTab('signup')" id="tabSignup" class="text-gray-400 px-4 pb-1">Sign Up</button>
                </div>

                <p id="roleTitle" class="text-center text-xs font-bold text-blue-400 uppercase tracking-widest mb-4"></p>

                <form id="loginForm" method="POST" action="/auth" class="space-y-4">
                    <input type="hidden" name="action" value="login">
                    <input type="hidden" name="role" id="loginRole">
                    <input type="text" name="name_surname" placeholder="Full Name" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none transition">
                    <input type="password" name="password" placeholder="Password" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none transition">
                    <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition shadow-lg shadow-blue-500/25">Log In</button>
                </form>

                <form id="signupForm" method="POST" action="/auth" class="hidden space-y-4">
                    <input type="hidden" name="action" value="signup">
                    <input type="hidden" name="role" id="signupRole">
                    <input type="text" name="name_surname" placeholder="Full Name" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none transition">
                    <input type="password" name="password" placeholder="Password" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none transition">
                    <textarea name="students" id="teacherStudents" placeholder="Enter Student Names (Comma separated)" class="hidden w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none transition"></textarea>
                    <button type="submit" class="w-full py-3 bg-slate-800 hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 text-white rounded-xl font-bold transition">Sign Up</button>
                </form>
            </div>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-sm text-center">
                {% for message in messages %}{{ message }}{% endfor %}
                </div>
              {% endif %}
            {% endwith %}
        </div>
    </div>
    
    <script>
        function showAuth(role) {
            document.getElementById('roleSelection').classList.add('hidden');
            document.getElementById('authForms').classList.remove('hidden');
            document.getElementById('loginRole').value = role;
            document.getElementById('signupRole').value = role;
            document.getElementById('roleTitle').innerText = role === 'teacher' ? '• Teacher Portal •' : '• Student Portal •';
            if (role === 'teacher') document.getElementById('teacherStudents').classList.remove('hidden');
            else document.getElementById('teacherStudents').classList.add('hidden');
        }
        function switchTab(tab) {
            if(tab === 'login') {
                document.getElementById('loginForm').classList.remove('hidden');
                document.getElementById('signupForm').classList.add('hidden');
                document.getElementById('tabLogin').className = 'text-blue-500 font-bold px-4 border-b-2 border-blue-500 pb-1';
                document.getElementById('tabSignup').className = 'text-gray-400 px-4 pb-1';
            } else {
                document.getElementById('signupForm').classList.remove('hidden');
                document.getElementById('loginForm').classList.add('hidden');
                document.getElementById('tabSignup').className = 'text-blue-500 font-bold px-4 border-b-2 border-blue-500 pb-1';
                document.getElementById('tabLogin').className = 'text-gray-400 px-4 pb-1';
            }
        }
    </script>

    {% else %}
    <!-- DASHBOARD -->
    <div class="flex flex-grow h-screen overflow-hidden">
        <aside class="w-64 bg-white dark:bg-darkcard border-r border-gray-200 dark:border-darkborder flex flex-col shadow-xl z-10">
            <div class="p-6 border-b border-gray-200 dark:border-darkborder">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-black text-xl shadow-lg shadow-blue-500/30">ET</div>
                    <div>
                        <h2 class="text-lg font-bold leading-tight">English Tracker</h2>
                        <span class="text-xs text-blue-500 font-medium">v1.3.0 DB</span>
                    </div>
                </div>
            </div>
            
            <nav class="flex-grow p-4 space-y-1.5 overflow-y-auto">
                <div class="mb-4 p-3 bg-gray-100 dark:bg-slate-800/60 rounded-xl text-xs font-semibold text-gray-500 dark:text-gray-400 flex items-center justify-between">
                    <span>User:</span>
                    <span class="text-blue-500 font-bold">{{ session['user_name'] }}</span>
                </div>
                
                <a href="/home" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'home' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                    <span>🏠 Home</span>
                </a>
                <a href="/lessons" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'lessons' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                    <span>📚 Lessons</span>
                </a>

                {% if session['role'] == 'teacher' %}
                    <a href="/teacher/assign" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'assign' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                        <span>📝 Assign HW</span>
                    </a>
                    <a href="/teacher/check" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'check' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                        <span>🎨 Check HW</span>
                    </a>
                {% else %}
                    <a href="/student/homework" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'homework' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                        <span>⏳ My Assignments</span>
                    </a>
                    <a href="/student/submit" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'submit' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                        <span>📤 Submit HW</span>
                    </a>
                    <a href="/student/evaluations" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'evaluations' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                        <span>⭐ Evaluations</span>
                    </a>
                {% endif %}
                
                <a href="/settings" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition-all {% if active_page == 'settings' %}bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30{% else %}hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-600 dark:text-gray-300{% endif %}">
                    <span>⚙️ Settings</span>
                </a>
            </nav>
            
            <div class="p-4 border-t border-gray-200 dark:border-darkborder">
                <a href="/logout" class="block w-full text-center py-2.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 rounded-xl font-bold transition">Log Out</a>
            </div>
        </aside>

        <main class="flex-grow p-8 overflow-y-auto relative bg-gray-50/50 dark:bg-darkbg">
            <div class="max-w-5xl mx-auto">
                {{ content | safe }}
            </div>
        </main>
    </div>
    {% endif %}
</body>
</html>
"""

PAGE_HOME = """
<div class="flex justify-between items-center mb-8">
    <div>
        <h2 class="text-3xl font-extrabold tracking-tight">Dashboard Overview</h2>
        <p class="text-gray-500 text-sm mt-1">Welcome back! Here is your quick status update.</p>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder">
        <h3 class="text-lg font-bold mb-4 text-blue-500 flex items-center space-x-2">
            <span>📅</span> <span>Upcoming Schedule</span>
        </h3>
        <div class="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
            <p class="font-bold text-blue-400">General English Class</p>
            <p class="text-sm text-gray-400 mt-1">Every Wednesday at 18:00</p>
        </div>
    </div>
    
    <div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder">
        <h3 class="text-lg font-bold mb-4 text-emerald-500 flex items-center space-x-2">
            <span>🔔</span> <span>Live Activity & Notifications</span>
        </h3>
        <div class="space-y-3 max-h-72 overflow-y-auto pr-1">
            {% if session['role'] == 'teacher' %}
                {% for n in teacher_notifications %}
                    <div class="p-3.5 rounded-xl border-l-4 text-sm transition-all {% if loop.first %}bg-blue-500/10 border-blue-500 shadow-md{% else %}bg-slate-800/60 border-slate-600 opacity-80{% endif %}">
                        <p class="font-semibold {% if loop.first %}text-blue-400 font-bold{% else %}text-slate-300{% endif %}">
                            {{ n.text }}
                        </p>
                        <span class="text-xs text-gray-500 mt-1 block">{{ n.date }}</span>
                    </div>
                {% else %}
                    <p class="text-sm text-gray-500 italic">No notifications yet.</p>
                {% endfor %}
            {% else %}
                <p class="text-sm text-gray-400">Track your homework status from the "My Assignments" menu.</p>
            {% endif %}
        </div>
    </div>
</div>
"""

PAGE_LESSONS = """
<h2 class="text-3xl font-extrabold mb-6">Schedule & Class Routine</h2>
<div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder">
    <div class="flex items-center space-x-4 p-4 border-b border-gray-200 dark:border-darkborder">
        <div class="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center text-2xl font-bold">📚</div>
        <div>
            <h4 class="text-xl font-bold">Weekly Speaking & Grammar Sync</h4>
            <p class="text-gray-400 text-sm">Wednesdays • 18:00 PM</p>
        </div>
    </div>
    <div class="p-4 mt-2 text-sm text-gray-400 leading-relaxed">
        Make sure to start and submit your homework before the weekly lesson begins. Teachers review submissions dynamically.
    </div>
</div>
"""

PAGE_SETTINGS = """
<h2 class="text-3xl font-extrabold mb-6">Settings</h2>
<div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder max-w-lg">
    <div class="mb-8 border-b border-gray-200 dark:border-darkborder pb-6">
        <h3 class="text-lg font-bold mb-3">Theme</h3>
        <button onclick="toggleTheme()" class="px-5 py-2.5 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 text-gray-800 dark:text-white rounded-xl font-bold transition">
            Toggle Light / Dark Mode 🌗
        </button>
    </div>

    <div>
        <h3 class="text-lg font-bold mb-4">Account Profile</h3>
        <form method="POST" action="/update_account" class="space-y-4">
            <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Full Name</label>
                <input type="text" name="new_name" value="{{ session['user_name'] }}" required class="w-full px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
            </div>
            <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">New Password (Optional)</label>
                <input type="password" name="new_password" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
            </div>
            <button type="submit" class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition">Save Updates</button>
        </form>
    </div>
</div>
"""

PAGE_ASSIGN = """
<h2 class="text-3xl font-extrabold mb-6">Assign New Homework</h2>
<div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder max-w-2xl">
    <form method="POST" action="/teacher/assign" class="space-y-5">
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Select Student</label>
            <select name="student_id" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="" disabled selected>-- Select a registered student --</option>
                {% for st in students %}
                    <option value="{{ st }}">{{ st }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Assignment Instructions</label>
            <textarea name="text" rows="5" required placeholder="Write clear instructions, topics, or questions..." class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none"></textarea>
        </div>
        <button type="submit" class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition shadow-lg shadow-blue-500/25">Send Assignment</button>
    </form>
</div>
"""

PAGE_CHECK = """
<h2 class="text-3xl font-extrabold mb-6">Check Submissions & Annotate</h2>
<div class="space-y-8">
    {% for sub in pending_submissions %}
    <div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder">
        <div class="flex justify-between items-center mb-4 pb-3 border-b border-gray-200 dark:border-darkborder">
            <div>
                <span class="text-xs font-bold text-blue-500 uppercase tracking-widest">Student Submission</span>
                <h3 class="text-xl font-black text-gray-100">{{ sub.student }}</h3>
            </div>
            <span class="text-xs bg-slate-800 text-gray-400 px-3 py-1 rounded-lg font-mono">Assignment ID: {{ sub.assignment_id }}</span>
        </div>
        
        <div class="mb-6 p-4 bg-slate-900 rounded-2xl border border-darkborder">
            <div class="flex flex-wrap items-center justify-between gap-4 mb-3 p-2 bg-slate-800 rounded-xl">
                <div class="flex items-center space-x-2">
                    <span class="text-xs font-bold text-gray-400">Color:</span>
                    <button type="button" onclick="setTool('pen', '#ef4444', '{{ sub.id }}')" class="w-6 h-6 rounded-full bg-red-500 border-2 border-white/20 hover:scale-110 transition"></button>
                    <button type="button" onclick="setTool('pen', '#3b82f6', '{{ sub.id }}')" class="w-6 h-6 rounded-full bg-blue-500 border-2 border-white/20 hover:scale-110 transition"></button>
                    <button type="button" onclick="setTool('pen', '#10b981', '{{ sub.id }}')" class="w-6 h-6 rounded-full bg-emerald-500 border-2 border-white/20 hover:scale-110 transition"></button>
                    <button type="button" onclick="setTool('pen', '#eab308', '{{ sub.id }}')" class="w-6 h-6 rounded-full bg-yellow-500 border-2 border-white/20 hover:scale-110 transition"></button>
                    <button type="button" onclick="setTool('pen', '#ffffff', '{{ sub.id }}')" class="w-6 h-6 rounded-full bg-white border-2 border-white/20 hover:scale-110 transition"></button>
                </div>
                
                <div class="flex items-center space-x-2">
                    <span class="text-xs font-bold text-gray-400">Size:</span>
                    <button type="button" onclick="setSize(2, '{{ sub.id }}')" class="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded font-bold">Thin</button>
                    <button type="button" onclick="setSize(5, '{{ sub.id }}')" class="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded font-bold">Medium</button>
                    <button type="button" onclick="setSize(10, '{{ sub.id }}')" class="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded font-bold">Thick</button>
                </div>

                <div class="flex items-center space-x-2">
                    <button type="button" onclick="setTool('pen', null, '{{ sub.id }}')" class="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-bold">✏️ Pen</button>
                    <button type="button" onclick="setTool('eraser', null, '{{ sub.id }}')" class="px-3 py-1 text-xs bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-bold">🧹 Eraser</button>
                    <button type="button" onclick="clearCanvas('{{ sub.id }}')" class="px-3 py-1 text-xs bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold">🗑️ Clear</button>
                </div>
            </div>

            <div class="flex justify-center overflow-auto">
                <div class="canvas-container rounded-xl overflow-hidden shadow-2xl border border-slate-700">
                    <canvas id="bg_canvas_{{ sub.id }}" class="absolute top-0 left-0 z-0"></canvas>
                    <canvas id="draw_canvas_{{ sub.id }}" class="relative z-10 cursor-crosshair"></canvas>
                </div>
            </div>
            <img id="img_{{ sub.id }}" src="{{ sub.image_b64 }}" class="hidden">
        </div>

        <form method="POST" action="/teacher/evaluate" onsubmit="saveCanvas('{{ sub.id }}')">
            <input type="hidden" name="submission_id" value="{{ sub.id }}">
            <input type="hidden" name="annotated_image" id="annotated_{{ sub.id }}">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                    <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Score / Grade</label>
                    <input type="text" name="score" required placeholder="e.g. 95/100 or A+" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
                </div>
                <div>
                    <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Feedback Note</label>
                    <input type="text" name="note" required placeholder="Excellent work! Watch out for tense usage..." class="w-full px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
                </div>
            </div>
            <button type="submit" class="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition shadow-lg shadow-emerald-500/25">Submit Feedback & Mark Checked</button>
        </form>
    </div>
    {% else %}
    <div class="p-12 text-center bg-white dark:bg-darkcard rounded-2xl border border-gray-200 dark:border-darkborder text-gray-500">
        ✨ No pending homework to evaluate right now!
    </div>
    {% endfor %}
</div>

<script>
    const contexts = {};
    const isDrawing = {};
    const tools = {};
    const colors = {};
    const sizes = {};

    document.querySelectorAll('img[id^="img_"]').forEach(img => {
        const initCanvas = function() {
            const id = img.id.split('_')[1];
            const bgCanvas = document.getElementById('bg_canvas_' + id);
            const drawCanvas = document.getElementById('draw_canvas_' + id);
            
            if (!bgCanvas || !drawCanvas) return;
            
            const w = img.width || 600;
            const h = img.height || 400;
            
            bgCanvas.width = drawCanvas.width = w;
            bgCanvas.height = drawCanvas.height = h;

            const bgCtx = bgCanvas.getContext('2d');
            const drawCtx = drawCanvas.getContext('2d');
            
            bgCtx.drawImage(img, 0, 0, w, h);
            
            contexts[id] = drawCtx;
            isDrawing[id] = false;
            tools[id] = 'pen';
            colors[id] = '#ef4444';
            sizes[id] = 3;

            drawCanvas.onmousedown = e => startDraw(e, id);
            drawCanvas.onmousemove = e => draw(e, id);
            drawCanvas.onmouseup = () => stopDraw(id);
            drawCanvas.onmouseout = () => stopDraw(id);
        };

        if (img.complete) {
            initCanvas();
        } else {
            img.onload = initCanvas;
        }
    });

    function setTool(tool, color, id) {
        if(tool) tools[id] = tool;
        if(color) colors[id] = color;
    }

    function setSize(size, id) {
        sizes[id] = size;
    }

    function getPos(canvas, evt) {
        const rect = canvas.getBoundingClientRect();
        return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
    }

    function startDraw(e, id) {
        isDrawing[id] = true;
        const ctx = contexts[id];
        const pos = getPos(document.getElementById('draw_canvas_' + id), e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }

    function draw(e, id) {
        if (!isDrawing[id]) return;
        const ctx = contexts[id];
        const pos = getPos(document.getElementById('draw_canvas_' + id), e);
        
        ctx.lineWidth = sizes[id];
        ctx.lineCap = 'round';

        if (tools[id] === 'eraser') {
            ctx.globalCompositeOperation = 'destination-out';
        } else {
            ctx.globalCompositeOperation = 'source-over';
            ctx.strokeStyle = colors[id];
        }

        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
    }

    function stopDraw(id) {
        isDrawing[id] = false;
        if(contexts[id]) contexts[id].beginPath();
    }

    function clearCanvas(id) {
        const canvas = document.getElementById('draw_canvas_' + id);
        const ctx = contexts[id];
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    function saveCanvas(id) {
        const bgCanvas = document.getElementById('bg_canvas_' + id);
        const drawCanvas = document.getElementById('draw_canvas_' + id);
        
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = bgCanvas.width;
        tempCanvas.height = bgCanvas.height;
        const tempCtx = tempCanvas.getContext('2d');
        
        tempCtx.drawImage(bgCanvas, 0, 0);
        tempCtx.drawImage(drawCanvas, 0, 0);
        
        document.getElementById('annotated_' + id).value = tempCanvas.toDataURL('image/jpeg');
    }
</script>
"""

PAGE_MY_HOMEWORK = """
<h2 class="text-3xl font-extrabold mb-6">My Homework Assignments</h2>
<div class="space-y-6">
    {% for hw in my_assignments %}
    {% set status_info = statuses.get(hw.id, None) %}
    <div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder relative overflow-hidden">
        <div class="flex justify-between items-start mb-4">
            <div>
                <span class="text-xs font-bold text-gray-400 uppercase tracking-wider">Teacher: {{ hw.teacher }}</span>
                <span class="text-xs text-gray-500 ml-3">• Assigned: {{ hw.date }}</span>
            </div>
            
            {% if not status_info or status_info.status == 'not_started' %}
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-300">Not Started</span>
            {% elif status_info.status == 'in_progress' %}
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">In Progress ⏳</span>
            {% elif status_info.status == 'completed' %}
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Completed 🎉</span>
            {% endif %}
        </div>

        <p class="text-lg text-gray-200 mb-6 whitespace-pre-wrap leading-relaxed">{{ hw.text }}</p>

        <div class="pt-4 border-t border-gray-200 dark:border-darkborder flex flex-wrap items-center justify-between gap-4">
            {% if not status_info or status_info.status == 'not_started' %}
                <form method="POST" action="/student/start_hw" class="flex flex-wrap items-center gap-3">
                    <input type="hidden" name="hw_id" value="{{ hw.id }}">
                    <div class="flex items-center space-x-2">
                        <label class="text-xs text-gray-400 font-bold">Est. Delivery (Max 5 days):</label>
                        <input type="date" name="est_date" min="{{ min_date }}" max="{{ max_date }}" required class="px-3 py-1.5 rounded-lg bg-slate-800 border border-darkborder text-xs font-bold text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <button type="submit" class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-sm transition shadow-lg shadow-blue-500/20">🚀 Start HW</button>
                </form>
            {% elif status_info.status == 'in_progress' %}
                <div class="text-xs text-amber-400 font-medium">
                    Target Date: <b>{{ status_info.est_date }}</b> ({{ status_info.days_str }})
                </div>
                <form method="POST" action="/student/finish_hw">
                    <input type="hidden" name="hw_id" value="{{ hw.id }}">
                    <button type="submit" class="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-sm transition shadow-lg shadow-emerald-500/20">✅ Complete HW</button>
                </form>
            {% else %}
                <span class="text-xs text-emerald-400 font-bold">Finished! Don't forget to submit photo evidence in the "Submit HW" tab.</span>
            {% endif %}
        </div>
    </div>
    {% else %}
    <div class="p-12 text-center bg-white dark:bg-darkcard rounded-2xl border border-gray-200 dark:border-darkborder text-gray-500">
        No homework assigned to you yet!
    </div>
    {% endfor %}
</div>
"""

PAGE_SUBMIT = """
<h2 class="text-3xl font-extrabold mb-6">Submit Finished Homework</h2>
<div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder max-w-xl">
    <form method="POST" action="/student/submit" enctype="multipart/form-data" class="space-y-6">
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Select Assignment</label>
            <select name="assignment_id" required class="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-darkborder focus:ring-2 focus:ring-blue-500 outline-none">
                <option value="" disabled selected>-- Choose assignment to upload for --</option>
                {% for hw in my_assignments %}
                    <option value="{{ hw.id }}">ID: {{ hw.id }} - {{ hw.text[:35] }}...</option>
                {% endfor %}
            </select>
        </div>
        
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">Upload Solution Image / Photo</label>
            <div class="border-2 border-dashed border-gray-300 dark:border-darkborder rounded-2xl p-8 text-center hover:bg-slate-800/50 transition cursor-pointer">
                <input type="file" name="hw_image" accept="image/*" required class="w-full text-sm text-gray-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-blue-600 file:text-white hover:file:bg-blue-700">
            </div>
        </div>
        
        <button type="submit" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition shadow-lg shadow-blue-500/25">Send Solution to Teacher</button>
    </form>
</div>
"""

PAGE_EVALUATIONS = """
<h2 class="text-3xl font-extrabold mb-6">Teacher Feedback & Grades</h2>
<div class="space-y-6">
    {% for ev in my_evaluations %}
    <div class="bg-white dark:bg-darkcard p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-darkborder">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div>
                <span class="text-xs font-bold text-emerald-400 uppercase tracking-widest">Evaluated Submission</span>
                <div class="mt-4 space-y-3">
                    <div>
                        <span class="text-xs text-gray-400 font-bold block">Grade / Score:</span>
                        <span class="text-2xl font-black text-emerald-400">{{ ev.score }}</span>
                    </div>
                    <div>
                        <span class="text-xs text-gray-400 font-bold block">Teacher's Note:</span>
                        <p class="text-gray-200 italic mt-1 bg-slate-800 p-3 rounded-xl border border-darkborder">"{{ ev.note }}"</p>
                    </div>
                </div>
            </div>
            <div class="text-center">
                <span class="text-xs text-gray-400 font-bold block mb-2">Annotated Correction Sheet:</span>
                <img src="{{ ev.annotated_image }}" class="max-w-full h-auto rounded-xl border border-darkborder shadow-lg mx-auto" style="max-height: 280px;">
            </div>
        </div>
    </div>
    {% else %}
    <div class="p-12 text-center bg-white dark:bg-darkcard rounded-2xl border border-gray-200 dark:border-darkborder text-gray-500">
        No checked evaluations yet.
    </div>
    {% endfor %}
</div>
"""

# --- HELPER FUNCTIONS ---

def render_page(template_string, active_page, **kwargs):
    rendered_content = render_template_string(template_string, **kwargs)
    return render_template_string(BASE_HTML, content=rendered_content, active_page=active_page)

# --- ROUTE LOGIC ---

@app.route("/")
def index():
    if "user" in session: return redirect(url_for("home"))
    return render_template_string(BASE_HTML)

@app.route("/auth", methods=["POST"])
def auth():
    action = request.form.get("action")
    role = request.form.get("role")
    name = request.form.get("name_surname")
    password = request.form.get("password")
    
    if action == "signup":
        existing_user = User.query.filter_by(name=name).first()
        if existing_user:
            flash("User already exists!")
            return redirect(url_for("index"))
            
        students_str = request.form.get("students", "") if role == 'teacher' else ""
        new_user = User(name=name, password=password, role=role, students=students_str)
        db.session.add(new_user)
        db.session.commit()
        
        session["user"] = session["user_name"] = name
        session["role"] = role
        return redirect(url_for("home"))
        
    elif action == "login":
        user = User.query.filter_by(name=name, password=password, role=role).first()
        if user:
            session["user"] = session["user_name"] = user.name
            session["role"] = user.role
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials or role mismatch!")
            return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/home")
def home():
    if "user" not in session: return redirect(url_for("index"))
    
    t_notifs = []
    if session.get('role') == 'teacher':
        t_notifs = Notification.query.filter_by(teacher=session['user']).order_by(Notification.id.desc()).all()
        
    return render_page(PAGE_HOME, "home", teacher_notifications=t_notifs)

@app.route("/lessons")
def lessons():
    if "user" not in session: return redirect(url_for("index"))
    return render_page(PAGE_LESSONS, "lessons")

@app.route("/settings")
def settings():
    if "user" not in session: return redirect(url_for("index"))
    return render_page(PAGE_SETTINGS, "settings")

@app.route("/update_account", methods=["POST"])
def update_account():
    if "user" not in session: return redirect(url_for("index"))
    
    user = User.query.filter_by(name=session["user"]).first()
    if not user:
        session.clear()
        return redirect(url_for("index"))
        
    new_name = request.form.get("new_name")
    new_password = request.form.get("new_password")
    
    user.name = new_name
    if new_password:
        user.password = new_password
        
    db.session.commit()
    session["user"] = session["user_name"] = new_name
    return redirect(url_for("settings"))

# --- TEACHER ROUTES ---

@app.route("/teacher/assign", methods=["GET", "POST"])
def assign():
    if session.get("role") != "teacher": return redirect(url_for("home"))
    
    if request.method == "POST":
        new_assign = Assignment(
            id=str(uuid.uuid4())[:8],
            teacher=session["user"],
            student=request.form.get("student_id"),
            text=request.form.get("text"),
            date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        db.session.add(new_assign)
        db.session.commit()
        return redirect(url_for("assign"))
        
    user = User.query.filter_by(name=session["user"]).first()
    my_students = [s.strip() for s in user.students.split(",") if s.strip()] if user and user.students else []
    return render_page(PAGE_ASSIGN, "assign", students=my_students)

@app.route("/teacher/check")
def check_hw():
    if session.get("role") != "teacher": return redirect(url_for("home"))
    pending = Submission.query.filter_by(teacher=session["user"], status="pending").all()
    return render_page(PAGE_CHECK, "check", pending_submissions=pending)

@app.route("/teacher/evaluate", methods=["POST"])
def evaluate():
    if session.get("role") != "teacher": return redirect(url_for("home"))
    
    sub_id = request.form.get("submission_id")
    sub = Submission.query.filter_by(id=sub_id).first()
    
    if sub:
        sub.status = "checked"
        new_eval = Evaluation(
            submission_id=sub_id,
            student=sub.student,
            teacher=session["user"],
            annotated_image=request.form.get("annotated_image"),
            score=request.form.get("score"),
            note=request.form.get("note")
        )
        db.session.add(new_eval)
        db.session.commit()
            
    return redirect(url_for("check_hw"))

# --- STUDENT ROUTES ---

@app.route("/student/homework")
def student_hw():
    if session.get("role") != "student": return redirect(url_for("home"))
    
    my_hw = Assignment.query.filter_by(student=session["user"]).all()
    statuses_query = HwStatus.query.filter_by(student=session["user"]).all()
    statuses = {s.assignment_id: s for s in statuses_query}
    
    min_d = datetime.now().strftime("%Y-%m-%d")
    max_d = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    
    return render_page(PAGE_MY_HOMEWORK, "homework", my_assignments=my_hw, statuses=statuses, min_date=min_d, max_date=max_d)

@app.route("/student/start_hw", methods=["POST"])
def start_hw():
    if session.get("role") != "student": return redirect(url_for("home"))
    
    hw_id = request.form.get("hw_id")
    est_date = request.form.get("est_date")
    student = session["user"]
    
    hw = Assignment.query.filter_by(id=hw_id).first()
    if hw:
        today = datetime.now().date()
        try:
            target_date = datetime.strptime(str(est_date), "%Y-%m-%d").date()
            days_diff = (target_date - today).days
        except (ValueError, TypeError):
            days_diff = 1

        if days_diff <= 0:
            time_str = "today"
        elif days_diff == 1:
            time_str = "within 1 day"
        else:
            time_str = f"within {days_diff} days"

        status_obj = HwStatus.query.filter_by(student=student, assignment_id=hw_id).first()
        if not status_obj:
            status_obj = HwStatus(student=student, assignment_id=hw_id)
            db.session.add(status_obj)
            
        status_obj.status = 'in_progress'
        status_obj.est_date = str(est_date)
        status_obj.days_str = time_str
        
        new_notif = Notification(
            teacher=hw.teacher,
            text=f"Your student {student} started the assignment assigned on {hw.date}. Estimated delivery: {time_str}.",
            date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        db.session.add(new_notif)
        db.session.commit()
        
    return redirect(url_for("student_hw"))

@app.route("/student/finish_hw", methods=["POST"])
def finish_hw():
    if session.get("role") != "student": return redirect(url_for("home"))
    
    hw_id = request.form.get("hw_id")
    student = session["user"]
    
    hw = Assignment.query.filter_by(id=hw_id).first()
    if hw:
        status_obj = HwStatus.query.filter_by(student=student, assignment_id=hw_id).first()
        if status_obj:
            status_obj.status = 'completed'
            
        new_notif = Notification(
            teacher=hw.teacher,
            text=f"Your student {student} completed the assignment assigned on {hw.date}.",
            date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        db.session.add(new_notif)
        db.session.commit()
        
    return redirect(url_for("student_hw"))

@app.route("/student/submit", methods=["GET", "POST"])
def submit_hw():
    if session.get("role") != "student": return redirect(url_for("home"))
    
    if request.method == "POST":
        file = request.files.get("hw_image")
        assign_id = request.form.get("assignment_id")
        
        if file and assign_id:
            image_b64 = "data:image/jpeg;base64," + base64.b64encode(file.read()).decode('utf-8')
            hw = Assignment.query.filter_by(id=assign_id).first()
            teacher_name = hw.teacher if hw else ""
            
            new_sub = Submission(
                id=str(uuid.uuid4())[:8],
                assignment_id=assign_id,
                student=session["user"],
                teacher=teacher_name,
                image_b64=image_b64,
                status="pending"
            )
            db.session.add(new_sub)
            db.session.commit()
            return redirect(url_for("submit_hw"))

    my_hw = Assignment.query.filter_by(student=session["user"]).all()
    return render_page(PAGE_SUBMIT, "submit", my_assignments=my_hw)

@app.route("/student/evaluations")
def student_evaluations():
    if session.get("role") != "student": return redirect(url_for("home"))
    my_evals = Evaluation.query.filter_by(student=session["user"]).all()
    return render_page(PAGE_EVALUATIONS, "evaluations", my_evaluations=my_evals)

if __name__ == "__main__":
    app.run(debug=True)
