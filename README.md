Chat Application

A real-time chat app built with FastAPI and WebSockets.
What it does

    Users can sign up and log in
    Real-time chat in different rooms
    Admin dashboard for managing users and rooms
    Message history and analytics
    Export chat data to CSV


Quick Start

Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib python-multipart jinja2



Set up database

Install PostgreSQL
Create a database called chatdb
Update the database URL in config.py if needed


Run the app


uvicorn app.main:app --reload


python run.py

Open your browser


API docs: http://localhost:8000/docs
Admin panel: http://localhost:8000/admin/dashboard
