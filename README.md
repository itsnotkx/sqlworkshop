# SQL Workshop Application

## Local Development Setup

### 1. Create and Activate Virtual Environment
```bash
py -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Supabase Database Setup

#### A. Create Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and sign in
2. Create a new project
3. Save your project URL and API keys

#### B. Load Your Database Schema
1. In Supabase Dashboard, go to **SQL Editor**
2. Run your `create_insert.sql` script to create tables and insert data

#### C. Create SQL Execution Function
In Supabase SQL Editor, run this to create the `exec_sql` function:
```sql
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result json;
BEGIN
  EXECUTE format('SELECT json_agg(t) FROM (%s) t', query) INTO result;
  RETURN COALESCE(result, '[]'::json);
END;
$$;
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
```

### 5. Run Locally
```bash
py app.py
```
The app will be available at `http://localhost:5000`

### 6. Test with ngrok (Optional - for local testing)
```bash
ngrok http 5000
```

---

## Production Deployment

### Option 1: Deploy to Render (Recommended - Free Tier)

#### Backend Deployment
1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [https://render.com](https://render.com) and sign in
   - Click **"New +"** → **"Web Service"**
   - Connect your GitHub repository
   - Configure:
     - **Name**: `sqlworkshop-backend` (or your preferred name)
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Instance Type**: `Free`

3. **Add Environment Variables**
   In Render dashboard, add:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon or service key

4. **Deploy**
   - Click **"Create Web Service"**
   - Wait for deployment (2-3 minutes)
   - Copy your backend URL (e.g., `https://sqlworkshop-backend.onrender.com`)

#### Frontend Deployment (if separate)
If you want to host the frontend separately:
1. Create a new **Static Site** on Render
2. Point to your repository
3. Set **Publish Directory**: `templates`
4. Update the frontend to point to your backend URL

---

### Option 2: Deploy to Railway

#### Backend Deployment
1. **Push code to GitHub** (same as above)

2. **Deploy on Railway**
   - Go to [https://railway.app](https://railway.app) and sign in
   - Click **"New Project"** → **"Deploy from GitHub repo"**
   - Select your repository
   - Railway will auto-detect Flask

3. **Add Environment Variables**
   - Click on your service
   - Go to **"Variables"** tab
   - Add:
     - `SUPABASE_URL`
     - `SUPABASE_KEY`

4. **Configure Start Command**
   - Go to **"Settings"**
   - Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`

5. **Generate Domain**
   - Go to **"Settings"** → **"Networking"**
   - Click **"Generate Domain"**
   - Copy your URL

---

### Option 3: Deploy to Heroku

#### Backend Deployment
1. **Create Procfile**
   Create a file named `Procfile` (no extension) in project root:
   ```
   web: gunicorn app:app
   ```

2. **Push to Heroku**
   ```bash
   heroku login
   heroku create sqlworkshop-app
   git push heroku main
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set SUPABASE_URL=https://your-project.supabase.co
   heroku config:set SUPABASE_KEY=your-key
   ```

4. **Open App**
   ```bash
   heroku open
   ```

---

### Option 4: Deploy to Vercel

#### Backend Deployment
1. **Create vercel.json**
   ```json
   {
     "builds": [
       {
         "src": "app.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app.py"
       }
     ]
   }
   ```

2. **Deploy**
   ```bash
   npm i -g vercel
   vercel
   ```

3. **Set Environment Variables**
   ```bash
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_KEY
   ```

---

## Frontend Updates for Production

If your frontend is making API calls, update the API endpoint in [templates/index.html](templates/index.html):

**For local development:**
```javascript
const API_URL = 'http://localhost:5000';
```

**For production:**
```javascript
const API_URL = 'https://your-backend-url.onrender.com';
```

Or use environment detection:
```javascript
const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5000' 
  : 'https://your-backend-url.onrender.com';
```

---

## Post-Deployment Checklist

✅ Backend is running and accessible  
✅ Environment variables are set correctly  
✅ Supabase function `exec_sql` is created  
✅ Database is populated with your schema  
✅ Frontend can connect to backend  
✅ All API endpoints work (`/execute_query`, `/list_tables`, `/table_schema`)  
✅ CORS is configured if frontend is on different domain

---

## Troubleshooting

**Connection Issues:**
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase RLS (Row Level Security) policies
- Ensure `exec_sql` function exists in Supabase

**Query Errors:**
- Verify the `exec_sql` function was created correctly
- Check Supabase logs in Dashboard → Database → Logs

**Deployment Failures:**
- Check build logs on your hosting platform
- Verify all dependencies in requirements.txt
- Ensure Python version compatibility (3.8+)

---

## Security Notes

⚠️ **Important**: This app only allows SELECT queries for security. The `exec_sql` function should only be accessible via the Supabase API with proper authentication.

For production, consider:
- Using service role key instead of anon key
- Implementing rate limiting
- Adding user authentication
- Setting up RLS policies in Supabase