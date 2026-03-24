# Yelp Prototype: DATA 228 Lab 1
## Instructions to Run:

## Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- MySQL 8+

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/suryasreddy/Yelp.git
cd Yelp
```

---

## Step 2 — Create the MySQL Database

Open **MySQL Workbench** and run:

```sql
CREATE DATABASE yelp_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

---

## Step 3 — Create the `.env` File

Create a file called `.env` inside the `backend/` folder:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/yelp_db
SECRET_KEY=supersecretkey123456789
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=uploads
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
```

---

## Step 4 — Backend Setup

```bash
cd backend

python3.11 -m venv venv

source venv/bin/activate

pip install -r requirements.txt
pip install bcrypt==4.0.1
pip install langchain-openai --upgrade
pip install langchain-community --upgrade
```

---

## Step 5 — Start the Backend

```bash
python -m uvicorn main:app --port 8000
```

---

## Step 6 — Seed the Database

Open a **new terminal**:

```bash
cd backend

source venv/bin/activate

python seed.py
```

---

## Step 7 — Frontend Setup

Open a **new terminal**:

```bash
cd frontend

npm install

echo "REACT_APP_API_URL=http://localhost:8000" > .env

npm start
```

---

## App URLs

- **Frontend:** http://localhost:3000  
- **API Docs:** http://localhost:8000/docs  

---

## Test Accounts

| Email | Password | Role |
|------|----------|------|
| alice@example.com | password123 | Reviewer |
| bob@example.com | password123 | Reviewer |
| sofia@example.com | password123 | Reviewer |
| owner@example.com | password123 | Owner |
