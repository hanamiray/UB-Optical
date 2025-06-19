from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
import os
from flask_mysqldb import MySQL
import bcrypt
from functools import wraps
from flask import make_response
from flask import session
from flask_login import login_required, logout_user, current_user
from flask_login import LoginManager
from flask_login import UserMixin
from datetime import timedelta



app = Flask(__name__)





# Add this at the TOP of app.py (right after imports)
app.secret_key = 'your-super-secret-key-1234567890'  # Replace with random string
app.config['SESSION_COOKIE_NAME'] = 'ub_optical_session'  # Unique name
app.config['SESSION_REFRESH_EACH_REQUEST'] = False




# Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Change to your MySQL username
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD')  # Mas secure
app.config['MYSQL_DB'] = 'ub_optical'





app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Specify your login route



mysql = MySQL(app)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/index')
@app.route('/')
def index():
    # Kung may separate homepage para sa visitors
    return render_template('index.html')  # Dapat may index.html sa templates folder




class User(UserMixin):
    def __init__(self, id):
        self.id = id

# This callback is needed for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)



# Change these routes:
@app.route('/images/<filename>')
def images(filename):
    return send_from_directory(os.path.join(app.root_path, 'images'), filename)

@app.route('/brand_images/<filename>')
def brand_images(filename):
    return send_from_directory(os.path.join(app.root_path, 'images', 'brands'), filename)






@app.context_processor
def inject_static_path():
    return {'static': lambda filename: url_for('static', filename=filename)}





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password', '').encode('utf-8')
        
        print(f"🔑 Login attempt: {email}")  # DEBUG
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id, password FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            print(f"📦 Database returned: {user}")  # DEBUG
            
            if user:
                print(f"🔐 Stored hash: {user[1]}")  # DEBUG
                if bcrypt.checkpw(password, user[1].encode('utf-8')):
                    session['logged_in'] = True
                    session['user_id'] = user[0]
                    print("🎉 LOGIN SUCCESS! Session:", session)  # DEBUG
                    return redirect(url_for('home_records'))
                else:
                    print("❌ WRONG PASSWORD")  # DEBUG
            else:
                print("🚫 USER NOT FOUND")  # DEBUG
                
            flash('Invalid credentials', 'error')
            
        except Exception as e:
            print(f"💥 DATABASE ERROR: {str(e)}")  # DEBUG
            flash('System error', 'error')
    
    # KAPAG GET REQUEST (BACK BUTTON/REFRESH)
    response = make_response(render_template('login.html'))
    
    # FORCE NO CACHE PARA SA LOGIN PAGE
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    
    return response


@app.after_request
def add_no_cache(response):
    if 'logged_in' not in session:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response



@app.route('/login', methods=['GET'])
def login_page():
    response = make_response(render_template('login.html'))
    # Force no caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response



@app.route('/test-image')
def test_image():
    return f"""
    <h1>Image Test</h1>
    <p>Logo: <img src="{url_for('static', filename='images/logo2.png')}" width="100"></p>
    <p>Default: <img src="{url_for('static', filename='images/default.png')}" width="100"></p>
    <p>Brand (HM): <img src="{url_for('static', filename='images/brands/hm.png')}" width="100"></p>
    """

@app.route('/about')
def about():
    return render_template('about.html') 

@app.route('/optometrist')
def optometrist():
    return render_template('optometrist.html') 

@app.route('/consultation')
def consultation():
    return render_template('consultation.html') 

@app.route('/location')
def location():
    return render_template('location.html') 

@app.route('/schedule')
def schedule():
    return render_template('schedule.html') 

@app.route('/services')
def services():
    return render_template('services.html') 

@app.route('/list')
def list():
    return render_template('list.html') 





@app.route('/logout')
@login_required
def logout():
    # Clear session at cookies
    session.clear()
    logout_user()
    
    # Create response na magre-redirect sa login
    resp = make_response(redirect(url_for('login')))
    
    # DELETE LAHAT NG COOKIES AT CACHE
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '-1'
    
    # Patayin ang session cookie
    resp.set_cookie('ub_optical_session', '', expires=0)
    resp.set_cookie('session', '', expires=0)  # Para siguradong walang matira
    
    return resp






@app.route('/home_records')
@login_required
def home_records():
    # Get total patients count
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]
    
    # Get recent visits (last 7 days)
    cur.execute("""
        SELECT COUNT(*) FROM patients 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    recent_visits = cur.fetchone()[0]
    
    # Get all patients for the table
    cur.execute("""
        SELECT id, CONCAT(last_name, ', ', first_name, ' ', IFNULL(middle_initial, '')) as name, 
               age, phone, DATE_FORMAT(created_at, '%Y-%m-%d') as last_visit
        FROM patients
        ORDER BY created_at DESC
        LIMIT 10
    """)
    patients = cur.fetchall()
    cur.close()
    
    # Create response with cache control headers
    response = make_response(render_template(
        'home_records.html',
        total_patients=total_patients,
        recent_visits=recent_visits,
        patients=patients
    ))
    
    # Prevent caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response



@app.after_request
def add_header(response):
    if 'logged_in' in session:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response





@app.route('/patient_records')
@login_required
def patient_records():
    # Similar to home_records but might show more detailed patient list
    return render_template('patient_records.html')

@app.route('/history_records')
@login_required
def history_records():
    # Placeholder for history records
    return render_template('history_records.html')

@app.route('/add_patient', methods=['POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        middle_initial = request.form.get('middle_initial', '')
        age = request.form['age']
        phone = request.form['phone']
        medical_history = request.form.get('medical_history', '')
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO patients (first_name, last_name, middle_initial, age, phone, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, middle_initial, age, phone, medical_history))
        mysql.connection.commit()
        cur.close()
        
        flash('Patient added successfully!', 'success')
        return redirect(url_for('home_records'))

if __name__ == '__main__':
    app.run(debug=True)