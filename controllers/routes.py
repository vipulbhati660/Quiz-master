from flask import Flask, render_template, current_app as app, request, redirect, url_for, flash, session
from models import db, User, Subject, Chapter, Quiz, Question, Score
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func

admin = User.query.filter_by(is_admin=True).first()
if not admin:
    passhash = generate_password_hash('admin')
    admin = User(username='admin', password_hash=passhash, is_admin=True)
    db.session.add(admin)
    db.session.commit()


@app.route("/login")
def login():
    return render_template('login.html')

@app.route("/login", methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash("Please fill all fields")
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("Username does not exist")
        return redirect(url_for('login'))

    if not check_password_hash(user.password_hash, password):
        flash("Invalid password")
        return redirect(url_for('login'))

    session['user_id'] = user.id
    flash("Login successful")
    return redirect(url_for('home'))

@app.route("/register")
def register():
    return render_template('register.html')

@app.route("/register", methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    qualification = request.form.get('qualification')
    dob = request.form.get('date')
    
    if not username or not password or not qualification or not full_name:
        flash('Please fill all fields')
        return redirect(url_for('register'))

    user = User.query.filter_by(username=username).first()

    if user:
        flash('Username already exists')
        return redirect(url_for('register'))
    
    passhash = generate_password_hash(password)

    new_user = User(username=username, password_hash=passhash, full_name=full_name, qualification=qualification, dob=dob)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

def auth_requried(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('You need to be logged in to access this page')
            return redirect(url_for('login'))
    return inner

def admin_requried(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:  
            return redirect(url_for('home'))
        return func(*args, **kwargs)
    return decorated_function


@app.route("/profile")
@auth_requried
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route("/profile", methods=["POST"])
@auth_requried
def profile_post():
    username = request.form.get('username')
    cpassword = request.form.get('cpassword')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    dob = request.form.get('date')
    qualification = request.form.get('qualification')

    if not username or not cpassword or not password:
        flash('Please fill all fields')
        return redirect(url_for('profile'))

    user = User.query.get(session['user_id'])
    if not check_password_hash(user.password_hash, cpassword):
        flash("Incorrect password !")
        return redirect(url_for('profile'))

    if username != user.username:
        new_username = User.query.filter_by(username=username).first()
        if new_username:
            flash("Username alreay exits")
            return redirect(url_for('profile'))

    new_passhash = generate_password_hash(password)
    user.username = username
    user.password_hash = new_passhash
    user.full_name = full_name
    user.date = dob
    user.qualification = qualification
    db.session.commit()
    flash("Profile Updated Successfully")
    return redirect(url_for('profile'))

@app.route("/logout")
@auth_requried
def logout():
    session.pop('user_id')
    return redirect(url_for('login'))

@app.route('/search')
@auth_requried
def search():
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    source = request.args.get('source', 'quiz')
    
    if user.is_admin:
        if source == 'subjects':
            subjects = Subject.query.filter(Subject.name.ilike(f"%{query}%")).all()
            return render_template('admin.html', subjects=subjects, user=user, source=source)
        elif source == 'quiz':
            quizzes = Quiz.query.filter(Quiz.name.ilike(f"%{query}%")).all()
            return render_template('quiz.html', quizzes=quizzes, user=user, source=source)
        elif source == 'users':
            users = User.query.filter(User.username.ilike(f"%{query}%")).all()
            return render_template('user_data.html', users=users, user=user, source=source)

    else:
        if source == 'subjects':
            quizzes = Quiz.query.join(
                Chapter, Quiz.chapter_id == Chapter.id
            ).join(
                Subject, Chapter.subject_id == Subject.id
            ).filter(
                Subject.name.ilike(f"%{query}%")
            ).all()
            return render_template('index.html', quizzes=quizzes, user=user, source=source)
        elif source == 'quiz':
            quizzes = Quiz.query.filter(Quiz.name.ilike(f"%{query}%")).all()
            return render_template('index.html', quizzes=quizzes, user=user, source=source)
        elif source == 'scores':
            try:
                search_marks = int(query)
                scores = Score.query.join(
                    Quiz, Score.quiz_id == Quiz.id
                ).filter(
                    Score.user_id == user.id,
                    Score.marks == search_marks
                ).all()
                
                quizzes = [Quiz.query.get(score.quiz_id) for score in scores]
                return render_template('index.html', quizzes=quizzes, user=user, source=source)
            except ValueError:
                flash('Please enter a valid number for score search')
                return redirect(url_for('home'))
        elif source == 'dates':
            try:
                search_date = datetime.strptime(query, '%d/%m/%Y').date()
                quizzes = Quiz.query.filter(
                    func.date(Quiz.date) == search_date
                ).all()
                return render_template('index.html', quizzes=quizzes, user=user, source=source)
            except ValueError:
                flash('Invalid date format. Use DD/MM/YYYY')
                return redirect(url_for('home'))
        
@app.route('/quiz')
@admin_requried
def quiz_management():
    user = User.query.get(session['user_id'])
    quizzes = Quiz.query.all()
    return render_template('quiz.html', quizzes=quizzes, user=user)

@app.route('/quiz/<int:id>/delete')
@admin_requried
def delete_quiz(id):
    quiz = Quiz.query.get(id)
    if not quiz:
        flash("Quiz not found")
        return redirect(url_for('quiz_management'))
    
    try:
        
        Question.query.filter_by(quiz_id=id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz deleted Successfully")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting quiz")
    
    return redirect(url_for('quiz_management'))


@app.route('/quiz/<int:id>/show')
@admin_requried
def show_quiz(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    chapter = Chapter.query.get(quiz.chapter_id)
    subject = Subject.query.get(chapter.subject_id)
    return render_template('show_quiz_info.html', quiz=quiz, chapter=chapter, subject=subject, user=user)

@app.route('/quiz/<int:id>/edit')
@admin_requried
def edit_quiz(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    return render_template('edit_quiz.html', quiz=quiz, user=user)

@app.route('/quiz/<int:id>/edit', methods=['POST'])
@admin_requried
def edit_quiz_post(id):
    quiz = Quiz.query.get_or_404(id)

    quiz.name = request.form.get('quiz_title')
    quiz.no_of_question = request.form.get('no_of_question')
    quiz.marks = request.form.get('marks')
    quiz.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
    quiz.time = request.form.get('time')
    quiz.remark = request.form.get('remark')
    
    try:
        db.session.commit()
        flash('Quiz updated successfully')
    except:
        db.session.rollback()
        flash('Error updating quiz')
    
    return redirect(url_for('quiz_management'))

@app.route('/quiz/<int:id>/add_question')
@admin_requried
def add_question(id):
    user = User.query.get(session['user_id'])  
    quiz = Quiz.query.get_or_404(id)
    return render_template('question.html', quiz=quiz, user=user)

@app.route('/quiz/<int:id>/add_question', methods=['POST'])
@admin_requried
def add_question_post(id):
    quiz = Quiz.query.get_or_404(id)
    
    question = request.form.get('question_name')
    option1 = request.form.get('option1')
    option2 = request.form.get('option2')
    option3 = request.form.get('option3')
    option4 = request.form.get('option4')
    correct_option = request.form.get('correct_option')

    new_question = Question(
        question_name=question,
        option1=option1,
        option2=option2,
        option3=option3,
        option4=option4,
        correct_option=correct_option,
        quiz_id=id
    )
    
    try:
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully')
    except:
        db.session.rollback()
        flash('Error adding question')
    
    return redirect(url_for('quiz_management'))


@app.route("/quiz/<int:id>/question/<int:question_id>/edit", methods=['GET', 'POST'])
@admin_requried
def edit_question(id, question_id):
    user = User.query.get(session['user_id'])
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
       
        question.question_name = request.form.get('question_name')
        question.option1 = request.form.get('option1')
        question.option2 = request.form.get('option2')
        question.option3 = request.form.get('option3')
        question.option4 = request.form.get('option4')
        question.correct_option = request.form.get('correct_option')
        
        try:
            db.session.commit()
            flash('Question updated successfully')
            return redirect(url_for('quiz_management'))
        except:
            db.session.rollback()
            flash('Error updating question')
            
    return render_template('edit_question.html', question=question, user=user)


@app.route("/quiz/<int:id>/question/<int:question_id>/delete")
@admin_requried
def delete_question(id, question_id):
    question = Question.query.get_or_404(question_id)
    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question deleted successfully')
    except:
        db.session.rollback()
        flash('Error deleting question')
    
    return redirect(url_for('quiz_management'))

@app.route("/admin")
@admin_requried
def admin():
    user = User.query.get(session['user_id'])  
    subjects = Subject.query.all()
    return render_template('admin.html', subjects=subjects, user=user) 

@app.route("/subject/add")
@admin_requried
def subject_add():
    user = User.query.get(session['user_id'])
    return render_template('subject.html', user=user)

@app.route("/subject/add", methods=['POST'])
def subject_add_post():
    subject_name = request.form.get('name')
    subject_description = request.form.get('description')
    

    if subject_name == '':
        flash("Please enter subject name")
        return redirect(url_for('subject_add'))

    subject = Subject.query.filter_by(name=subject_name).first()
    if subject:
        flash('Subject already exists')
        return redirect(url_for('subject_add'))

    if len(subject_name) > 64:
        flash("Subject name should not exceed 64 characters")
        return redirect(url_for('subject_add'))

    new_subject = Subject(name=subject_name, description=subject_description)
    db.session.add(new_subject)
    db.session.commit()
    flash("Subject added successfully")
    return redirect(url_for('admin'))

@app.route("/subject/<int:id>/edit")
@admin_requried
def edit_subject(id):
    user = User.query.get(session['user_id'])
    subjects = Subject.query.get(id)
    if not subjects:
        flash("Subject not found")
        return redirect(url_for('admin'))
    return render_template('edit_subject.html', subjects=subjects, user=user)

@app.route("/subject/<int:id>/edit", methods=['POST'])
@admin_requried
def edit_subject_post(id):
    subjects = Subject.query.get(id)
    if not subjects:
        flash("Subject not found")
        return redirect(url_for('admin'))
    subject_name = request.form.get('name')
    subject_description = request.form.get('description')
    if not subject_name:
        flash("Please enter subject name")
        return redirect(url_for('edit_subject', id=id))
    subjects.name = subject_name
    subjects.description = subject_description
    db.session.commit()
    flash("Subject updated successfully")
    return redirect(url_for('admin'))

@app.route("/subject/<int:id>/delete")
@admin_requried
def delete_subject(id):
    subject = Subject.query.get(id)
    if not subject:
        flash("Subject not found")
        return redirect(url_for('admin'))

    try:
        
        chapters = Chapter.query.filter_by(subject_id=id).all()
        
        for chapter in chapters:
            quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
            for quiz in quizzes:
                
                Score.query.filter_by(quiz_id=quiz.id).delete()
               
                Question.query.filter_by(quiz_id=quiz.id).delete()
                
                db.session.delete(quiz)
            
            
            db.session.delete(chapter)
        
       
        db.session.delete(subject)
        db.session.commit()
        flash("Subject deleted Successfully")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting subject")
    
    return redirect(url_for('admin'))


@app.route("/chapter/add")
@admin_requried
def chapter_add():
    user = User.query.get(session['user_id'])
    subject_id = request.args.get('subject_id', type=int)
    if not subject_id:
        flash("No subject selected")
        return redirect(url_for('admin'))
    subject = Subject.query.get_or_404(subject_id)
    return render_template('chapter.html', user=user, subject=subject, chapters=None)

@app.route("/chapter/add", methods=['POST'])
def chapter_add_post():
    chapter_name = request.form.get('name')
    chapter_description = request.form.get('description')
    subject_id = request.args.get('subject_id', type=int)
    
    if not subject_id:
        flash("No subject selected")
        return redirect(url_for('admin'))
    
    subject = Subject.query.get_or_404(subject_id)

    if chapter_name == '':
        flash("Please enter chapter name")
        return redirect(url_for('chapter_add', subject_id=subject_id))

    chapter = Chapter.query.filter_by(name=chapter_name, subject_id=subject_id).first()
    if chapter:
        flash('Chapter already exists')
        return redirect(url_for('chapter_add', subject_id=subject_id))

    if len(chapter_name) > 64:
        flash("Chapter name should not exceed 64 characters")
        return redirect(url_for('chapter_add', subject_id=subject_id))

    new_Chapter = Chapter(name=chapter_name, description=chapter_description, subject_id=subject.id)
    db.session.add(new_Chapter)
    db.session.commit()
    flash("Chapter added successfully")
    return redirect(url_for('admin'))

@app.route("/chapter/<int:id>/edit")
@admin_requried
def edit_chapter(id):
    user = User.query.get(session['user_id'])
    chapters = Chapter.query.get(id)
    if not chapters:
        flash("Chapter not found")
        return redirect(url_for('admin'))
    return render_template('edit_chapter.html', chapters=chapters, user=user)

@app.route("/chapter/<int:id>/edit", methods=['POST'])
@admin_requried
def edit_chapter_post(id):
    chapters = Chapter.query.get(id)
    if not chapters:
        flash("Chapter not found")
        return redirect(url_for('admin'))
    chapter_name = request.form.get('name')
    chapter_description = request.form.get('description')
    if not chapter_name:
        flash("Please enter chapter name")
        return redirect(url_for('edit_chapter', id=id))
    chapters.name = chapter_name
    chapters.description = chapter_description
    db.session.commit()
    flash("Chapter updated successfully")
    return redirect(url_for('admin'))

@app.route("/chapter/<int:id>/delete")
@admin_requried
def delete_chapter(id):
    chapter = Chapter.query.get(id)
    if not chapter:
        flash("Chapter not found")
        return redirect(url_for('admin'))
    
    try:
        db.session.delete(chapter)
        db.session.commit()
        flash("Chapter deleted successfully")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting chapter")
    
    return redirect(url_for('admin'))

@app.route("/chapter/<int:id>/create")
@admin_requried
def create_quiz(id):
    user = User.query.get(session['user_id'])
    
    chapter_id = id
    if not chapter_id:
        flash("No chapter selected")
        return redirect(url_for('admin'))
    chapter = Chapter.query.get_or_404(chapter_id)
    return render_template('create_quiz.html', user=user, chapter=chapter)

@app.route("/chapter/<int:chapter_id>/create", methods=['POST'])
@admin_requried
def create_quiz_post(chapter_id):
    quiz_name = request.form.get('quiz_title')
    no_of_question = request.form.get('no_of_question')
    marks = request.form.get('marks')
    date = request.form.get('date')
    time = request.form.get('time')
    remark = request.form.get('remark')

    date = datetime.strptime(date, '%Y-%m-%d')
    
    
    time = int(time)

    chapter = Chapter.query.get_or_404(chapter_id)
    if quiz_name == '':
        flash("Please enter quiz name")
        return redirect(url_for('create_quiz', id=chapter_id))

    quiz = Quiz.query.filter_by(name=quiz_name, chapter_id=chapter_id).first()
    if quiz:
        flash('Quiz already exists')
        return redirect(url_for('create_quiz', id=chapter_id))

    if not marks.isdigit():
        flash("Marks should be a digit")
        return redirect(url_for('create_quiz', id=chapter_id))

    if not no_of_question.isdigit():
        flash("Number of question should be a digit")
        return redirect(url_for('create_quiz', id=chapter_id))

    # First check for 60 minutes
    if int(time) > 60:
        flash("Time should not exceed 60 minutes")
        return redirect(url_for('create_quiz', id=chapter_id))

    if int(no_of_question) <= 0 or int(marks) <= 0 or int(time) <= 0:
        flash("Number of questions, marks, and time should be positive")
        return redirect(url_for('create_quiz', id=chapter_id))

    if int(no_of_question) > 100:
        flash("Number of questions should not exceed 100")
        return redirect(url_for('create_quiz', id=chapter_id))

    if int(marks) > 100:
        flash("Marks should not exceed 100")
        return redirect(url_for('create_quiz', id=chapter_id))

    new_quiz = Quiz(name=quiz_name, no_of_question=no_of_question, marks=marks, date=date, time=time, remark=remark, chapter_id=chapter.id)
    db.session.add(new_quiz)
    db.session.commit()
    flash("Quiz created successfully")
    return redirect(url_for('admin'))

@app.route('/summary')
@admin_requried
def summary():
    user = User.query.get(session['user_id'])
    
    subject_top_scores = db.session.query(
        Subject.name.label('subject_name'),
        func.max(Score.marks).label('top_score')
    ).join(
        Quiz, Quiz.id == Score.quiz_id
    ).join(
        Chapter, Chapter.id == Quiz.chapter_id 
    ).join(
        Subject, Subject.id == Chapter.subject_id  
    ).group_by(Subject.name).all()
    

    subject_attempts = db.session.query(
        Subject.name.label('subject_name'),
        func.count(Score.id).label('attempts')
    ).join(
        Quiz, Quiz.id == Score.quiz_id
    ).join(
        Chapter, Chapter.id == Quiz.chapter_id 
    ).join(
        Subject, Subject.id == Chapter.subject_id  
    ).group_by(Subject.name).all()
    
    
    labels = [score.subject_name for score in subject_top_scores]
    top_scores = [score.top_score for score in subject_top_scores]
    attempts = [attempt.attempts for attempt in subject_attempts]
    
    return render_template('summary.html',
                         user=user,
                         labels=labels,
                         top_scores=top_scores,
                         attempts=attempts)


# USER ROUTES
@app.route('/quiz/<int:id>/view')
@auth_requried
def view_quiz(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    chapter = Chapter.query.get(quiz.chapter_id)
    subject = Subject.query.get(chapter.subject_id)
    return render_template('view_quiz.html', quiz=quiz, chapter=chapter, subject=subject, user=user)

@app.route('/quiz/<int:id>/start')
@auth_requried
def start_quiz(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter_by(quiz_id=id).all()
    
    
    session['current_question'] = 0
    session['quiz_id'] = id
    
    return render_template('start_quiz.html',
                         quiz=quiz,
                         question=questions[0],
                         question_number=1,
                         total_questions=len(questions), user=user)

@app.route('/quiz/<int:id>/save', methods=['POST'])
@auth_requried
def save_answer(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter_by(quiz_id=id).all()
    current_q = session.get('current_question', 0)
    
    answer = request.form.get('answer')
    action = request.form.get('action')
    
    if not session.get('answers'):
        session['answers'] = {}
    session['answers'][str(current_q)] = answer
    
    if action == 'submit':
        
        score = 0
        for i, question in enumerate(questions):
            user_answer = session['answers'].get(str(i))
            if user_answer and user_answer == question.correct_option:
                score += quiz.marks
        
       
        existing_score = Score.query.filter_by(user_id=user.id, quiz_id=id).first()
        if existing_score:
            existing_score.marks = score
            existing_score.timestamp = int((datetime.utcnow() + timedelta(hours=5, minutes=30)).timestamp())
        else:
            new_score = Score(
                user_id=user.id,
                quiz_id=id,
                marks=score,
                timestamp=int((datetime.utcnow() + timedelta(hours=5, minutes=30)).timestamp())
            )
            db.session.add(new_score)
        
        try:
            db.session.commit()
            session.pop('current_question', None)
            session.pop('quiz_id', None)
            session.pop('answers', None)
            flash('Quiz Submitted Successfully')
            return redirect(url_for('home'))
        except:
            db.session.rollback()
            flash('Error submitting quiz')
            return redirect(url_for('home'))
    
    
    if current_q < len(questions) - 1:
        session['current_question'] = current_q + 1
        return render_template('start_quiz.html',
                            quiz=quiz,
                            question=questions[current_q + 1],
                            question_number=current_q + 2,
                            total_questions=len(questions),
                            user=user)
    else:
        flash('No more questions left. Please press Submit to complete the quiz.')
        return render_template('start_quiz.html',
                            quiz=quiz,
                            question=questions[current_q],
                            question_number=current_q + 1,
                            total_questions=len(questions),
                            user=user)
       

@app.route('/quiz/<int:id>/submit', methods=['POST'])
@auth_requried
def submit_quiz(id):
    user = User.query.get(session['user_id'])
    quiz = Quiz.query.get_or_404(id)
    questions = Question.query.filter_by(quiz_id=id).all()
    answers = session.get('answers', {})
    score = 0
    
   
    for i, question in enumerate(questions):
        user_answer = answers.get(str(i))
        if user_answer and user_answer == question.correct_option:
            score += quiz.marks
    
    
    new_score = Score(
        user_id=user.id,
        quiz_id=id,
        marks=score
    )
    
    try:
        db.session.add(new_score)
        db.session.commit()
        session.pop('current_question', None)
        session.pop('quiz_id', None)
        session.pop('answers', None)
        flash('Quiz Submitted Successfully')
        return redirect(url_for('home'))
    except:
        db.session.rollback()
        flash('Error submitting quiz')
        return redirect(url_for('home'))

@app.route('/scores')
@auth_requried
def score():
    from datetime import datetime
    user = User.query.get(session['user_id'])
    scores = db.session.query(
        Score, Quiz
    ).join(
        Quiz, Score.quiz_id == Quiz.id
    ).filter(
        Score.user_id == user.id
    ).all()
    
    score_data = []
    for score, quiz in scores:
        score_data.append({
            'quiz': quiz,
            'score': score.marks,
            'total_marks': quiz.no_of_question * quiz.marks,
            'timestamp': score.timestamp
        })
    
    return render_template('score.html', 
                         scores=score_data, 
                         user=user,
                         datetime=datetime)


@app.route('/user_summary')
@auth_requried
def user_summary():
    user = User.query.get(session['user_id'])
    
    
    subject_quiz_counts = db.session.query(
        Subject.name.label('subject_name'),
        func.count(Score.id).label('quiz_count')
    ).join(
        Quiz, Quiz.id == Score.quiz_id
    ).join(
        Chapter, Chapter.id == Quiz.chapter_id
    ).join(
        Subject, Subject.id == Chapter.subject_id
    ).filter(
        Score.user_id == user.id
    ).group_by(Subject.name).all()
    
    
    month_attempts = db.session.query(
        func.strftime('%m', func.datetime(Score.timestamp, 'unixepoch')).label('month'),
        func.count(Score.id).label('attempts')
    ).filter(
        Score.user_id == user.id
    ).group_by('month').all()
    
    
    subjects = [item.subject_name for item in subject_quiz_counts]
    quiz_counts = [item.quiz_count for item in subject_quiz_counts]
    months = [item.month for item in month_attempts]
    attempts = [item.attempts for item in month_attempts]
    
    return render_template('user_summary.html',
                         user=user,
                         subjects=subjects,
                         quiz_counts=quiz_counts,
                         months=months,
                         attempts=attempts)

@app.route('/')
@auth_requried
def home():
    user = User.query.get(session['user_id'])
    if user.is_admin:
        return redirect(url_for('admin'))
    
    
    quizzes = Quiz.query.join(Question).group_by(Quiz.id).having(func.count(Question.id) > 0).all()
    
    return render_template('index.html', quizzes=quizzes, user=user)

@app.route('/user_data')
@admin_requried
def user_data():
    user = User.query.get(session['user_id'])
   
    users = User.query.filter(User.is_admin == False).all()
    return render_template('user_data.html', users=users, user=user)

@app.route('/user/<int:id>/delete')
@admin_requried
def delete_user(id):
    if id == session['user_id']:
        flash('Cannot delete your own account!')
        return redirect(url_for('user_data'))
        
    user_to_delete = User.query.get_or_404(id)
    
    try:
       
        Score.query.filter_by(user_id=id).delete()
        
        
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('User deleted successfully')
    except:
        db.session.rollback()
        flash('Error deleting user')
    
    return redirect(url_for('user_data'))

