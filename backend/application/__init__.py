from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from application.config import Config
from flask_security import SQLAlchemyUserDatastore
import os
import pickle

base_dir = os.path.abspath(os.path.dirname(__file__))
template_folder = os.path.join(base_dir, '..','..','frontend', 'templates')
static_folder = os.path.join(base_dir,'..','..','frontend', 'static')


import gc

_current_loaded_week = None
_current_faiss_index = None

def load_faiss_for_week(week):
    global _current_loaded_week, _current_faiss_index

    # 1. If this exact week is already in RAM, reuse it immediately
    if _current_loaded_week == week and _current_faiss_index is not None:
        return _current_faiss_index

    # 2. Free previous index from memory and force garbage collection
    _current_faiss_index = None
    _current_loaded_week = None
    gc.collect()

    # 3. Locate the week-specific file
    faiss_folder = os.path.join(base_dir, '..', 'FAISS')
    faiss_index_path = os.path.join(faiss_folder, f"faiss_index_week{week}.pkl")

    # Fallback to combined index if the week-specific file doesn't exist
    if not os.path.exists(faiss_index_path):
        faiss_index_path = os.path.join(faiss_folder, "faiss_index_all_weeks.pkl")
        if not os.path.exists(faiss_index_path):
            print(f"FAISS index for Week {week} not found.")
            return None

    # 4. Load only the requested index into memory
    try:
        with open(faiss_index_path, "rb") as f:
            _current_faiss_index = pickle.load(f)
            _current_loaded_week = week
    except Exception as e:
        print(f"Warning: Could not load FAISS index for week {week}: {e}")
        return None
        
    return _current_faiss_index  

app = Flask(__name__,template_folder=template_folder,static_folder=static_folder)
app.config.from_object(Config)
db = SQLAlchemy(app)
api = Api(app)

# Initialize models after app context is created
from application.models import User,Role,Lecture,Course

def create_datastore():
    # Initialize datastore after the app context
    datastore = SQLAlchemyUserDatastore(db, User, Role)
    return datastore

with app.app_context():

    db.create_all()

    datastore  = create_datastore()
    datastore.find_or_create_role(name='admin',description='Admin role')
    datastore.find_or_create_role(name='user',description='User role')
    
#     if not datastore.find_user(email='admin@email.com'):
#         datastore.create_user(email='admin@email.com',password=generate_password_hash('admin'),name='admin',roles=['admin'])
    
    default_courses = ["Business Analytics", "Software Engineering", "Software Testing", "Deep Learning"]

    for course_name in default_courses:
        course = Course.query.filter_by(name=course_name).first() # Check duplicates
        if not course:
            new_course = Course(name=course_name)
            db.session.add(new_course)
            db.session.commit() # Commit to get the course ID
        
            # Insert default lectures for the new course
            if new_course.name == 'Business Analytics':
                default_lectures = [
                    {'course_id': new_course.id, 'lectureNumber': '1.1', 'title': 'Introduction to Data Visualization', 'link': 'https://youtu.be/_0z2c-Awpt0', 'weekNumber': 1},
                    {'course_id': new_course.id, 'lectureNumber': '1.2', 'title': 'Defining the Message', 'link': 'https://youtu.be/1zWJyhv6j_g', 'weekNumber': 1},
                    {'course_id': new_course.id, 'lectureNumber': '1.3', 'title': 'Creating Designs', 'link': 'https://youtu.be/lLvRWjclPus', 'weekNumber': 1},
                    {'course_id': new_course.id, 'lectureNumber': '2.1', 'title': 'Probability Distributions', 'link': 'https://youtu.be/yMFsKaMRqdw', 'weekNumber': 2},
                    {'course_id': new_course.id, 'lectureNumber': '2.2', 'title': 'Business Example', 'link': 'https://youtu.be/ePqGFuLnVFM', 'weekNumber': 2},
                    {'course_id': new_course.id, 'lectureNumber': '2.3', 'title': 'Guessing the Distribution', 'link': 'https://youtu.be/UM-3E8fsCgA', 'weekNumber': 2},
                    {'course_id': new_course.id, 'lectureNumber': '3.1', 'title': 'Determining Association Between Categorical Variables', 'link': 'https://youtu.be/wWFK-N7RTKU', 'weekNumber': 3},
                    {'course_id': new_course.id, 'lectureNumber': '3.2', 'title': 'Bayes\' Rule', 'link': 'https://youtu.be/O1-fspYUq6g', 'weekNumber': 3},
                    {'course_id': new_course.id, 'lectureNumber': '3.3', 'title': 'Chi-Squared Test of Independence', 'link': 'https://youtu.be/obVldwZBm0c', 'weekNumber': 3},
                    {'course_id': new_course.id, 'lectureNumber': '3.4', 'title': 'Implementation in Python', 'link': 'https://youtu.be/8eeRkqA1YO4', 'weekNumber': 3},
                    {'course_id': new_course.id, 'lectureNumber': '3.5', 'title': 'Implementation in Spreadsheets', 'link': 'https://youtu.be/IFLk64kNdSE', 'weekNumber': 3}
                ]

                for lecture_data in default_lectures:
                    lecture = Lecture.query.filter_by(course_id=lecture_data['course_id'], lectureNumber=lecture_data['lectureNumber']).first()
                    if not lecture:
                        new_lecture = Lecture(
                                                course_id=lecture_data['course_id'],
                                                lectureNumber=lecture_data['lectureNumber'],
                                                title=lecture_data['title'],
                                                link=lecture_data['link'],
                                                weekNumber=lecture_data['weekNumber']
                                            )
                        db.session.add(new_lecture)

    db.session.commit()

    weeks = {lecture.weekNumber for lecture in Lecture.query.distinct(Lecture.weekNumber).all()}
    class DynamicFaissStore:
        def __getitem__(self, week):
            return load_faiss_for_week(week)
        def get(self, week, default=None):
            idx = load_faiss_for_week(week)
            return idx if idx is not None else default
    
    faiss_store = DynamicFaissStore()
    faiss_cache = faiss_store



# Import the controllers after app context is set up
from . import controllers
