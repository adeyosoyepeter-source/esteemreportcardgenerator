import os
import re
from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.conf import settings


def resolve_logo_path(configured_path):
    """Find the school logo from the configured path or common workspace locations."""
    candidates = []
    if configured_path:
        candidates.append(configured_path)
    if configured_path and not os.path.isabs(configured_path):
        candidates.append(os.path.join(os.getcwd(), configured_path))

    project_root = os.path.dirname(os.path.abspath(str(settings.BASE_DIR)))
    candidates.extend([
        os.path.join(project_root, configured_path) if configured_path else None,
        os.path.join(project_root, "logo.png"),
        os.path.join(project_root, "school_logo.png"),
        os.path.join(settings.MEDIA_ROOT, configured_path) if configured_path else None,
        os.path.join(settings.MEDIA_ROOT, "logo.png"),
        os.path.join(settings.MEDIA_ROOT, "school_logo.png"),
    ])

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""


def sanitize_filename(name: str) -> str:
    """Sanitize student name for safe PDF filenames."""
    if not name:
        return "student"
    keep = []
    for char in name.strip():
        if char.isalnum() or char in (" ", "-", "_"):
            keep.append(char)
    filename = "".join(keep).strip()
    filename = filename.replace(" ", "_").replace("-", "_")
    while "__" in filename:
        filename = filename.replace("__", "_")
    return filename or "student"


def build_pdf_filename(student_data: dict, suffix: str = "ReportCard") -> str:
    """Create a safe filename for a student's PDF including term and year.

    Result example: "John_Doe_FIRST_TERM_2024-2025_ReportCard.pdf"
    """
    if not isinstance(student_data, dict):
        student_data = {}

    name = student_data.get('Student Name') or student_data.get('Name') or 'student'
    term = student_data.get('Term') or ''
    year = student_data.get('Year') or student_data.get('Session') or ''

    parts = [sanitize_filename(str(name))]
    if term:
        parts.append(sanitize_filename(str(term)))
    if year:
        parts.append(sanitize_filename(str(year)))

    filename = "_".join(parts)
    if suffix:
        filename = f"{filename}_{sanitize_filename(str(suffix))}"
    return f"{filename}.pdf"


def calculate_grade(score, max_mark=100):
    """Return grade text and percentage text based on score and max mark."""
    if score is None:
        return "F", "N/A", ""
    try:
        score_value = float(score)
        max_value = float(max_mark) if max_mark not in (None, "", 0) else 100.0
    except (ValueError, TypeError):
        return "F", "N/A", ""

    if score_value < 0:
        score_value = 0
    if max_value <= 0:
        max_value = 100.0

    percentage = round((score_value / max_value) * 100.0, 2)
    if percentage >= 70:
        grade = "A"
    elif percentage >= 60:
        grade = "B"
    elif percentage >= 50:
        grade = "C"
    elif percentage >= 45:
        grade = "D"
    elif percentage >= 40:
        grade = "E"
    else:
        grade = "F"
    return grade, f"{percentage:.2f}%", ""


def calculate_total_percentage(subjects_data):
    """Calculate total percentage from subject marks on a 100-mark scale."""
    total_marks = 0.0
    total_max_marks = 0.0

    for subject in subjects_data:
        score = subject.get("score")
        max_mark = subject.get("max_mark", 100)
        if score is None:
            continue
        try:
            score_value = float(score)
            max_value = float(max_mark) if max_mark not in (None, "", 0) else 100.0
        except (ValueError, TypeError):
            continue
        if max_value <= 0:
            max_value = 100.0
        total_marks += score_value
        total_max_marks += max_value

    if total_max_marks == 0:
        return 0.0
    return round((total_marks / total_max_marks) * 100.0, 2)


def calculate_gpa(subjects_data):
    """Backward-compatible wrapper for total percentage calculation."""
    return calculate_total_percentage(subjects_data)


def parse_sheet_metadata(title_value, sheet_name):
    """Extract class, term, and session from the sheet title row."""
    title_text = str(title_value or "").strip()
    class_name = sheet_name
    term = ""
    session = ""

    if title_text:
        term_match = re.search(r"(?i)\b(first|second|third)\s+term\b", title_text)
        if term_match:
            term = f"{term_match.group(1).upper()} TERM"

        class_match = re.search(r"(?i)(?P<class>.+?)\s+(first|second|third)\s+term\b", title_text)
        if class_match and class_match.group("class").strip():
            class_name = class_match.group("class").strip()

        session_match = re.search(r"(?i)\b(?P<session>\d{4}/\d{4})\b", title_text)
        if session_match:
            session = session_match.group("session")

    return class_name or sheet_name, term, session


def apply_report_metadata(student_data, term=None, year=None):
    """Apply the selected term and academic year to a student record."""
    updated_data = dict(student_data or {})
    if term:
        updated_data["Term"] = str(term).strip()
    if year:
        updated_data["Session"] = str(year).strip()
        updated_data["Year"] = str(year).strip()
    elif updated_data.get("Session"):
        updated_data["Year"] = updated_data["Session"]
    return updated_data


def read_broadsheet(file_path):
    """Read Excel broadsheet sheets and return student rows and detected subjects."""
    default_credit_hour = settings.SCHOOL_CONFIG['default_credit_hour']
    subject_credit_hours = settings.SCHOOL_CONFIG['subject_credit_hours']

    students = []
    excel_file = pd.ExcelFile(file_path, engine="openpyxl")

    for sheet_name in excel_file.sheet_names:
        try:
            sheet_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl")
        except Exception:
            continue

        if sheet_df.shape[0] < 3:
            continue

        header_row_index = None
        header_values = []
        for row_index in range(sheet_df.shape[0]):
            row_values = sheet_df.iloc[row_index].tolist()
            normalized_row = []
            for value in row_values:
                if pd.isna(value):
                    normalized_row.append("")
                else:
                    normalized_row.append(str(value).strip())

            if any(value.lower() == "names of student" for value in normalized_row):
                header_row_index = row_index
                header_values = normalized_row
                break

        if header_row_index is None:
            continue

        normalized_headers = [value.lower() for value in header_values]

        student_name_index = None
        admission_index = None
        home_address_index = None
        telephone_index = None
        total_index = None
        average_index = None
        for index, header in enumerate(normalized_headers):
            if header == "names of student":
                student_name_index = index
            elif header == "admission no":
                admission_index = index
            elif header == "home address":
                home_address_index = index
            elif header == "telephone":
                telephone_index = index
            elif header == "total":
                total_index = index
            elif header == "average":
                average_index = index

        if student_name_index is None:
            student_name_index = 2 if len(header_values) > 2 else None

        subject_indices = []
        if telephone_index is not None:
            subject_end = total_index if total_index is not None else average_index
            if subject_end is not None and subject_end > telephone_index:
                subject_indices = list(range(telephone_index + 1, subject_end))
        elif student_name_index is not None and total_index is not None and total_index > student_name_index:
            subject_indices = list(range(student_name_index + 1, total_index))

        title_value = sheet_df.iloc[header_row_index - 1, 0] if header_row_index > 0 and sheet_df.shape[1] > 0 else ""
        class_name, term, session = parse_sheet_metadata(title_value, sheet_name)

        for row_index in range(header_row_index + 1, sheet_df.shape[0]):
            try:
                row = sheet_df.iloc[row_index]
                if student_name_index is not None and student_name_index < len(row):
                    student_name = str(row.iloc[student_name_index]).strip() if not pd.isna(row.iloc[student_name_index]) else ""
                else:
                    student_name = ""

                if not student_name:
                    continue

                subjects = []
                scored_values = []
                for subject_index in subject_indices:
                    if subject_index >= len(row):
                        continue

                    raw_value = row.iloc[subject_index]
                    if pd.isna(raw_value):
                        score_value = None
                    else:
                        try:
                            score_value = float(raw_value)
                        except (TypeError, ValueError):
                            score_value = None

                    if score_value is not None and score_value != 0:
                        scored_values.append(score_value)

                    subject_name = header_values[subject_index] if subject_index < len(header_values) else f"Column {subject_index + 1}"
                    subjects.append({
                        "name": subject_name,
                        "score": score_value,
                        "credit_hour": subject_credit_hours.get(subject_name, default_credit_hour),
                        "max_mark": 100,
                    })

                if not scored_values:
                    continue

                total_score = sum(scored_values)
                average_score = total_score / len(scored_values)
                student_data = {
                    "Student Name": student_name,
                    "Class": class_name,
                    "Term": term,
                    "Session": session,
                    "Roll No": "",
                    "Section": "",
                    "Attendance": "",
                    "Remarks": "",
                    "Admission No": "",
                    "Home Address": "",
                    "Telephone": "",
                    "Total": total_score,
                    "Average": average_score,
                }

                if admission_index is not None and admission_index < len(row):
                    student_data["Admission No"] = str(row.iloc[admission_index]).strip() if not pd.isna(row.iloc[admission_index]) else ""
                if home_address_index is not None and home_address_index < len(row):
                    student_data["Home Address"] = str(row.iloc[home_address_index]).strip() if not pd.isna(row.iloc[home_address_index]) else ""
                if telephone_index is not None and telephone_index < len(row):
                    student_data["Telephone"] = str(row.iloc[telephone_index]).strip() if not pd.isna(row.iloc[telephone_index]) else ""

                students.append({"student_data": student_data, "subjects": subjects})
            except Exception:
                continue

    return students


def generate_pdf_bytes(student_data, subjects):
    """Generate a report card PDF and return as bytes."""
    school_config = settings.SCHOOL_CONFIG
    school_name = school_config['name']
    school_address = school_config['address']
    year = school_config['year']
    logo_path = resolve_logo_path(school_config['logo_path'])
    issue_date = datetime.now().strftime("%d %B %Y")
    default_credit_hour = school_config['default_credit_hour']
    
    # Create PDF in memory
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    border_color = colors.HexColor("#003366")
    c.setStrokeColor(border_color)
    c.setLineWidth(3)
    c.rect(20, 20, width - 40, height - 40, stroke=1, fill=0)
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56, stroke=1, fill=0)

    # School logo and header
    logo_box_size = 70
    if logo_path:
        try:
            logo = ImageReader(logo_path)
            c.drawImage(logo, 38, height - 38 - logo_box_size, width=logo_box_size - 6, height=logo_box_size - 6, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    else:
        c.setStrokeColor(border_color)
        c.rect(35, height - 35 - logo_box_size, logo_box_size, logo_box_size, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 65, school_name)

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 85, school_address)

    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 14)
    report_header = " | ".join(filter(None, [student_data.get("Class", ""), student_data.get("Term", ""), student_data.get("Session", "") or student_data.get("Year", "")]))
    if report_header:
        c.drawCentredString(width / 2, height - 105, report_header.upper())
    else:
        c.drawCentredString(width / 2, height - 105, f"FINAL TERMINAL EXAMINATION {year}")

    banner_height = 24
    banner_y = height - 130
    c.setFillColor(colors.HexColor("#F2C74C"))
    c.rect(40, banner_y, width - 80, banner_height, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#3E2723"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, banner_y + 7, "MARKSHEET")

    photo_box_size = 70
    c.setStrokeColor(border_color)
    c.rect(width - 35 - photo_box_size, height - 35 - photo_box_size, photo_box_size, photo_box_size, stroke=1, fill=0)

    # Student info section
    info_y = height - 165
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, info_y, "Student Name:")
    c.line(120, info_y - 2, width - 40, info_y - 2)

    info_y -= 22
    c.drawString(40, info_y, "Class:")
    c.line(75, info_y - 2, 135, info_y - 2)
    c.drawString(150, info_y, "Roll No:")
    c.line(205, info_y - 2, 270, info_y - 2)
    c.drawString(295, info_y, "Section:")
    c.line(345, info_y - 2, 410, info_y - 2)

    c.setFont("Helvetica", 11)
    c.drawString(125, height - 165, student_data.get("Student Name", ""))
    c.drawString(80, height - 187, student_data.get("Class", ""))
    c.drawString(210, height - 187, student_data.get("Roll No", ""))
    c.drawString(350, height - 187, student_data.get("Section", ""))

    # Subjects table
    table_top = height - 220
    table_left = 32
    row_height = 22
    headers = ["S.NO", "SUBJECT", "MAX MARK", "MARK OBTAINED", "PERCENTAGE", "GRADE"]
    table_width = width - 64
    col_widths = [34, 160, 54, 136, 70, 73]

    c.setFillColor(colors.whitesmoke)
    c.rect(table_left, table_top - row_height, table_width, row_height, stroke=0, fill=1)
    c.setStrokeColor(border_color)
    c.setLineWidth(0.8)
    c.line(table_left, table_top - row_height, table_left + table_width, table_top - row_height)

    x = table_left
    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 10)
    for index, header in enumerate(headers):
        c.drawCentredString(x + col_widths[index] / 2, table_top - 16, header)
        x += col_widths[index]
        c.line(x, table_top, x, table_top - (len(subjects) + 1) * row_height)

    y = table_top - row_height
    c.line(table_left, table_top, table_left + table_width, table_top)
    c.line(table_left, y - len(subjects) * row_height, table_left, y)
    c.line(table_left + table_width, y - len(subjects) * row_height, table_left + table_width, y)

    col_positions = []
    current_x = table_left
    for width in col_widths:
        col_positions.append(current_x)
        current_x += width

    c.setFont("Helvetica", 10)
    for idx, subject in enumerate(subjects, start=1):
        row_y = y - (idx - 1) * row_height
        c.setFillColor(colors.black)
        grade, percentage_text, _ = calculate_grade(subject.get("score"), subject.get("max_mark", 100))
        subject_name = subject.get("name", "")
        score_value = subject.get("score")
        max_mark_value = subject.get("max_mark", 100)
        if score_value is None:
            display_score = "N/A"
        else:
            try:
                display_score = f"{float(score_value):.0f}"
            except (TypeError, ValueError):
                display_score = str(score_value)
        c.drawString(col_positions[0] + 4, row_y - 16, str(idx))
        c.drawString(col_positions[1] + 4, row_y - 16, subject_name)
        c.drawCentredString(col_positions[2] + col_widths[2] / 2, row_y - 16, f"{float(max_mark_value):.0f}")
        c.drawCentredString(col_positions[3] + col_widths[3] / 2, row_y - 16, display_score)
        c.drawCentredString(col_positions[4] + col_widths[4] / 2, row_y - 16, percentage_text)
        c.drawCentredString(col_positions[5] + col_widths[5] / 2, row_y - 16, grade)
        c.line(table_left, row_y - row_height, table_left + table_width, row_y - row_height)

    # Attendance and total percentage box
    box_top = y - len(subjects) * row_height - 20
    box_height = 60
    half_width = (table_width - 8) / 2
    c.setStrokeColor(border_color)
    c.rect(table_left, box_top - box_height, table_width, box_height, stroke=1, fill=0)
    c.line(table_left + half_width + 4, box_top, table_left + half_width + 4, box_top - box_height)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(table_left + 6, box_top - 20, "ATTENDANCE")
    c.setFont("Helvetica", 11)
    c.drawString(table_left + 6, box_top - 38, student_data.get("Attendance", ""))

    total_percentage = calculate_total_percentage(subjects)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(table_left + half_width + 12, box_top - 20, "TOTAL PERCENTAGE")
    c.setFont("Helvetica", 11)
    c.drawString(table_left + half_width + 12, box_top - 38, f"{total_percentage:.2f}%")

    # Footer
    footer_y = box_top - box_height - 30
    c.setFont("Helvetica", 9)
    c.drawString(table_left, footer_y + 10, f"ISSUE ON {issue_date}")

    sign_x = table_left
    sign_width = (table_width - 40) / 3
    for index, label in enumerate(["Teacher Sign", "Parents Sign", "Principal Sign"]):
        x = table_left + index * (sign_width + 20)
        c.line(x, footer_y - 10, x + sign_width, footer_y - 10)
        c.drawCentredString(x + sign_width / 2, footer_y - 24, label)

    legend_top = footer_y - 50
    legend_left = table_left
    legend_right = table_left + table_width / 2 + 10
    c.setFont("Helvetica-Oblique", 8)
    legend_lines = [
        ("90% and above: A+ Grade", "80% and above: A Grade"),
        ("70% and above: B+ Grade", "60% and above: B Grade"),
        ("50% and above: C+ Grade", "40% and above: C Grade"),
        ("35% and above: D Grade", "35% and below: Not Graded"),
    ]
    for idx, (left_text, right_text) in enumerate(legend_lines):
        y = legend_top - idx * 12
        c.drawString(legend_left, y, left_text)
        c.drawString(legend_right, y, right_text)

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer
