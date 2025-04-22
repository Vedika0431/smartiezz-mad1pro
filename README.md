# Quiz Master - V1

## Author

**Name**: Vedika Santosh Vangar
**Roll Number**: 23f3000802
**Email:** 23f3000802@ds.study.iitm.ac.in

Description

Quiz Master is a multi-user quiz management system developed using Flask, SQLite, and Jinja2. It provides user authentication, quiz creation, question management, and result tracking.

## Technologies Used

- **Programming Language:** Python

* **Framework:** Flask

- **User Authentication:** Flask-Login, Flask-Bcrypt

* **Database Migrations:** Flask-Migrate





Database Migrations: Flask-Migrate Installation & Setup

1. **Create a Virtual Environment**

   python -m venv venv
   source venv/bin/activate  
   'venv\Scripts\activate'    # On Windows use 
   

2. **Install Dependencies**
   pip install -r requirements.txt


3. **Set Up the Database**
   flask db init
   flask db migrate -m "Initial migration."
   flask db upgrade


4. **Run the Application**
   flask run or python app.py

5. **Access**
   Open `http://127.0.0.1:5000` in your browser.

## Database Schema


- **User** - Stores user information including authentication details
- **QuizLevel** - Defines different quiz difficulty levels
- **Subject** - Stores subjects related to quizzes
- **Chapter** - Subcategories within subjects
- **Question** - Stores quiz questions with multiple-choice answers
- **Score** - Tracks user quiz performance
- **Quiz** - Manages quiz events and scheduling

## Features

- User authentication (Admin & Non-Admin)
- Quiz creation and management
- Question bank with options & correct answers
- Score tracking and history

## Notes

- Default admin credentials should be set in the database manually.
- The `config.py` file must be correctly configured before running the project.
- All dependencies should be installed in a virtual environment to avoid conflicts.

# **admin login**

**admin email:** admin@example.com

**admin password:** admin1



## Video Demonstration
https://drive.google.com/file/d/1EXW7cmMo9vy5rbsUmOQeLM4Hr1TQK0Jl/view?usp=sharing
