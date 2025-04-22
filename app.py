from flask import Flask, render_template, redirect, url_for, flash, request, session,make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import RegistrationForm, LoginForm
from models import db, bcrypt, User, Subject, Chapter, Question, Score ,QuizLevel,Quiz# Updated imports
from config import Config
from datetime import datetime
from sqlalchemy import extract, func

# **Ensure db is created within app context**

app = Flask(__name__)
app.config.from_object(Config)

# **Initialize extensions here**
db.init_app(app)
from flask_migrate import Migrate

migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)  # **Now login_manager is properly initialized**
login_manager.login_view = 'login'  # **Redirect unauthorized users to login**

# Global variable to store added quizzes
added_quizzes = []

@app.route('/')
def home():
    return render_template('home.html')

# @app.route('/')
# def home():
#     return redirect(url_for('login'))  # Redirect to login page or another public page


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Use db.session.get() instead of User.query.get()

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

@app.after_request
def add_cache_control(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Check email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))  # Redirect to the home page after logout

# Route to edit a chapter
@app.route('/admin/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def edit_chapter(chapter_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    # Fetch the chapter based on its ID
    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':
        chapter.name = request.form.get('chapter_name', chapter.name)
        chapter.description = request.form.get('chapter_description', chapter.description)
        db.session.commit()
        flash("Chapter updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_chapter.html', chapter=chapter)









@app.context_processor
def inject_now():
    return {'now': datetime.now}
















# Route to delete a chapter
@app.route('/admin/delete_chapter/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def delete_chapter(chapter_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    # Fetch the chapter based on its ID
    chapter = Chapter.query.get_or_404(chapter_id)

    # Delete all associated quizzes
    for quiz in chapter.quizzes:
        db.session.delete(quiz)

    # Delete all associated questions
    for question in chapter.questions:
        db.session.delete(question)

    # Delete the chapter
    db.session.delete(chapter)
    db.session.commit()
    flash("Chapter, its associated quizzes, and questions deleted successfully!", 'danger')
    return redirect(url_for('admin_dashboard'))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Use db.session.get() instead of User.query.get()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        is_admin = form.email.data == "admin@example.com"
        user = User(email=form.email.data, password=hashed_password,
                    full_name=form.full_name.data, qualification=form.qualification.data,
                    dob=form.dob.data, is_admin=is_admin)  # <-- Store admin flag
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)
# Dashboard Route

@app.route('/dashboard')
@login_required
def dashboard():
    if getattr(current_user, "is_admin", False):  # Safe check
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    # Fetch filter parameters
    selected_level = request.args.get('quiz_level', '').strip()
    selected_subject = request.args.get('subject', '').strip()

    # Fetch upcoming quizzes with optional filters
    query = Quiz.query.join(Chapter).join(Subject)
    if selected_level:
        query = query.filter(Quiz.quiz_level_name == selected_level)
    if selected_subject:
        query = query.filter(Quiz.subject_id == selected_subject)

    upcoming_quizzes = query.all()
    quiz_levels = QuizLevel.query.all()
    subjects = Subject.query.all()

    return render_template(
        'user_dashboard.html',
        user=current_user,
        upcoming_quizzes=upcoming_quizzes,
        quiz_levels=quiz_levels,
        subjects=subjects,
        selected_level=selected_level,
        selected_subject=selected_subject
    )

#today's changes
@app.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '').strip()  # Get the search query from the URL parameters

    if request.method == 'POST':
        # Handle adding a subject
        if 'subject_name' in request.form:
            subject_name = request.form.get('subject_name')
            description = request.form.get('description')

            if not subject_name:
                flash('Subject name cannot be empty.', 'danger')
                return redirect(url_for('admin_dashboard'))

            new_subject = Subject(name=subject_name, description=description)
            try:
                db.session.add(new_subject)
                db.session.commit()
                flash('Subject added successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding subject: {str(e)}', 'danger')

    # Fetch subjects and filter by search query if provided
    if search_query:
        subjects = Subject.query.filter(Subject.name.ilike(f'%{search_query}%')).all()
    else:
        subjects = Subject.query.all()

    # Fetch chapters for each subject
    chapters = {
        subject.id: Chapter.query.filter_by(subject_id=subject.id).all()
        for subject in subjects
    }

    return render_template(
        'admin_dashboard.html',
        subjects=subjects,
        chapters=chapters,
        search_query=search_query
    )
# @app.route("/summary")
# @login_required
# def summary():
#     # Fetching the current year and month
#     current_month = datetime.now().month  # Integer format (1-12)
#     current_year = datetime.now().year   # Integer format (YYYY)

#     # Fetching total quizzes attempted per subject (Overall)
#     overall_results = (
#         db.session.query(Subject.name, db.func.count(Score.id))
#         .join(Chapter, Subject.id == Chapter.subject_id)
#         .join(Quiz, Chapter.id == Quiz.chapter_id)
#         .outerjoin(Score, (Score.chapter_id == Chapter.id) & (Score.user_id == current_user.id))
#         .group_by(Subject.name)
#         .all()
#     )

#     # Fetching quizzes attempted per subject in the current month
#     monthly_results = (
#     db.session.query(Subject.name, db.func.count(Score.id))
#     .join(Chapter, Subject.id == Chapter.subject_id)
#     .join(Quiz, Chapter.id == Quiz.chapter_id)
#     .outerjoin(Score, (Score.chapter_id == Chapter.id) & (Score.user_id == current_user.id))
#     .filter(extract('year', Score.timestamp) == current_year)   
#     .filter(extract('month', Score.timestamp) == current_month)
#     .group_by(Subject.name)
#     .all()
#     )
#     # Extracting subject names and their corresponding quiz counts
#     overall_subject_names = [row[0] for row in overall_results]
#     overall_quiz_counts = [row[1] for row in overall_results]

#     monthly_subject_names = [row[0] for row in monthly_results]
#     monthly_quiz_counts = [row[1] for row in monthly_results]

#     return render_template(
#         "summary.html",
#         subject_names=overall_subject_names,
#         subject_quiz_counts=overall_quiz_counts,
#         month_subject_names=monthly_subject_names,
#         month_subject_quiz_counts=monthly_quiz_counts
#     )


















@app.route("/user/summary")
@login_required
def user_summary():
    """Summary for logged-in users"""
    current_month = datetime.now().month  
    current_year = datetime.now().year  

    # Fetch total quizzes attempted per subject (Overall)
    overall_results = (
        db.session.query(Subject.name, db.func.count(Score.id))
        .join(Chapter, Subject.id == Chapter.subject_id)
        .join(Quiz, Chapter.id == Quiz.chapter_id)
        .outerjoin(Score, (Score.chapter_id == Chapter.id) & (Score.user_id == current_user.id))
        .group_by(Subject.name)
        .all()
    )

    # Fetch quizzes attempted in the current month
    monthly_results = (
        db.session.query(Subject.name, db.func.count(Score.id))
        .join(Chapter, Subject.id == Chapter.subject_id)
        .join(Quiz, Chapter.id == Quiz.chapter_id)
        .outerjoin(Score, (Score.chapter_id == Chapter.id) & (Score.user_id == current_user.id))
        .filter(extract('year', Score.timestamp) == current_year)   
        .filter(extract('month', Score.timestamp) == current_month)
        .group_by(Subject.name)
        .all()
    )

    # Extracting subject names and quiz counts
    overall_subject_names = [row[0] for row in overall_results]
    overall_quiz_counts = [row[1] for row in overall_results]

    monthly_subject_names = [row[0] for row in monthly_results]
    monthly_quiz_counts = [row[1] for row in monthly_results]

    return render_template(
        "summary.html",
        subject_names=overall_subject_names,
        subject_quiz_counts=overall_quiz_counts,
        month_subject_names=monthly_subject_names,
        month_subject_quiz_counts=monthly_quiz_counts,
        user_type="user"  # Pass user type for clarity
    )






















@app.route("/admin_summary")
@login_required
def admin_summary():
    if not current_user.is_admin:
        return "Unauthorized", 403  

    # Fetch highest score per subject along with total possible score
    subquery = (
        db.session.query(
            Subject.name.label("subject_name"),
            func.coalesce(func.max(Score.score), 0).label("top_score"),  # Highest user score
            func.coalesce(func.sum(Score.score), 0).label("total_possible_score")  # Sum of max possible marks
        )
        .join(Chapter, Subject.id == Chapter.subject_id)
        .outerjoin(Score, Score.chapter_id == Chapter.id)  # Get scores from chapters
        .group_by(Subject.name)
        .subquery()
    )

    # Fetch subject names and correct percentage scores
    top_scores = db.session.query(
        subquery.c.subject_name, 
        subquery.c.top_score, 
        subquery.c.total_possible_score
    ).all()

    subject_names = []
    top_scores_percentages = []

    for row in top_scores:
        subject_name = row[0]
        top_score = row[1]
        total_possible_score = row[2]

        # Calculate percentage correctly
        percentage = (top_score / total_possible_score) * 100 if total_possible_score > 0 else 0
        subject_names.append(f"{subject_name} ({percentage:.2f}%)")  # Show percentage in subject name
        top_scores_percentages.append(percentage)

    # Fetch subject-wise user attempts
    user_attempts = (
        db.session.query(Subject.name, func.count(Score.id))
        .join(Chapter, Subject.id == Chapter.subject_id)
        .outerjoin(Score, Score.chapter_id == Chapter.id)
        .group_by(Subject.name)
        .all()
    )

    attempt_labels = [row[0] for row in user_attempts]
    attempt_counts = [row[1] for row in user_attempts]

    return render_template(
        "admin_summary.html",
        subject_names=subject_names,  # Names with correct percentages
        top_scores_values=top_scores_percentages,  # Correct percentage values
        attempt_labels=attempt_labels,
        attempt_counts=attempt_counts
    )




@app.route('/add_question/<int:chapter_id>/<string:quiz_level_name>', methods=['GET', 'POST'])
@login_required
def add_question(chapter_id, quiz_level_name):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':
        question_title = request.form.get('question_title')
        question_summary = request.form.get('question_summary')
        options = request.form.getlist('options[]')
        correct_option = request.form.get('correct_option')

        # Validate inputs
        if len(options) != 4:
            flash('Exactly 4 options are required.', 'danger')
            return redirect(url_for('add_question', chapter_id=chapter_id, quiz_level_name=quiz_level_name))

        if not correct_option.isdigit() or int(correct_option) < 1 or int(correct_option) > 4:
            flash('Correct option must be a number between 1 and 4.', 'danger')
            return redirect(url_for('add_question', chapter_id=chapter_id, quiz_level_name=quiz_level_name))

        # Add the question to the database
        new_question = Question(
            title=question_title,
            summary=question_summary,
            options=options,
            correct_option=options[int(correct_option) - 1],
            chapter_id=chapter_id,
            quiz_level_name=quiz_level_name
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('add_question', chapter_id=chapter_id, quiz_level_name=quiz_level_name))

    questions = Question.query.filter_by(chapter_id=chapter_id, quiz_level_name=quiz_level_name).all()
    return render_template('add_question.html', chapter=chapter, questions=questions, quiz_level_name=quiz_level_name)

@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        question.title = request.form.get('question_title')
        question.summary = request.form.get('question_summary')
        options = request.form.getlist('options[]')
        correct_option = request.form.get('correct_option')

        # Validate inputs
        if len(options) != 4:
            flash('Exactly 4 options are required.', 'danger')
            return redirect(url_for('edit_question', question_id=question_id))

        if not correct_option.isdigit() or int(correct_option) < 1 or int(correct_option) > 4:
            flash('Correct option must be a number between 1 and 4.', 'danger')
            return redirect(url_for('edit_question', question_id=question_id))

        # Update the question
        question.options = options
        question.correct_option = options[int(correct_option) - 1]
        db.session.commit()
        flash("Question updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_question.html', question=question)

from sqlalchemy.sql import text  # Import text for raw SQL queries

@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()

    # Reset auto-increment if no questions exist
    if Question.query.count() == 0:
        db.session.execute(text("DELETE FROM sqlite_sequence WHERE name='question'"))
        db.session.commit()

    flash("Question deleted successfully!", "danger")
    return redirect(url_for('admin_quiz'))  # Redirect to refresh data

@app.route('/select_quiz', methods=['POST'])
@login_required
def select_quiz():
    quiz_type = request.form['quiz_type']
    return redirect(url_for('select_subject', quiz_type=quiz_type))

@app.route('/select_subject/<quiz_type>', methods=['GET', 'POST'])
@login_required
def select_subject(quiz_type):
    subjects = Subject.query.all()
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        return redirect(url_for('select_chapter', quiz_type=quiz_type, subject_id=subject_id))
    return render_template('select_subject.html', quiz_type=quiz_type, subjects=subjects)

@app.route('/select_chapter/<quiz_type>/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def select_chapter(quiz_type, subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if request.method == 'POST':
        chapter_id = request.form['chapter_id']
        return redirect(url_for('start_quiz', quiz_type=quiz_type, subject_id=subject_id, chapter_id=chapter_id))
    return render_template('select_chapter.html', quiz_type=quiz_type, subject=subject)

@app.route('/start_quiz/<string:quiz_type>/<int:subject_id>/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def start_quiz(quiz_type, subject_id, chapter_id):
    # Ensure the chapter exists and belongs to the selected subject
    chapter = Chapter.query.filter_by(id=chapter_id, subject_id=subject_id).first_or_404()
    questions = Question.query.filter_by(chapter_id=chapter_id, quiz_level_name=quiz_type).all()  # Filter by quiz level
    if not questions:
        flash("No questions available for this chapter and quiz type.", "warning")
        return redirect(url_for('user_dashboard'))

    # Clear session data for the quiz to reset previous answers
    for index in range(len(questions)):
        session.pop(f'quiz_{chapter_id}_q{index}', None)

    # Start with the first question
    return redirect(url_for('quiz_question', chapter_id=chapter_id, question_index=0))

@app.route('/quiz_question/<int:chapter_id>/<int:question_index>', methods=['GET', 'POST'])
@login_required
def quiz_question(chapter_id, question_index):
    chapter = Chapter.query.get_or_404(chapter_id)
    questions = Question.query.filter_by(chapter_id=chapter_id).all()

    if request.method == 'POST':
        selected_option = request.form.get('selected_option')
        action = request.form.get('action')

        # Save the selected option in the session
        if selected_option:
            session[f'quiz_{chapter_id}_q{question_index}'] = selected_option

        # Handle navigation
        if action == 'save_next' and question_index < len(questions) - 1:
            return redirect(url_for('quiz_question', chapter_id=chapter_id, question_index=question_index + 1))
        elif action == 'previous' and question_index > 0:
            return redirect(url_for('quiz_question', chapter_id=chapter_id, question_index=question_index - 1))
        elif action == 'submit':
            return redirect(url_for('submit_quiz', chapter_id=chapter_id))

    # Render the current question
    question = questions[question_index]
    return render_template(
        'quiz_question.html',
        chapter=chapter,
        question=question,
        question_index=question_index,
        total_questions=len(questions)
    )

@app.route('/submit_quiz/<int:chapter_id>', methods=['POST'])
@login_required
def submit_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    questions = Question.query.filter_by(chapter_id=chapter_id).all()

    correct_answers = 0
    total_questions = len(questions)

    for index, question in enumerate(questions):
        selected_option = session.get(f'quiz_{chapter_id}_q{index}')
        if selected_option and selected_option == question.correct_option:
            correct_answers += 1

    # Save or update the score in the database
    existing_score = Score.query.filter_by(user_id=current_user.id, chapter_id=chapter_id).first()
    if existing_score:
        existing_score.score = correct_answers
        existing_score.total_questions = total_questions
        existing_score.timestamp = datetime.utcnow()
    else:
        new_score = Score(
            user_id=current_user.id,
            chapter_id=chapter_id,
            score=correct_answers,
            total_questions=total_questions,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_score)
    db.session.commit()

    # Store results in the session for redirection
    session['quiz_results'] = {
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'percentage': round((correct_answers / total_questions) * 100, 2) if total_questions > 0 else 0
    }

    return redirect(url_for('quiz_result', chapter_id=chapter_id))

@app.route('/quiz_result/<int:chapter_id>', methods=['GET'])
@login_required
def quiz_result(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    results = session.pop('quiz_results', None)  # Retrieve and clear results from the session

    if not results:
        flash("No quiz results found. Please try again.", "warning")
        return redirect(url_for('user_dashboard'))

    return render_template(
        'quiz_result.html',
        chapter=chapter,
        correct_answers=results['correct_answers'],
        total_questions=results['total_questions'],
        percentage=results['percentage']
    )

@app.route('/retry_quiz/<string:quiz_type>/<int:subject_id>/<int:chapter_id>', methods=['GET'])
@login_required
def retry_quiz(quiz_type, subject_id, chapter_id):
    # Clear session data for the quiz to reset previous answers
    questions = Question.query.filter_by(chapter_id=chapter_id, quiz_level_name=quiz_type).all()
    for index in range(len(questions)):
        session.pop(f'quiz_{chapter_id}_q{index}', None)

    # Redirect to start the quiz fresh
    return redirect(url_for('start_quiz', quiz_type=quiz_type, subject_id=subject_id, chapter_id=chapter_id))

@app.route('/scores')
@login_required
def scores():
    user_scores = (
        db.session.query(
            Score,
            Chapter.name,
            func.count(Question.id).label('max_questions')  # Dynamically calculate max questions
        )
        .join(Chapter, Score.chapter_id == Chapter.id)
        .join(Question, Question.chapter_id == Chapter.id)
        .filter(Score.user_id == current_user.id)
        .group_by(Score.id, Chapter.name)  # Group by Score and Chapter name
        .all()
    )

    # Include the timestamp (date) and calculate the percentage in the scores data
    scores_data = [
        (
            score,
            chapter_name,
            max_questions,
            f"{score.score}/{score.total_questions}",
            round((score.score / score.total_questions) * 100, 2) if score.total_questions > 0 else 0
        )
        for score, chapter_name, max_questions in user_scores
    ]

    return render_template('scores.html', scores=scores_data)

@app.route('/admin/edit_quiz/<int:chapter_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(chapter_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    chapter = Chapter.query.get_or_404(chapter_id)
    if request.method == 'POST':
        chapter.name = request.form.get('chapter_name', chapter.name)
        chapter.num_questions = request.form.get('num_questions', chapter.num_questions)
        db.session.commit()
        flash('Quiz updated successfully!', 'success')
        return redirect(url_for('admin_quiz'))
    return render_template('edit_quiz.html', chapter=chapter)

@app.route('/admin/delete_quiz/<int:chapter_id>', methods=['POST'])
@login_required
def delete_quiz(chapter_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    chapter = Chapter.query.get_or_404(chapter_id)
    db.session.delete(chapter)
    db.session.commit()
    flash('Quiz deleted successfully!', 'danger')
    return redirect(url_for('admin_quiz'))

@app.route('/admin/add_quiz_form', methods=['GET'])
@login_required
def add_quiz_form():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('add_quiz_form.html')

@app.route('/admin/add_quiz', methods=['GET', 'POST'])
@login_required
def add_quiz():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    quiz_levels = QuizLevel.query.all()  # Fetch all quiz levels for the dropdown

    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        quiz_level_name = request.form.get('quiz_level')  # Get the selected quiz level
        date = request.form.get('date')  # Expected format: xx/xx/yyyy
        duration = request.form.get('duration')  # Expected format: hh:mm

        if not chapter_id or not quiz_level_name or not date or not duration:
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_quiz'))

        # Validate chapter ID
        chapter = Chapter.query.get(chapter_id)
        if not chapter:
            flash('Invalid Chapter ID.', 'danger')
            return redirect(url_for('add_quiz'))

        # Validate quiz level
        quiz_level = QuizLevel.query.filter_by(level_name=quiz_level_name).first()
        if not quiz_level:
            flash('Invalid Quiz Level.', 'danger')
            return redirect(url_for('add_quiz'))

        # Fetch subject
        subject = Subject.query.get(chapter.subject_id)
        if not subject:
            flash('Invalid Subject.', 'danger')
            return redirect(url_for('add_quiz'))

        # Store quiz details in the database
        new_quiz = Quiz(
            chapter_id=chapter_id,
            subject_id=subject.id,
            quiz_level_name=quiz_level_name,  # Associate quiz level with the quiz
            date=date,
            duration=duration
        )
        db.session.add(new_quiz)
        db.session.commit()

        flash(f'Quiz added successfully for Chapter: {chapter.name}', 'success')
        return redirect(url_for('admin_quiz'))

    return render_template('add_quiz.html', quiz_levels=quiz_levels)

@app.route('/admin/add_independent_subject', methods=['GET', 'POST'])
@login_required
def add_independent_subject():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        description = request.form.get('description')

        if not subject_name or not description:
            flash('Subject name and description cannot be empty.', 'danger')
            return redirect(url_for('admin_dashboard'))

        # Create a new subject without associating it with a quiz level
        new_subject = Subject(name=subject_name)
        try:
            db.session.add(new_subject)
            db.session.commit()
            flash('Independent subject added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding subject: {str(e)}', 'danger')

        return redirect(url_for('admin_dashboard'))

    return render_template('add_independent_subject.html')

@app.route('/view_quiz/<int:quiz_id>', methods=['GET'])
@login_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('view_quiz.html', quiz=quiz)

@app.route('/admin/view_subjects', methods=['GET'])
@login_required
def view_subjects():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    subjects = Subject.query.all()
    return render_template('view_subjects.html', subjects=subjects)

@app.route('/admin/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)
    if request.method == 'POST':
        subject.name = request.form.get('subject_name', subject.name)
        subject.description = request.form.get('subject_description', subject.description)
        db.session.commit()
        flash("Subject updated successfully!", "success")
        return redirect(url_for('view_subjects'))

    return render_template('edit_subject.html', subject=subject)

@app.route('/admin/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)

    # Delete all associated chapters and their questions
    for chapter in subject.chapters:
        for question in chapter.questions:
            db.session.delete(question)
        db.session.delete(chapter)

    # Delete the subject
    db.session.delete(subject)
    db.session.commit()
    flash("Subject, its associated chapters, and questions deleted successfully!", "danger")
    return redirect(url_for('view_subjects'))

@app.route('/admin/view_users', methods=['GET'])
@login_required
def view_users():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    # Fetch only non-admin users
    users = User.query.filter_by(is_admin=False).all()
    return render_template('view_users.html', users=users)

@app.route('/admin/add_chapter/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def add_chapter(subject_id):
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    subject = Subject.query.get_or_404(subject_id)

    if request.method == 'POST':
        chapter_name = request.form.get('chapter_name')
        chapter_description = request.form.get('chapter_description')

        if not chapter_name or not chapter_description:
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_chapter', subject_id=subject_id))

        # Create and add the new chapter
        new_chapter = Chapter(
            name=chapter_name,
            description=chapter_description,
            subject_id=subject_id
        )
        db.session.add(new_chapter)
        db.session.commit()
        flash('Chapter added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_chapter.html', subject=subject)

@app.route('/admin/quiz', methods=['GET'])
@login_required
def admin_quiz():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

    # Fetch all quiz levels and chapters
    quiz_levels = QuizLevel.query.all()
    quiz_chapters = Chapter.query.all()

    # Filter quizzes by level if a filter is applied
    selected_level = request.args.get('quiz_level', '').strip()
    return render_template(
        'quiz.html',
        quiz_levels=quiz_levels,
        quiz_chapters=quiz_chapters,
        selected_level=selected_level
    )

if __name__ == '__main__':
    app.run(debug=True)