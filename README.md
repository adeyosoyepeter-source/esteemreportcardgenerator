# Report Card Generator - Web App

The desktop Tkinter application has been converted to a modern Django web application.

## 📦 Project Structure

```
result_generator/
├── django_app/              # Django web application
│   ├── manage.py
│   ├── requirements.txt
│   ├── README.md           # Detailed setup instructions
│   ├── config/             # Django configuration
│   ├── report_card/        # Main Django app
│   └── media/              # Uploads and files
├── run.sh                  # Quick start script
├── report_card_generator.py # Original desktop app
└── report_card_generator.spec
```

## 🚀 Quick Start

### Option 1: Using the Quick Start Script
```bash
bash run.sh
```

### Option 2: Manual Setup
```bash
cd django_app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open your browser to: **http://127.0.0.1:8000**

## ✨ Key Features

- 🌐 **Web-based Interface** - Access from any browser
- 📱 **Responsive Design** - Works on desktop and mobile
- 📤 **Easy File Upload** - Drag and drop Excel files
- 📄 **Batch Processing** - Generate all report cards at once
- ⬇️ **ZIP Downloads** - Download multiple PDFs as ZIP
- 🎨 **Professional PDFs** - Beautiful, customizable report cards
- 🧮 **Auto Grading** - Automatic GPA and grade calculation

## 📚 Documentation

See [django_app/README.md](django_app/README.md) for:
- Detailed installation instructions
- Excel file format requirements
- Customization options
- Configuration guide
- Troubleshooting tips

## 🔧 System Requirements

- Python 3.8+
- pip or conda
- No additional system dependencies

## 📝 What Changed

| Feature | Desktop App | Web App |
|---------|------------|--------|
| Interface | Tkinter GUI | Web Browser |
| File Management | File dialogs | Drag & drop |
| Deployment | Standalone exe | Browser-based |
| Customization | Code editing | Settings & config |
| Access | Local only | Network accessible |

## 🛠️ Customization

Edit `django_app/config/settings.py` to customize:
- School name and address
- Grade thresholds
- Subject credit hours
- School logo

## 📄 Example Excel Format

Your Excel file needs these columns:
- Student Name
- Class
- Roll No
- Section
- Attendance
- Remarks
- Subject scores (numeric columns)

## 🎯 Next Steps

1. Copy your Excel broadsheets to the `django_app/media/broadsheets/` folder
2. Start the development server
3. Open http://127.0.0.1:8000 in your browser
4. Upload your file and generate report cards

## ☁️ Deploy to Render

1. Add your app to Render as a Python web service
2. Set the build command:
   - `pip install -r requirements.txt`
3. Set the start command:
   - `gunicorn config.wsgi --chdir django_app --bind 0.0.0.0:$PORT`
4. Add environment variables:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-service-name.onrender.com`
   - `DATABASE_URL` (optional)

## 📧 Support

For detailed help, see the README.md in the django_app folder or refer to:
- Django Documentation: https://docs.djangoproject.com
- ReportLab Documentation: https://www.reportlab.com/docs/reportlab-userguide.pdf

---

**Version**: 2.0 (Web App)
**Last Updated**: 2026-06-30
