from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
import sqlite3

app = FastAPI()

# ---------- CONFIG ----------
SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ---------- DATABASE SETUP ----------
def get_db():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- SCHEMAS ----------
class UserCreate(BaseModel):
    username: str
    password: str

class CategoryCreate(BaseModel):
    name: str

class ExpenseCreate(BaseModel):
    category_id: int | None = None
    amount: float
    description: str | None = None
    date: str  # format: YYYY-MM-DD

# ---------- PASSWORD HELPERS ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ---------- TOKEN HELPERS ----------
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    if user is None:
        raise credentials_exception
    return user

# ---------- AUTH ROUTES ----------
@app.post("/register")
def register(user: UserCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = hash_password(user.password)
    cur.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (user.username, hashed_pw))
    conn.commit()
    conn.close()
    return {"message": "User registered successfully"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    user = cur.fetchone()
    conn.close()

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# ---------- CATEGORY ROUTES ----------
@app.post("/categories")
def create_category(category: CategoryCreate, current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (current_user["id"], category.name))
    conn.commit()
    category_id = cur.lastrowid
    conn.close()
    return {"id": category_id, "name": category.name}

@app.get("/categories")
def get_categories(current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE user_id = ?", (current_user["id"],))
    categories = cur.fetchall()
    conn.close()
    return [dict(c) for c in categories]

@app.delete("/categories/{category_id}")
def delete_category(category_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, current_user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Category deleted"}

# ---------- EXPENSE ROUTES ----------
@app.post("/expenses")
def create_expense(expense: ExpenseCreate, current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, category_id, amount, description, date) VALUES (?, ?, ?, ?, ?)",
        (current_user["id"], expense.category_id, expense.amount, expense.description, expense.date)
    )
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()
    return {"id": expense_id, **expense.dict()}

@app.get("/expenses")
def get_expenses(current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", (current_user["id"],))
    expenses = cur.fetchall()
    conn.close()
    return [dict(e) for e in expenses]

@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, expense: ExpenseCreate, current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, current_user["id"]))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Expense not found")

    cur.execute(
        "UPDATE expenses SET category_id=?, amount=?, description=?, date=? WHERE id=?",
        (expense.category_id, expense.amount, expense.description, expense.date, expense_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Expense updated"}

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, current_user["id"]))
    conn.commit()
    conn.close()
    return {"message": "Expense deleted"}

# ---------- SUMMARY ROUTE ----------
@app.get("/expenses/summary")
def expense_summary(current_user=Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT categories.name as category_name, SUM(expenses.amount) as total
        FROM expenses
        LEFT JOIN categories ON expenses.category_id = categories.id
        WHERE expenses.user_id = ?
        GROUP BY expenses.category_id
    """, (current_user["id"],))
    summary = cur.fetchall()
    conn.close()
    return [dict(s) for s in summary]

@app.get("/")
def root():
    return {"message": "Expense Tracker API is running"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)    
