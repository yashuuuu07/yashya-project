import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase_client import get_supabase
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")
supabase = get_supabase()

# --- Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Unauthorized access.", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        try:
            # Sign up with Supabase
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if auth_response.user:
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            else:
                flash("Registration failed.", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                # Fetch role from 'users' table - remove .single() to avoid crash if not found
                # Also pass the token to ensure we can read the table if RLS is on
                try:
                    user_query = supabase.table("users", token=auth_response.access_token).select("role").eq("id", auth_response.user.id).execute()
                    user_data_list = user_query.data if isinstance(user_query.data, list) else []
                    
                    # Fallback: If user not in 'users' table, create them now
                    if not user_data_list:
                        print(f"User {auth_response.user.id} not found in public.users, creating...")
                        supabase.table("users", token=auth_response.access_token).insert({
                            "id": auth_response.user.id,
                            "email": auth_response.user.email,
                            "role": "user"
                        }).execute()
                        role = "user"
                    else:
                        role = user_data_list[0].get('role', 'user')
                except Exception as e:
                    print(f"User check/init failed: {e}")
                    role = "user" # Default to user if DB fails but login succeeded
                
                session['user'] = {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "access_token": auth_response.access_token # Store token
                }
                session['role'] = role
                
                flash(f"Welcome back, {email}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid credentials.", "error")
        except Exception as e:
            error_str = str(e)
            if "Email not confirmed" in error_str:
                flash("Login failed: Please confirm your email address or disable 'Confirm Email' in Supabase Auth settings.", "error")
            else:
                flash(f"Login failed: {error_str}", "error")
            print(f"Login Error: {error_str}")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    token = session['user'].get('access_token')
    # Fetch courses for the user
    courses_query = supabase.table("courses", token=token).select("*").execute()
    courses = courses_query.data or []
    return render_template('dashboard.html', courses=courses)

@app.route('/admin')
@login_required
@admin_required
def admin():
    token = session['user'].get('access_token')
    courses_query = supabase.table("courses", token=token).select("*").execute()
    courses = courses_query.data or []
    return render_template('admin.html', courses=courses)

@app.route('/admin/course/create', methods=['POST'])
@login_required
@admin_required
def create_course():
    title = request.form.get('title')
    description = request.form.get('description')
    youtube_url = request.form.get('youtube_url')
    
    # Simple YouTube ID extraction
    import re
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    video_id = video_id_match.group(1) if video_id_match else None
    
    if not video_id:
        flash("Invalid YouTube URL.", "error")
        return redirect(url_for('admin'))

    token = session['user'].get('access_token')
    try:
        supabase.table("courses", token=token).insert({
            "title": title,
            "description": description,
            "created_by": session['user']['id']
        }).execute()
        
        # In a real app, you'd link this to the course_id. 
        # For simplicity in this demo, we store video data in the course or a related table.
        # Let's fetch the last inserted course_id or just use title if needed.
        # Optimization: Add course_videos row here.
        new_course = supabase.table("courses", token=token).select("id").eq("title", title).order("created_at", desc=True).limit(1).execute()
        if new_course.data:
            supabase.table("course_videos", token=token).insert({
                "course_id": new_course.data[0]['id'],
                "youtube_url": youtube_url,
                "youtube_video_id": video_id
            }).execute()

        flash("Course created successfully!", "success")
    except Exception as e:
        flash(f"Error creating course: {str(e)}", "error")
        
    return redirect(url_for('admin'))

@app.route('/admin/course/delete/<course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    token = session['user'].get('access_token')
    try:
        supabase.table("courses", token=token).delete().eq("id", course_id).execute()
        flash("Course deleted.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for('admin'))

@app.route('/course/<course_id>')
@login_required
def view_course(course_id):
    token = session['user'].get('access_token')
    course_query = supabase.table("courses", token=token).select("*").eq("id", course_id).single().execute()
    video_query = supabase.table("course_videos", token=token).select("*").eq("course_id", course_id).single().execute()
    
    if not course_query.data:
        flash("Course not found.", "error")
        return redirect(url_for('dashboard'))
    
    video_id = video_query.data['youtube_video_id'] if video_query.data else ""
    return render_template('course.html', course=course_query.data, video_id=video_id)

@app.route('/api/log_emotion', methods=['POST'])
@login_required
def log_emotion():
    data = request.json
    token = session['user'].get('access_token')
    try:
        supabase.table("emotion_logs", token=token).insert({
            "user_id": session['user']['id'],
            "course_id": data.get('course_id'),
            "emotion": data.get('emotion'),
            "confidence_score": data.get('score'),
            "video_timestamp": data.get('timestamp')
        }).execute()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
