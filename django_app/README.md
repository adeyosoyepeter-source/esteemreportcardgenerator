# Report Card Generator - Django Web App

A modern web application for generating professional PDF report cards from Excel broadsheets. Built with Django and featuring an intuitive web interface.

## Features

- 📁 Upload Excel broadsheets (.xlsx files)
- 👥 Automatic student data parsing
- 📄 Generate professional PDF report cards
- ⬇️ Download individual or batch report cards as ZIP
- 🎨 Responsive web interface
- 📊 GPA calculation and grade assignment
- 🏫 Customizable school information

## System Requirements

- Python 3.8+
- pip (Python package manager)

## Installation & Setup

### 1. Navigate to the Django app directory

```bash
cd django_app
```

### 2. Create a virtual environment (recommended)

```bash
# On Linux/Mac
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (optional, for admin access)

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`

## Usage

### 1. Upload Broadsheet
- Click the upload area or drag and drop an Excel file (.xlsx)
- The app will parse the file and extract student data

### 2. Preview Students
- Review the loaded students and their subject counts
- The app displays the first 10 students as a preview

### 3. Generate Report Cards
- **Download All**: Generate and download all report cards as a ZIP file
- **Individual Downloads**: Download specific student report cards one at a time

## Excel File Format

Your Excel file should contain the following columns:

| Student Name | Class | Roll No | Section | Attendance | Remarks | Subject1 | Subject2 | ... |
|--------------|-------|---------|---------|------------|---------|----------|----------|-----|
| John Doe     | 10-A  | 001     | A       | 95%        | Good    | 85       | 92       | ... |

**Required columns:**
- Student Name
- Class
- Roll No
- Section
- Attendance
- Remarks

**Optional columns:**
- Any additional columns with numeric values will be treated as subjects

## Customization

### School Configuration

Edit `config/settings.py` to customize:

```python
SCHOOL_CONFIG = {
    'name': 'Your School Name',
    'address': 'School Address',
    'year': '2026',
    'logo_path': 'school_logo.png',
    'subject_credit_hours': {
        'Mathematics': 3.00,
        'English': 3.00,
        # ... add your subjects
    },
    'grade_thresholds': [
        (90, 'A+', 4.0, 'Excellent'),
        # ... customize grades
    ],
}
```

### School Logo

Place your school logo as `school_logo.png` in the `media/` folder.

## Grade Thresholds

Default grade scale (customizable in settings):
- 90%+ : A+ (4.0) - Excellent
- 80%+ : A (3.7) - Very Good
- 70%+ : B+ (3.3) - Good
- 60%+ : B (3.0) - Satisfactory
- 50%+ : C+ (2.7) - Fair
- 40%+ : C (2.3) - Needs Improvement
- 35%+ : D (2.0) - Passing
- Below 35% : F (0.0) - Not Graded

## File Structure

```
django_app/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # Database (auto-created)
├── media/                   # User uploads and generated files
├── config/                  # Project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── report_card/             # Main app
    ├── templates/
    │   └── index.html       # Main page
    ├── static/
    │   ├── css/
    │   │   └── style.css
    │   └── js/
    │       └── app.js
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── forms.py
    ├── utils.py             # PDF generation logic
    └── admin.py
```

## Troubleshooting

### Port Already in Use
If port 8000 is already in use:
```bash
python manage.py runserver 8080
```

### Permission Denied on Media Files
Ensure the `media/` directory has write permissions:
```bash
chmod 755 media/
```

### File Upload Issues
- Ensure file is in .xlsx format (not .xls)
- Check file size doesn't exceed 10MB
- Verify all required columns are present

## API Endpoints

- `POST /api/upload/` - Upload and process Excel file
- `POST /api/generate-pdfs/` - Generate all report cards as ZIP
- `POST /api/generate-single/` - Generate individual report card

## Production Deployment

For production deployment:

1. Set `DEBUG = False` in `config/settings.py`
2. Update `SECRET_KEY` with a secure value
3. Set `ALLOWED_HOSTS` to your domain
4. Use a production WSGI server (Gunicorn, uWSGI)
5. Set up a proper database (PostgreSQL recommended)
6. Configure static and media file serving

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please check the troubleshooting section or review the Django and ReportLab documentation.
