from flask import current_app as app
from flask import flash, render_template, request, redirect, url_for
from .ai_utils import generate_content
import requests
import os

from . import db
from .models import Enrollment

# --- CONFIGURATION (loaded from environment) ---
GOPHISH_API_KEY = os.getenv("GOPHISH_API_KEY")
GOPHISH_URL = os.getenv("GOPHISH_URL")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN")
MOODLE_URL = os.getenv("MOODLE_URL")

# --- HELPER FUNCTIONS ---

def moodle_api_call(function_name, params={}):
    """A helper function to make calls to the Moodle API."""
    base_url = f"{MOODLE_URL}/webservice/rest/server.php"
    call_params = params.copy()
    call_params.update({
        'wstoken': MOODLE_TOKEN,
        'wsfunction': function_name,
        'moodlewsrestformat': 'json',
    })
    try:
        response = requests.post(base_url, data=call_params, timeout=30)
        response.raise_for_status()
        # Handle empty responses which indicate success for some functions
        if response.text:
            return response.json()
        return {"status": "ok"} # Return a success indicator for empty responses
    except requests.exceptions.RequestException as e:
        print(f"Error calling Moodle API: {e}")
        return {'exception': str(e)}

def get_moodle_user_by_email(email):
    """
    Finds a Moodle user's full details from their email address.
    This is the final, corrected version based on direct API response analysis.
    """
    function = "core_user_get_users_by_field"
    # This parameter format is correct.
    params = {'field': 'email', 'values[0]': email}
    response = moodle_api_call(function, params)

    # The Moodle API for this function returns a LIST of users directly.
    # We must check if the response is a list and if it is not empty.
    if isinstance(response, list) and len(response) > 0:
        # If the list is not empty, it means we found at least one user.
        # We return the first user object from the list.
        return response[0]
    
    # If the response is not a list, is an empty list, or was an error, we return None.
    return None

# --- FLASK ROUTES ---

@app.route('/')
def home_page():
    """Renders the main welcome/landing page."""
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    headers = {'Authorization': f'Bearer {GOPHISH_API_KEY}'}
    campaigns = []
    try:
        response = requests.get(f"{GOPHISH_URL}/api/campaigns/", headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        campaigns = response.json()
        for c in campaigns:
            stats = c.get('stats', {}); total = stats.get('total', 0)
            failed = stats.get('submitted_data', 0) + stats.get('clicked_link', 0)
            c['fail_rate'] = f"{(failed / total) * 100:.2f}%" if total > 0 else "N/A"
    except requests.exceptions.RequestException as e:
        flash(f"Could not fetch campaigns from GoPhish: {e}", "error")
    return render_template('dashboard.html', campaigns=campaigns)

@app.route('/campaign/<int:campaign_id>')
def campaign_details(campaign_id):
    headers = {'Authorization': f'Bearer {GOPHISH_API_KEY}'}
    campaign, failed_users, moodle_courses = {}, [], []
    try:
        response = requests.get(f"{GOPHISH_URL}/api/campaigns/{campaign_id}", headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        campaign = response.json()
        failed_users = [r for r in campaign.get('results', []) if r['status'] in ["Clicked Link", "Submitted Data", "Email Opened"]]
        moodle_courses = moodle_api_call('core_course_get_courses') or []
    except requests.exceptions.RequestException as e:
        flash(f"Could not fetch campaign details: {e}", "error")
    return render_template('campaign.html', campaign=campaign, failed_users=failed_users, moodle_courses=moodle_courses)

@app.route('/enroll', methods=['POST'])
def enroll_users():
    course_ids = request.form.getlist('course_ids')
    user_emails = request.form.getlist('user_emails') 
    campaign_id = request.form.get('campaign_id', type=int)
    
    print("\n--- INITIATING ENROLLMENT PROCESS ---")

    if not course_ids or not user_emails:
        flash("Error: You must select at least one course and one user.", "error")
        return redirect(url_for('campaign_details', campaign_id=campaign_id))

    successful_enrollments = 0
    failed_enrollments = []
    
    for email in user_emails:
        print(f"\nProcessing user: {email}")
        user_object = get_moodle_user_by_email(email)
        
        if user_object:
            user_id = user_object['id']
            print(f"  -> Found Moodle User ID: {user_id}")
            for course_id in course_ids:
                print(f"  --> Attempting to enroll in Course ID: {course_id}")
                function = 'enrol_manual_enrol_users'
                params = {'enrolments[0][roleid]': 5, 'enrolments[0][userid]': user_id, 'enrolments[0][courseid]': course_id}
                
                result = moodle_api_call(function, params)
                
                print(f"  --> RAW MOODLE API RESPONSE: {result}")

                # --- START OF NEW, SMARTER LOGIC ---
                is_successful = False
                # First, check if there was an error at all
                if result and isinstance(result, dict) and 'exception' in result:
                    # An error occurred. Check if it's the specific email error we can ignore.
                    if result.get('errorcode') == 'Message was not sent.':
                        print("  --> LOGIC: 'Message was not sent' error detected. Treating as SUCCESS.")
                        is_successful = True
                    else:
                        # It was a different, real error.
                        print("  --> LOGIC: A critical Moodle error was detected.")
                        is_successful = False
                else:
                    # There was no exception, so it's a clean success.
                    print("  --> LOGIC: No exception found. Treating as SUCCESS.")
                    is_successful = True

                if is_successful:
                    successful_enrollments += 1
                    new_enrollment = Enrollment(
                        gophish_campaign_id=campaign_id, 
                        user_email=email, 
                        moodle_user_id=user_id, 
                        moodle_course_id=course_id
                    )
                    db.session.add(new_enrollment)
                else:
                    failed_enrollments.append(f"{email} -> CourseID {course_id}")
                # --- END OF NEW LOGIC ---

        else:
            print("  -> LOGIC: Moodle user not found.")
            failed_enrollments.append(f"{email} (User not found)")

    # (The database commit and flash message logic remains the same)
    if successful_enrollments > 0:
        try:
            print(f"\nAttempting to commit {successful_enrollments} records to database...")
            db.session.commit()
            print("  -> Database commit SUCCEEDED.")
            flash(f"Successfully created {successful_enrollments} new enrollments.", "success")
        except Exception as e:
            db.session.rollback()
            print(f"  -> DATABASE COMMIT FAILED: {e}")
            flash(f"Database error: {e}", "error")
    else:
        print("\nNo successful enrollments to commit.")
    
    if failed_enrollments:
        flash(f"Failed to create some enrollments: {', '.join(failed_enrollments)}", "error")

    print("--- ENROLLMENT PROCESS COMPLETE ---")
    return redirect(url_for('campaign_details', campaign_id=campaign_id))


@app.route('/manual_enroll', methods=['GET', 'POST'])
def manual_enroll():
    if request.method == 'POST':
        course_ids = request.form.getlist('course_ids')
        emails_string = request.form.get('user_emails_text', '')
        user_emails = [e.strip() for e in emails_string.splitlines() if e.strip()]

        if not course_ids or not user_emails:
            flash("Error: You must provide at least one email and select one course.", "error")
            return redirect(url_for('manual_enroll'))

        successful_enrollments = 0
        failed_enrollments = []
        
        for email in user_emails:
            user_object = get_moodle_user_by_email(email)
            if user_object:
                user_id = user_object['id']
                for course_id in course_ids:
                    function = 'enrol_manual_enrol_users'
                    params = {'enrolments[0][roleid]': 5, 'enrolments[0][userid]': user_id, 'enrolments[0][courseid]': course_id}
                    result = moodle_api_call(function, params)
                    
                    is_successful = False
                    if result and isinstance(result, dict) and 'exception' in result:
                        if result.get('errorcode') == 'Message was not sent.':
                            is_successful = True
                    else:
                        is_successful = True

                    if is_successful:
                        successful_enrollments += 1
                        new_enrollment = Enrollment(gophish_campaign_id=0, user_email=email, moodle_user_id=user_id, moodle_course_id=course_id)
                        db.session.add(new_enrollment)
                    else:
                        failed_enrollments.append(f"{email} in CourseID {course_id}")
            else:
                failed_enrollments.append(f"{email} (User not found)")
        
        if successful_enrollments > 0:
            try:
                db.session.commit()
                flash(f"Process complete. Created {successful_enrollments} new course enrollments.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Database error: {e}", "error")
        
        if failed_enrollments:
            flash(f"Failed to create some enrollments: {', '.join(failed_enrollments)}", "error")
            
        return redirect(url_for('manual_enroll'))

    moodle_courses = moodle_api_call('core_course_get_courses') or []
    return render_template('manual_enroll.html', moodle_courses=moodle_courses)
    if request.method == 'POST':
        course_ids = request.form.getlist('course_ids')
        emails_string = request.form.get('user_emails_text', '')
        user_emails = [e.strip() for e in emails_string.splitlines() if e.strip()]

        if not course_ids or not user_emails:
            flash("Error: You must provide at least one email and select one course.", "error")
            return redirect(url_for('manual_enroll'))

        successful_enrollments, failed_emails = 0, []
        for email in user_emails:
            user_object = get_moodle_user_by_email(email)
            if user_object:
                user_id = user_object['id']
                for course_id in course_ids:
                    function = 'enrol_manual_enrol_users'
                    params = {'enrolments[0][roleid]': 5, 'enrolments[0][userid]': user_id, 'enrolments[0][courseid]': course_id}
                    result = moodle_api_call(function, params)
                    if not (isinstance(result, dict) and 'exception' in result):
                        successful_enrollments += 1
                        new_enrollment = Enrollment(gophish_campaign_id=0, user_email=email, moodle_user_id=user_id, moodle_course_id=course_id)
                        db.session.add(new_enrollment)
            else:
                failed_emails.append(email)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Database error: {e}", "error")
            return redirect(url_for('manual_enroll'))
        
        if successful_enrollments > 0:
            flash(f"Process complete. Created {successful_enrollments} new course enrollments.", "success")
        if failed_emails:
            flash(f"Could not find Moodle users for: {', '.join(failed_emails)}", "error")
        return redirect(url_for('manual_enroll'))

    moodle_courses = moodle_api_call('core_course_get_courses') or []
    return render_template('manual_enroll.html', moodle_courses=moodle_courses)


@app.route('/training_status')
def training_status():
    print("--- Loading Training Status Page ---")
    
    # 1. Fetch records from our local database
    enrollments = Enrollment.query.order_by(Enrollment.enrollment_timestamp.desc()).all()
    print(f"Found {len(enrollments)} enrollment records in the database.")
    
    if not enrollments:
        print("No enrollments found. Rendering empty page.")
        return render_template('training_status.html', enrollments=[])

    # 2. Get all course names in a single API call for efficiency
    moodle_courses_raw = moodle_api_call('core_course_get_courses') or []
    course_names = {}
    if moodle_courses_raw and 'exception' not in moodle_courses_raw:
        course_names = {c['id']: c['fullname'] for c in moodle_courses_raw}
    print(f"Successfully fetched {len(course_names)} course names from Moodle.")

    # 3. Loop through each local record and check its status from Moodle
    for enrollment in enrollments:
        enrollment.course_name = course_names.get(enrollment.moodle_course_id, f'Unknown Course (ID: {enrollment.moodle_course_id})')
        
        print(f"Checking Moodle status for user ID {enrollment.moodle_user_id} in course ID {enrollment.moodle_course_id}...")
        
        function = 'core_completion_get_course_completion_status'
        params = {'courseid': enrollment.moodle_course_id, 'userid': enrollment.moodle_user_id}
        status_result = moodle_api_call(function, params)
        
        # --- THIS IS THE CRUCIAL DEBUG LINE ---
        print(f"--> Moodle API Response: {status_result}") 
        
        # 4. Safely process the response
        if isinstance(status_result, dict) and status_result.get('completionstatus'):
            if status_result['completionstatus'].get('completed'):
                enrollment.completion_status = 'Completed'
            else:
                enrollment.completion_status = 'In Progress'
        else:
            enrollment.completion_status = 'Status Unavailable' # A clearer default status
    
    print("--- Finished processing. Rendering template. ---")
    return render_template('training_status.html', enrollments=enrollments)

@app.route('/test_moodle')
def test_moodle_connection():
    print("--- RUNNING MOODLE CONNECTION TEST ---")
    
    # This is the simplest Moodle API function. It requires no parameters.
    # If this fails, the core connection (URL, Token, etc.) is broken.
    function_name = 'core_webservice_get_site_info'
    
    result = moodle_api_call(function_name)
    
    # Print the raw result to the terminal for our records
    print(f"MOODLE API TEST RESULT: {result}")
    
    # Return the result directly to the browser as JSON
    return result

@app.route('/disenroll/<int:enrollment_id>', methods=['POST'])
def disenroll(enrollment_id):
    """Disenrolls a user from a course and deletes the local record."""
    enrollment = db.session.get(Enrollment, enrollment_id)
    
    if not enrollment:
        flash("Enrollment record not found.", "error")
        return redirect(url_for('training_status'))

    function = 'enrol_manual_unenrol_users'
    params = {
        'enrolments[0][roleid]': 5,
        'enrolments[0][userid]': enrollment.moodle_user_id,
        'enrolments[0][courseid]': enrollment.moodle_course_id
    }
    result = moodle_api_call(function, params)

    # A successful disenroll returns None or a dict without an 'exception'.
    if result is None or (isinstance(result, dict) and 'exception' not in result):
        db.session.delete(enrollment)
        db.session.commit()
        flash(f"Successfully disenrolled {enrollment.user_email}.", "success")
    else:
        # This now only runs if there was a real error.
        error_message = result.get('message', 'Unknown Moodle API error.') if isinstance(result, dict) else 'Unknown Moodle API error.'
        flash(f"Moodle API error: Could not disenroll user. {error_message}", "error")

    return redirect(url_for('training_status'))

@app.route('/courses')
def courses_list():
    """Displays a list of all Moodle courses."""
    courses = moodle_api_call('core_course_get_courses') or []
    return render_template('courses_list.html', courses=courses)

@app.route('/course/<int:course_id>/users')
def course_users(course_id):
    """Displays a list of users enrolled in a specific course."""
    # First, get the course details to display the name
    course_details_func = 'core_course_get_courses_by_field'
    course_params = {'field': 'id', 'value': course_id}
    courses_response = moodle_api_call(course_details_func, course_params)
    course = courses_response['courses'][0] if courses_response and courses_response.get('courses') else {'fullname': 'Unknown'}

    # Now, get the list of enrolled users
    users_func = 'core_enrol_get_enrolled_users'
    user_params = {'courseid': course_id}
    users = moodle_api_call(users_func, user_params) or []
    
    return render_template('course_users.html', users=users, course=course)


@app.route('/user_search', methods=['GET', 'POST'])
def user_search():
    if request.method == 'POST':
        email = request.form.get('email')
        # --- Use the new, correct helper function ---
        user = get_moodle_user_by_email(email)
        
        if user:
            user_id = user['id']
            # Now get their courses
            courses_func = 'core_enrol_get_users_courses'
            courses_params = {'userid': user_id}
            courses = moodle_api_call(courses_func, courses_params) or []
            return render_template('user_search.html', courses=courses, user=user, search_attempt=True)

        # If user was not found
        return render_template('user_search.html', courses=[], user=None, search_attempt=True)
    
    # If it's a GET request, just show the search page
    return render_template('user_search.html', search_attempt=False)


@app.route('/ai_lab', methods=['GET', 'POST'])
def ai_lab():
    generated_content = None
    if request.method == 'POST':
        content_type = request.form.get('content_type')
        prompt = request.form.get('prompt')
        if content_type and prompt:
            # Show a loading message while waiting for the API
            flash("Generating content with Gemini AI, please wait...", "info")
            generated_content = generate_content(content_type, prompt)
        else:
            flash("Please select a content type and enter a prompt.", "error")
    
    return render_template('ai_lab.html', generated_content=generated_content)