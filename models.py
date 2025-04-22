from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100))
    dob = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"User('{self.email}', '{self.full_name}', Admin: {self.is_admin})"

class QuizLevel(db.Model):
    __tablename__ = 'quiz_level'  # Correct table name
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    level_name = db.Column(db.String(50), nullable=False)  # Unique primary key

    def __repr__(self):
        return f"QuizLevel('{self.level_name}')"

class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Add description column
    chapters = db.relationship('Chapter', backref='subject', lazy=True, cascade="all, delete")  # Add cascade delete for chapters

    def __init__(self, name, description=None):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"Subject('{self.name}', Description: {self.description})"

class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    max_questions = db.Column(db.Integer, nullable=False, default=0)  # Add this column

    # Relationships
    questions = db.relationship('Question', backref='chapter', lazy=True, cascade="all, delete")
    quizzes = db.relationship('Quiz', back_populates='chapter', lazy=True, cascade="all, delete")
    scores = db.relationship('Score', backref='chapter', lazy=True)

    def __repr__(self):
        return f"Chapter('{self.name}', Description: '{self.description}', Subject ID: {self.subject_id}), Max Questions: {self.max_questions})"

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)  # Add title field
    summary = db.Column(db.Text, nullable=False)  # Replace 'text' with 'summary'
    options = db.Column(db.JSON, nullable=False)  # Store options as a JSON array
    correct_option = db.Column(db.String(100), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)  # Reference Chapter table
    quiz_level_name = db.Column(db.String(50), db.ForeignKey('quiz_level.level_name'), nullable=False)  # Reference QuizLevel table

    def __repr__(self):
        return f"Question('{self.title}', '{self.summary}', '{self.correct_option}', Chapter ID: {self.chapter_id}, Level: {self.quiz_level_name})"

class Score(db.Model):
    __tablename__ = 'score'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # Number of correct answers
    total_questions = db.Column(db.Integer, nullable=False)  # Total number of questions in the quiz
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for when the score was updated

    def __repr__(self):
        return f"Score(user_id={self.user_id}, chapter_id={self.chapter_id}, score={self.score}, total_questions={self.total_questions}, timestamp={self.timestamp})"

class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    quiz_level_name = db.Column(db.String(50), nullable=False)  
    date = db.Column(db.String(10), nullable=False)  
    duration = db.Column(db.String(5), nullable=False)  

    # Relationship to fetch chapter
    chapter = db.relationship('Chapter', back_populates='quizzes', lazy=True)

    @property
    def subject(self):
        return self.chapter.subject if self.chapter else None  

    def __repr__(self):
        return f"Quiz('{self.chapter_id}', '{self.quiz_level_name}', '{self.subject_id}', '{self.date}', '{self.duration}')"
