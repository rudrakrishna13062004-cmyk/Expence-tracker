# Expense Tracker API

A RESTful Expense Tracker API built with FastAPI, SQLite, JWT Authentication, and bcrypt password hashing.

## Features

- User Registration
- User Login
- JWT Authentication
- Password Hashing with bcrypt
- Category Management
- Expense Management
- Create, Read, Update and Delete Expenses
- Expense Summary by Category
- SQLite Database
- REST API

## Technologies Used

- Python
- FastAPI
- SQLite
- JWT
- bcrypt
- REST API
- Pydantic
- Uvicorn

## API Endpoints

### Authentication

POST /register
- Register a new user

POST /token
- Login and get JWT access token

### Categories

POST /categories
- Create a category

GET /categories
- Get user categories

DELETE /categories/{category_id}
- Delete a category

### Expenses

POST /expenses
- Create an expense

GET /expenses
- Get all expenses

PUT /expenses/{expense_id}
- Update an expense

DELETE /expenses/{expense_id}
- Delete an expense

GET /expenses/summary
- Get expense summary by category

## How to Run

Install dependencies:

pip install -r requirements.txt

Run the application:

uvicorn main:app --reload

Open Swagger documentation:

http://127.0.0.1:8000/docs

## Database

The project uses SQLite.

The database file is created automatically when the application starts.

## Authentication

The API uses JWT Bearer Authentication to protect private endpoints.

Passwords are securely hashed using bcrypt.

## Project Structure

expense-tracker-api/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
└── .env.example
