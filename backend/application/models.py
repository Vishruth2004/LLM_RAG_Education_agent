from application import db
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
import werkzeug.security as ws

class User(db.Model,UserMixin):
    id=db.Column(db.Integer(),primary_key=True)
    name=db.Column(db.String(25),nullable=False)
    email=db.Column(db.String(50),unique=True)
    password=db.Column(db.String,nullable=False)
    active = db.Column(db.Boolean)
    fs_uniquifier = db.Column(db.String(255),unique=True,nullable=False)
    roles = db.relationship('Role',secondary='roles_users',
                            backref = db.backref('users',lazy='dynamic'))

class Role(db.Model,RoleMixin):
    id = db.Column(db.Integer(),primary_key=True)
    name = db.Column(db.String,unique=True)
    description = db.Column(db.String(255))

class RolesUsers(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    user_id = db.Column('user_id',db.Integer(),db.ForeignKey('user.id'))
    role_id = db.Column('role_id',db.Integer(),db.ForeignKey('role.id'))

class Course(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(25),unique=True)
    
class Registration(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.String,db.ForeignKey('user.id'))
    course_id=db.Column(db.Integer,db.ForeignKey('course.id'))
    user = db.relationship('User', backref='registrations')
    course = db.relationship('Course', backref='registrations')

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id=db.Column(db.Integer,db.ForeignKey('course.id'))
    lectureNumber = db.Column(db.Float, nullable=False)
    title = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    weekNumber = db.Column(db.Integer, nullable=False)

# ---------------------------------------------------------------------------
# AI Usage Tracking Models
# ---------------------------------------------------------------------------

class AIUsage(db.Model):
    """Tracks per-user, per-feature daily AI request counts."""
    __tablename__ = 'ai_usage'
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature = db.Column(db.String(20), nullable=False)   # 'chat' or 'mock'
    date    = db.Column(db.Date, nullable=False)
    count   = db.Column(db.Integer, default=0, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'feature', 'date', name='uq_ai_usage_user_feature_date'),
    )

class GlobalAIUsage(db.Model):
    """Tracks total AI requests across ALL users per day (global budget)."""
    __tablename__ = 'global_ai_usage'
    id    = db.Column(db.Integer, primary_key=True)
    date  = db.Column(db.Date, unique=True, nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
