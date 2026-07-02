import os
import re
import threading
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:  # pragma: no cover - optional dependency in headless environments
    tk = None
    filedialog = None
    messagebox = None

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - optional dependency in headless environments
    ctk = None

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# ---------- EDITABLE SETTINGS ----------
SCHOOL_NAME = "ESTEEM STANDARD CHOICE ACADEMY"
SCHOOL_ADDRESS = "21, Egbado Street, Ope-ilu, Agbado, Ogun State"
YEAR = "2026"
LOGO_PATH = "logo.png"
ISSUE_DATE = datetime.now().strftime("%d %B %Y")
MAX_SCORE = 100

SUBJECT_CREDIT_HOURS = {
    "Mathematics": 3.00,
    "English": 3.00,
    "Science": 3.00,
    "History": 2.50,
    "Geography": 2.50,
}

GRADE_THRESHOLDS = [
    (70, "A", 4.0, "Excellent"),
    (60, "B", 3.0, "Good"),
    (50, "C", 2.0, "Fair"),
    (45, "D", 1.0, "Needs Improvement"),
    (40, "E", 0.5, "Poor"),
    (0, "F", 0.0, "Fail"),
]
DEFAULT_CREDIT_HOUR = 3.00

# ---------- HELPER FUNCTIONS ----------

def resolve_logo_path():
    """Find the school logo from the configured path or common workspace locations."""
    candidates = []
    if LOGO_PATH:
        candidates.append(LOGO_PATH)
    if LOGO_PATH and not os.path.isabs(LOGO_PATH):
        candidates.append(os.path.join(os.getcwd(), LOGO_PATH))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        os.path.join(script_dir, LOGO_PATH) if LOGO_PATH else None,
        os.path.join(script_dir, "logo.png"),
        os.path.join(script_dir, "school_logo.png"),
        os.path.join(os.getcwd(), "logo.png"),
        os.path.join(os.getcwd(), "school_logo.png"),
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


def sanitize_path_component(name: str) -> str:
    """Create a filesystem-safe path component from a sheet or class name."""
    if not name:
        return "unknown"
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name).strip())
    cleaned = cleaned.replace(" ", "_")
    return cleaned or "unknown"


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


def read_broadsheet(file_path, log_callback=None):
    """Read Excel broadsheet sheets and return student rows and detected subjects."""
    students = []
    excel_file = pd.ExcelFile(file_path, engine="openpyxl")

    for sheet_name in excel_file.sheet_names:
        try:
            sheet_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl")
        except Exception as exc:
            if log_callback:
                log_callback(f"Skipping sheet '{sheet_name}': {exc}")
            continue

        if log_callback:
            log_callback(f"Processing sheet: {sheet_name}")

        try:
            if sheet_df.shape[0] < 3:
                if log_callback:
                    log_callback(f"Skipping sheet '{sheet_name}': missing header row")
                continue

            header_row = sheet_df.iloc[2].tolist() if sheet_df.shape[0] > 2 else []
            header_values = []
            for value in header_row:
                if pd.isna(value):
                    header_values.append("")
                else:
                    header_values.append(str(value).strip())

            normalized_headers = [value.lower() for value in header_values]
            if "names of student" not in normalized_headers:
                if log_callback:
                    log_callback(f"Skipping sheet '{sheet_name}': invalid header row (missing 'NAMES OF STUDENT')")
                continue

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

            title_value = sheet_df.iloc[1, 0] if sheet_df.shape[0] > 1 and sheet_df.shape[1] > 0 else ""
            class_name, term, session = parse_sheet_metadata(title_value, sheet_name)

            for row_index in range(3, sheet_df.shape[0]):
                try:
                    row = sheet_df.iloc[row_index]
                    if student_name_index is not None and student_name_index < len(row):
                        student_name = str(row.iloc[student_name_index]).strip() if not pd.isna(row.iloc[student_name_index]) else ""
                    else:
                        student_name = ""

                    if not student_name:
                        if log_callback:
                            log_callback(f"Skipping row {row_index + 1} in sheet '{sheet_name}': blank student name")
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

                        subjects.append({
                            "name": header_values[subject_index] if subject_index < len(header_values) else f"Column {subject_index + 1}",
                            "score": score_value,
                            "credit_hour": SUBJECT_CREDIT_HOURS.get(header_values[subject_index], DEFAULT_CREDIT_HOUR),
                            "max_mark": MAX_SCORE,
                        })

                    if not scored_values:
                        if log_callback:
                            log_callback(f"Skipping student '{student_name}' in sheet '{sheet_name}': no scores")
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
                except Exception as exc:
                    if log_callback:
                        log_callback(f"Skipping row {row_index + 1} in sheet '{sheet_name}': {exc}")
        except Exception as exc:
            if log_callback:
                log_callback(f"Skipping sheet '{sheet_name}': {exc}")

    return students


def generate_pdf(student_data, subjects, output_path):
    """Generate a report card PDF for one student."""
    os.makedirs(output_path, exist_ok=True)
    student_name = sanitize_filename(student_data.get("Student Name", "student"))
    class_name = sanitize_filename(student_data.get("Class", "class"))
    file_name = f"{student_name}_{class_name}" if class_name else student_name
    output_file = os.path.join(output_path, f"{file_name}_ReportCard.pdf")
    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4

    border_color = colors.HexColor("#003366")
    c.setStrokeColor(border_color)
    c.setLineWidth(3)
    c.rect(20, 20, width - 40, height - 40, stroke=1, fill=0)
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56, stroke=1, fill=0)

    # School logo and header
    logo_box_size = 70
    resolved_logo_path = resolve_logo_path()
    if resolved_logo_path:
        try:
            logo = ImageReader(resolved_logo_path)
            c.drawImage(logo, 38, height - 38 - logo_box_size, width=logo_box_size - 6, height=logo_box_size - 6, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    else:
        c.setStrokeColor(border_color)
        c.rect(35, height - 35 - logo_box_size, logo_box_size, logo_box_size, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 65, SCHOOL_NAME)

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 85, SCHOOL_ADDRESS)

    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 14)
    report_header = " | ".join(filter(None, [student_data.get("Class", ""), student_data.get("Term", ""), student_data.get("Session", "")]))
    if report_header:
        c.drawCentredString(width / 2, height - 105, report_header.upper())
    else:
        c.drawCentredString(width / 2, height - 105, f"FINAL TERMINAL EXAMINATION {YEAR}")

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
    c.drawString(table_left, footer_y + 10, f"ISSUE ON {ISSUE_DATE}")

    sign_x = table_left
    sign_width = (table_width - 40) / 3
    for index, label in enumerate(["Teacher Sign", "Parents Sign", "Principal Sign"]):
        x = table_left + index * (sign_width + 20)
        c.line(x, footer_y - 10, x + sign_width, footer_y - 10)
        c.drawCentredString(x + sign_width / 2, footer_y - 24, label)

    c.save()
    return output_file


class ReportCardGeneratorApp:
    """Desktop GUI application for generating report cards."""

    def __init__(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.title("Esteem Standard Choice Academy - Report Card Generator")
        self.root.geometry("760x520")
        self.root.resizable(False, False)

        self.broadsheet_path = ""
        self.output_folder = ""
        self.total_students = 0
        self.generated_count = 0

        self.create_widgets()

    def create_widgets(self):
        self.title_label = ctk.CTkLabel(self.root, text="Report Card Generator", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        frame = ctk.CTkFrame(self.root)
        frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.select_broadsheet_button = ctk.CTkButton(frame, text="Select Broadsheet", command=self.select_broadsheet)
        self.select_broadsheet_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.selected_file_label = ctk.CTkLabel(frame, text="No broadsheet selected", anchor="w")
        self.selected_file_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.select_output_button = ctk.CTkButton(frame, text="Select Output Folder", command=self.select_output_folder)
        self.select_output_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.output_folder_label = ctk.CTkLabel(frame, text="No output folder selected", anchor="w")
        self.output_folder_label.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.generate_button = ctk.CTkButton(frame, text="Generate Report Cards", command=self.start_generation)
        self.generate_button.grid(row=2, column=0, columnspan=2, padx=10, pady=15, sticky="ew")

        self.progress = ctk.CTkProgressBar(frame)
        self.progress.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="ew")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(frame, text="Ready", anchor="w")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

        self.open_folder_button = ctk.CTkButton(frame, text="Open Output Folder", command=self.open_output_folder, state="disabled")
        self.open_folder_button.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.log_text = ctk.CTkTextbox(frame, height=140, wrap="word")
        self.log_text.grid(row=6, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")
        self.log_text.insert("end", "Logs will appear here.\n")
        self.log_text.configure(state="disabled")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(6, weight=1)

    def append_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def log_message(self, message):
        self.root.after(0, lambda: self.append_log(message))

    def select_broadsheet(self):
        file_path = filedialog.askopenfilename(title="Select Excel Broadsheet", filetypes=[("Excel Files", "*.xlsx")])
        if file_path:
            self.broadsheet_path = file_path
            self.selected_file_label.configure(text=os.path.basename(file_path))

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_label.configure(text=folder)

    def start_generation(self):
        if not self.broadsheet_path:
            messagebox.showwarning("Missing Input", "Please select an Excel broadsheet first.")
            return
        if not self.output_folder:
            messagebox.showwarning("Missing Output Folder", "Please select an output folder first.")
            return

        self.generate_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")
        self.progress.set(0)
        self.status_label.configure(text="Reading broadsheet...")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "Starting generation...\n")
        self.log_text.configure(state="disabled")

        worker = threading.Thread(target=self.run_generation)
        worker.daemon = True
        worker.start()

    def run_generation(self):
        self.log_message(f"Reading broadsheet: {self.broadsheet_path}")
        try:
            students = read_broadsheet(self.broadsheet_path, log_callback=self.log_message)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Read Error", f"Failed to read broadsheet:\n{exc}"))
            self.root.after(0, lambda: self.generate_button.configure(state="normal"))
            self.root.after(0, lambda: self.status_label.configure(text="Ready"))
            return

        self.total_students = len(students)
        self.generated_count = 0
        if self.total_students == 0:
            self.log_message("No eligible student records were found in the selected broadsheet.")
            self.root.after(0, lambda: messagebox.showinfo("No Students", "No student records were found in the selected broadsheet."))
            self.root.after(0, lambda: self.generate_button.configure(state="normal"))
            self.root.after(0, lambda: self.status_label.configure(text="Ready"))
            return

        failures = []
        for index, record in enumerate(students, start=1):
            student_data = record.get("student_data", {})
            subjects = record.get("subjects", [])
            class_name = student_data.get("Class", "Unknown")
            class_folder = os.path.join(self.output_folder, sanitize_path_component(class_name))
            student_name = student_data.get("Student Name", f"Row {index}")
            try:
                generate_pdf(student_data, subjects, class_folder)
                self.generated_count += 1
                self.log_message(f"Generated PDF for {student_name} in {class_name}")
            except Exception as exc:
                failures.append((student_name, str(exc)))
                self.log_message(f"Failed to generate PDF for {student_name} in {class_name}: {exc}")

            progress_value = self.generated_count / self.total_students if self.total_students else 0
            self.root.after(0, lambda value=progress_value, idx=index: self.update_progress(value, idx, self.total_students))

        final_text = f"✅ Done! Generated {self.generated_count} of {self.total_students} report cards"
        if failures:
            final_text += f" (with {len(failures)} failures)"
        self.log_message(final_text)
        self.root.after(0, lambda: self.status_label.configure(text=final_text))
        self.root.after(0, lambda: self.generate_button.configure(state="normal"))
        self.root.after(0, lambda: self.open_folder_button.configure(state="normal"))

        if failures:
            error_text = "Some report cards could not be generated:\n" + "\n".join([f"{name}: {error}" for name, error in failures])
            self.root.after(0, lambda: messagebox.showwarning("Generation Completed With Errors", error_text))

    def update_progress(self, value, index, total):
        self.progress.set(value)
        self.status_label.configure(text=f"Generating {index} of {total}...")

    def open_output_folder(self):
        if not self.output_folder:
            return
        if os.name == "nt":
            os.startfile(self.output_folder)
        else:
            try:
                os.system(f'xdg-open "{self.output_folder}"')
            except Exception:
                pass

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ReportCardGeneratorApp()
    app.run()
