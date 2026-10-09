import json
import tempfile
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .forms import BroadsheetUploadForm
from .utils import read_broadsheet, generate_pdf_bytes, sanitize_filename, apply_report_metadata, build_pdf_filename


def _get_request_session(request):
    """Return a usable session-like object for the request."""
    session = getattr(request, 'session', None)
    if session is None:
        session = {}
        setattr(request, 'session', session)
    return session


def index(request):
    """Home page with upload form."""
    form = BroadsheetUploadForm()
    return render(request, 'index.html', {'form': form})


@require_http_methods(["POST"])
@csrf_exempt
def upload_broadsheet(request):
    """Handle Excel broadsheet upload and process data."""
    form = BroadsheetUploadForm(request.POST, request.FILES)
    if request.FILES and 'file' in request.FILES:
        if not form.is_valid():
            form = BroadsheetUploadForm()

    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file uploaded'}, status=400)

    file = request.FILES['file']
    term = request.POST.get('term') or (form.cleaned_data.get('term') if form.is_bound else None) or 'First Term'
    year = request.POST.get('year') or (form.cleaned_data.get('year') if form.is_bound else None) or ''

    if not file.name.endswith('.xlsx'):
        return JsonResponse({'success': False, 'error': 'Please upload an .xlsx file'}, status=400)

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        # Read broadsheet
        students = read_broadsheet(tmp_path)
        
        if not students:
            return JsonResponse({
                'success': False,
                'error': 'No student records found in the broadsheet'
            }, status=400)

        session = _get_request_session(request)
        session['report_metadata'] = {
            'term': term,
            'year': year,
        }

        # Store student data in session for download
        session['students_data'] = [
            {
                'student_data': apply_report_metadata(record['student_data'], term=term, year=year),
                'subjects': record['subjects']
            }
            for record in students
        ]
        if hasattr(session, 'modified'):
            session.modified = True

        return JsonResponse({
            'success': True,
            'message': f'Loaded {len(students)} students',
            'student_count': len(students),
            'report_metadata': {'term': term, 'year': year},
            'students': [
                {
                    'name': record['student_data'].get('Student Name', ''),
                    'class': record['student_data'].get('Class', ''),
                    'roll_no': record['student_data'].get('Roll No', ''),
                    'subjects_count': len(record.get('subjects', []))
                }
                for record in students[:10]  # Show first 10
            ]
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error processing file: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def generate_pdfs(request):
    """Generate all report card PDFs as a ZIP file."""
    try:
        session = _get_request_session(request)
        students_data = session.get('students_data', [])
        
        if not students_data:
            return JsonResponse({
                'success': False,
                'error': 'No student data found. Please upload a file first.'
            }, status=400)

        import zipfile
        import io

        report_metadata = session.get('report_metadata', {})
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for record in students_data:
                student_data = apply_report_metadata(
                    record['student_data'],
                    term=report_metadata.get('term'),
                    year=report_metadata.get('year')
                )
                subjects = record['subjects']
                
                # Generate PDF
                pdf_bytes = generate_pdf_bytes(student_data, subjects)
                
                # Add to ZIP using student name + term + year
                filename = build_pdf_filename(student_data)
                zip_file.writestr(filename, pdf_bytes.getvalue())

        zip_buffer.seek(0)
        
        response = FileResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="report_cards.zip"'
        
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating PDFs: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def generate_single_pdf(request):
    """Generate a single report card PDF."""
    try:
        data = json.loads(request.body)
        student_index = data.get('student_index', 0)
        
        session = _get_request_session(request)
        students_data = session.get('students_data', [])
        
        if student_index >= len(students_data):
            return JsonResponse({
                'success': False,
                'error': 'Invalid student index'
            }, status=400)
        
        record = students_data[student_index]
        report_metadata = session.get('report_metadata', {})
        student_data = apply_report_metadata(
            record['student_data'],
            term=report_metadata.get('term'),
            year=report_metadata.get('year')
        )
        subjects = record['subjects']
        
        # Generate PDF
        pdf_bytes = generate_pdf_bytes(student_data, subjects)
        
        response = FileResponse(pdf_bytes, content_type='application/pdf')
        filename = build_pdf_filename(student_data)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating PDF: {str(e)}'
        }, status=500)
