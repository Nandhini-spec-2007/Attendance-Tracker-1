# Attendance Tracker
Frontend: HTML/CSS/JS (static/) | Backend: Python Flask (app.py) | Database: MySQL

## Setup
1. Install Python 3.9+ and MySQL, and make sure MySQL is running.
2. `pip install -r requirements.txt`
3. Set DB details if not default (root, empty password):
   - Windows: `set DB_PASSWORD=yourpassword`
   - Mac/Linux: `export DB_PASSWORD=yourpassword`
4. `python setup_db.py`  (creates tables + demo data)
5. `python app.py` and open http://localhost:5000

## Demo logins
| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Faculty | faculty | faculty123 |
| Student | student | student123 |

## Notes
- Low attendance threshold: change `THRESHOLD` in app.py (default 75).
- Percentage = Present days / total working days x 100 (a working day is any date with attendance recorded). Leave days count as not present.
- Biometric: /api/biometric receives a fingerprint ID. Connect a real scanner by posting its matched ID to this endpoint; the page lets you type an ID to test.
- Change SECRET_KEY and the demo passwords before real use.
