# 🍃 Leaf Analyzer - Setup Guide (macOS + MAMP/XAMPP)

## Project Structure
```
leaf_analyzer/
├── index.php                  ← Root redirect to auth/login.php
├── leaf_analyzer.sql          ← Import this into MySQL
├── README.md
├── config/
│   └── db.php                 ← DB credentials here
├── auth/
│   ├── login.php
│   ├── signup.php
│   └── logout.php
├── dashboard/
│   ├── index.php              ← Main dashboard
│   └── analyze.php            ← AJAX endpoint
├── assets/
│   ├── css/style.css
│   └── js/dashboard.js
├── python/
│   ├── analyze_leaf.py        ← ML + color analysis
│   ├── train_model.py         ← Train your own model
│   └── leaf_disease_model.keras  ← (optional, add your trained model here)
└── uploads/                   ← Auto-created, writable by PHP
```

---

## Step 1 — Web Server (MAMP recommended for macOS)

1. Download & install **MAMP** from https://www.mamp.info
2. Set Document Root to the **parent folder** of `leaf_analyzer/`
   - MAMP → Preferences → Web Server → Document Root → select folder
3. Start servers (Apache + MySQL)
4. Visit: http://localhost:8888/leaf_analyzer/

---

## Step 2 — Database

1. Open **phpMyAdmin**: http://localhost:8888/phpMyAdmin/
2. Click **Import** → choose `leaf_analyzer.sql` → Go
3. Database `leaf_analyzer` with tables `users` and `analysis_history` will be created

---

## Step 3 — Python Dependencies

```bash
# Install Python 3 if not already (via Homebrew)
brew install python

# Install required libraries
pip3 install pillow

# Optional: for ML model support
pip3 install tensorflow numpy
```

---

## Step 4 — Verify Python path

The app auto-detects Python 3 at these macOS paths (in order):
1. `/opt/homebrew/bin/python3` (Apple Silicon Mac)
2. `/usr/local/bin/python3` (Intel Mac / Homebrew)
3. `/usr/bin/python3` (System)

Confirm yours: `which python3` in Terminal

---

## Step 5 — (Optional) Train your own model

1. Download the PlantVillage Potato dataset
2. Place it at `python/dataset/Potato/`
3. Run: `cd python && python3 train_model.py`
4. This saves `leaf_disease_model.keras` into `python/`

Without the model, the app falls back to **color analysis** automatically.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| White page / DB error | Import the SQL, check MAMP is running |
| "Python not found" | `brew install python` then restart MAMP |
| "Script not found" | Make sure `analyze_leaf.py` is in `python/` folder |
| Images not showing | `chmod 755 uploads/` |
| JSON parse error | Check PHP error log in MAMP |
