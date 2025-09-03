from . import db  # Imports the db object from our __init__.py file

# --- DATABASE MODEL ---
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gophish_campaign_id = db.Column(db.Integer, nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    moodle_user_id = db.Column(db.Integer, nullable=False)
    moodle_course_id = db.Column(db.Integer, nullable=False)
    enrollment_timestamp = db.Column(db.DateTime, server_default=db.func.now())
    completion_status = db.Column(db.String(50), default='Enrolled')

    def __repr__(self):
        return f'<Enrollment {self.user_email} in Course {self.moodle_course_id}>'