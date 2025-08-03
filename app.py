from flask import Flask, render_template, request, redirect, url_for, session,flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId  # Import ObjectId for MongoDB document identification
from datetime import date
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Define the upload folder path
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploaded_cvs')  # This will create the folder in your current working directory
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Initialize MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client['job_board']
contacts_collection = db['contacts']
user_collection = db['users']
job_collection = db["jobs"]
applications_collection = db['applications']


@app.route('/')
def home():
    return render_template('home.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        pwd = request.form['pwd']
        
        # Look for user by name
        user = user_collection.find_one({'name': name})
        
        # Check if user exists and password is correct
        if user and check_password_hash(user['pwd'], pwd):
            session['user'] = name
            session['user_email'] = user['email']  # Store email in session
            session['role'] = user['role']
            
            # Redirect based on the user role
            if user['role'] == 'admin':
                return redirect(url_for('admin_home'))
            else:
                return redirect(url_for('user_home'))
        else:
            return "Invalid login!"
    return render_template('login.html')


@app.route('/admin_home')
def admin_home():
    if 'user' in session and session['role'] == 'admin':
        return render_template('admin/admin_home.html')
    return redirect(url_for('login'))

@app.route('/user_home')
def user_home():
    if 'user' in session and session['role'] == 'user':
        return render_template('user/user_home.html')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print(request.form)
        name = request.form.get('name')
        pwd = generate_password_hash(request.form.get('pwd'))
        phno = request.form.get('phno')
        email = request.form.get('email')
        role = request.form.get('role')  # This can be 'admin' or 'user'
        
        user_collection.insert_one({'name': name, 'pwd': pwd, 'role': role, 'phno':phno,'email':email})
        return redirect(url_for('login'))
    return render_template('register.html')



# Admin: Add job
@app.route('/admin/add_jobs', methods=['GET', 'POST'])
def add_jobs():
    if request.method == 'POST':
        job_data = {
            "position": request.form.get('position'),
            "company": request.form.get('company'),
            "job_type": request.form.get('job-type'),
            "salary": request.form.get('salary'),
            "job_deadline": request.form.get('job-deadline'),
            "location": request.form.get('location'),
            "vacancy": request.form.get('vacancy'),
            "skills": request.form.getlist('skills'),
            "contact_mail": request.form.get('contact-mail'),
            "job_description": request.form.get('job-description')
        }
        job_collection.insert_one(job_data)
        return redirect(url_for('manage_jobs'))
    return render_template('admin/add_jobs.html')

# Admin: Manage jobs (with Edit/Delete)
@app.route('/admin/manage_jobs')
def manage_jobs():
    jobs = job_collection.find()
    return render_template('admin/manage_jobs.html', jobs=jobs)

@app.route('/admin/edit_job/<job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    job = job_collection.find_one({"_id": ObjectId(job_id)})
    if request.method == 'POST':
        updated_data = {
            "position": request.form.get('position'),
            "company": request.form.get('company'),
            "job_type": request.form.get('job-type'),
            "salary": request.form.get('salary'),
            "job_deadline": request.form.get('job-deadline'),
            "location": request.form.get('location'),
            "vacancy": request.form.get('vacancy'),
            "skills": request.form.getlist('skills'),
            "contact_mail": request.form.get('contact-mail'),
            "job_description": request.form.get('job-description')
        }
        job_collection.update_one({"_id": ObjectId(job_id)}, {"$set": updated_data})
        return redirect(url_for('manage_jobs'))
    return render_template('admin/edit_jobs.html', job=job)

@app.route('/admin/delete_job/<job_id>', methods=['POST'])
def delete_job(job_id):
    job_collection.delete_one({"_id": ObjectId(job_id)})
    return redirect(url_for('manage_jobs'))

# User: View jobs
@app.route('/jobs')
def jobs():
    jobs = job_collection.find()
    return render_template('user/jobs.html', jobs=jobs)


@app.route('/apply/<job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Fetch the job details
        job = job_collection.find_one({'_id': ObjectId(job_id)})
        
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('jobs'))

        # Capture the form data
        cv_file = request.files['cv']
        if cv_file:
            cv_filename = os.path.join(app.config['UPLOAD_FOLDER'], cv_file.filename)
            cv_file.save(cv_filename)  # Save the CV file

        application_data = {
            'user_email': session['user_email'],
            'job_id': job_id,
            'position': job['position'],
            'company': job['company'],
            'status': 'Applied',
            'firstname': request.form.get('first-name'),
            'lastname': request.form.get('last-name'),
            'email': request.form.get('email'),
            'job_role': request.form.get('job-role'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'pincode': request.form.get('pincode'),
            'phonenumber': request.form.get('phonenumber'),
            'apply_date': request.form.get('date'),
            'cv': cv_filename  # Store the file path in the database
        }

        # Insert the application into the database
        applications_collection.insert_one(application_data)

        flash('Application submitted successfully!', 'success')
        return redirect(url_for('applications'))

    return render_template('user/apply.html', job_id=job_id)


@app.route('/applications')
def applications():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    # Fetch all applications for the logged-in user
    user_email = session['user_email']
    user_applications = list(applications_collection.find({'user_email': user_email}))

    return render_template('user/applications.html', applications=user_applications)








if __name__ == '__main__':
    app.run(debug=True)