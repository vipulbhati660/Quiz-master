from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(50), unique = True, nullable = False)
    password_hash = db.Column(db.String(256),  nullable = False)
    full_name = db.Column(db.String(100), nullable=False, default='User')
    qualification = db.Column(db.String(255), nullable = True)
    dob = db.Column(db.String(20), nullable = True)
    is_admin = db.Column(db.Boolean, nullable = False, default = False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(64), nullable = False, unique = True)
    description = db.Column(db.String(150))
    chapters = db.relationship('Chapter', backref='subject', cascade='all, delete')


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(64 ), nullable = False)
    description = db.Column(db.String(100))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(255), nullable = False)
    no_of_question = db.Column(db.Integer, nullable = False)
    marks = db.Column(db.Integer, nullable = False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.Integer, default=int(datetime.utcnow().timestamp()))
    remark = db.Column(db.String(255))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    questions = db.relationship('Question', backref='quiz', lazy=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    question_name = db.Column(db.String(300), nullable = False)
    option1 = db.Column(db.String(50), nullable = False)
    option2 = db.Column(db.String(50), nullable = False)
    option3 = db.Column(db.String(50), nullable = False)
    option4 = db.Column(db.String(50), nullable = False)
    correct_option = db.Column(db.String(50), nullable = False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable = False)

class Score(db.Model):  
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable = False)
    marks = db.Column(db.Integer, nullable = False)
    timestamp = db.Column(db.Integer, default=lambda: int(datetime.utcnow().timestamp()))
