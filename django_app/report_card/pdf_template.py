from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


TEMPLATE_SUBJECT_ROW_COUNT = 13
TEMPLATE_FILENAME = "report_card_gabriel_promise-1.pdf"
_TABLE_LEFT = 68
_TABLE_BOTTOM = 296.8898
_TABLE_WIDTH = 465.2756
_TABLE_ROW_HEIGHT = 22
_TABLE_COLUMN_BOUNDARIES = (104, 268, 330, 408, 478)
_TABLE_VALUE_COLUMNS = (
    (74, 98),
    (104, 268),
    (273, 323),
    (331, 403),
    (410, 480),
    (486, 530),
)
_TEMPLATE_TEXT_FIELDS = (
    (145, 666, 182, 13),
    (104, 638, 38, 13),
    (247, 638, 82, 13),
    (399, 638, 62, 13),
)

_GRADE_LEGEND = (
    ("90% and above: A+ Grade", "80% and above: A Grade"),
    ("70% and above: B+ Grade", "60% and above: B Grade"),
    ("50% and above: C+ Grade", "40% and above: C Grade"),
    ("35% and above: D Grade", "35% and below: Not Graded"),
)


def _draw_fitted_text(pdf_canvas, text, x, y, max_width, font_name, font_size):
    text = str(text or "")
    while font_size > 6 and stringWidth(text, font_name, font_size) > max_width:
        font_size -= 0.25
    pdf_canvas.setFont(font_name, font_size)
    pdf_canvas.drawString(x, y, text)


def _paint_field(pdf_canvas, x, y, width, height, fill_color=colors.white):
    pdf_canvas.setFillColor(fill_color)
    pdf_canvas.rect(x, y, width, height, stroke=0, fill=1)


def _draw_subject_values(pdf_canvas, subject, row_index, baseline, calculate_grade):
    score = subject.get("score")
    maximum = subject.get("max_mark", 100)
    grade, percentage, _ = calculate_grade(score, maximum)
    try:
        maximum_text = f"{float(maximum):.0f}"
    except (TypeError, ValueError):
        maximum_text = str(maximum)
    if score is None:
        score_text = "N/A"
    else:
        try:
            score_text = f"{float(score):.0f}"
        except (TypeError, ValueError):
            score_text = str(score)

    pdf_canvas.setFillColor(colors.black)
    pdf_canvas.setFont("Helvetica", 9.5)
    pdf_canvas.drawCentredString(86, baseline, str(row_index + 1))
    _draw_fitted_text(
        pdf_canvas,
        str(subject.get("name", "")).upper(),
        110,
        baseline,
        156,
        "Helvetica",
        9.5,
    )
    pdf_canvas.setFont("Helvetica", 9.5)
    pdf_canvas.drawCentredString(298, baseline, maximum_text)
    pdf_canvas.drawCentredString(368, baseline, score_text)
    pdf_canvas.drawCentredString(445, baseline, percentage)
    pdf_canvas.drawCentredString(508, baseline, grade)


def _draw_extended_rows(
    pdf_canvas,
    subjects,
    calculate_grade,
    calculate_total_percentage,
):
    first_extra_row = TEMPLATE_SUBJECT_ROW_COUNT
    extra_row_count = len(subjects) - TEMPLATE_SUBJECT_ROW_COUNT
    last_row_bottom = _TABLE_BOTTOM - extra_row_count * _TABLE_ROW_HEIGHT

    pdf_canvas.saveState()
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.rect(
        63,
        99,
        _TABLE_LEFT + _TABLE_WIDTH + 5 - 63,
        180,
        stroke=0,
        fill=1,
    )

    for row_index in range(first_extra_row, len(subjects)):
        row_bottom = _TABLE_BOTTOM - (
            row_index - TEMPLATE_SUBJECT_ROW_COUNT + 1
        ) * _TABLE_ROW_HEIGHT
        row_color = (
            colors.white
            if row_index % 2 == 0
            else colors.HexColor("#EEF3F8")
        )
        pdf_canvas.setFillColor(row_color)
        pdf_canvas.rect(
            _TABLE_LEFT,
            row_bottom,
            _TABLE_WIDTH,
            _TABLE_ROW_HEIGHT,
            stroke=0,
            fill=1,
        )

    pdf_canvas.setStrokeColor(colors.HexColor("#0B1A3B"))
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.line(_TABLE_LEFT, _TABLE_BOTTOM, _TABLE_LEFT, last_row_bottom)
    pdf_canvas.line(
        _TABLE_LEFT + _TABLE_WIDTH,
        _TABLE_BOTTOM,
        _TABLE_LEFT + _TABLE_WIDTH,
        last_row_bottom,
    )
    pdf_canvas.setLineWidth(0.5)
    for boundary in _TABLE_COLUMN_BOUNDARIES:
        pdf_canvas.line(boundary, _TABLE_BOTTOM, boundary, last_row_bottom)
    for row_number in range(1, extra_row_count + 1):
        y = _TABLE_BOTTOM - row_number * _TABLE_ROW_HEIGHT
        pdf_canvas.line(_TABLE_LEFT, y, _TABLE_LEFT + _TABLE_WIDTH, y)

    for row_index in range(first_extra_row, len(subjects)):
        baseline = 590.3898 - (row_index + 1) * _TABLE_ROW_HEIGHT
        _draw_subject_values(
            pdf_canvas,
            subjects[row_index],
            row_index,
            baseline,
            calculate_grade,
        )

    shift = extra_row_count * _TABLE_ROW_HEIGHT
    total_box_y = 232.8898 - shift
    pdf_canvas.setStrokeColor(colors.HexColor("#0B1A3B"))
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.rect(_TABLE_LEFT, total_box_y, _TABLE_WIDTH, 44, stroke=1, fill=0)
    pdf_canvas.setFillColor(colors.HexColor("#0B1A3B"))
    pdf_canvas.rect(_TABLE_LEFT, total_box_y + 28, _TABLE_WIDTH, 16, stroke=0, fill=1)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont("Helvetica-Bold", 9)
    pdf_canvas.drawString(76, total_box_y + 32.5, "TOTAL PERCENTAGE")
    pdf_canvas.setFillColor(colors.black)
    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawCentredString(
        300.6,
        239.8898 - shift,
        f"{calculate_total_percentage(subjects):.2f}%",
    )
    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.drawString(
        68,
        204.8898 - shift,
        f"ISSUE ON {datetime.now().strftime('%d %B %Y')}",
    )

    legend_y = 114.8898 - shift
    pdf_canvas.setStrokeColor(colors.HexColor("#0B1A3B"))
    pdf_canvas.setLineWidth(0.8)
    pdf_canvas.rect(_TABLE_LEFT, legend_y, _TABLE_WIDTH, 60, stroke=1, fill=0)
    pdf_canvas.setFillColor(colors.black)
    pdf_canvas.setFont("Helvetica", 9.5)
    for index, (left_text, right_text) in enumerate(_GRADE_LEGEND):
        baseline = 160.8898 - shift - index * 14
        pdf_canvas.drawString(82, baseline, left_text)
        pdf_canvas.drawString(310.6378, baseline, right_text)
    pdf_canvas.restoreState()


def generate_template_pdf(
    student_data,
    subjects,
    calculate_grade,
    calculate_total_percentage,
):
    """Overlay student values on the supplied report-card artwork."""
    template_path = Path(__file__).resolve().parents[2] / TEMPLATE_FILENAME
    if getattr(sys, "frozen", False):
        template_path = Path(sys._MEIPASS) / TEMPLATE_FILENAME
    if not template_path.is_file():
        raise FileNotFoundError(f"Report-card template not found: {template_path}")

    with template_path.open("rb") as template_file:
        template_reader = PdfReader(template_file)
        if len(template_reader.pages) != 1:
            raise ValueError("The report-card template must contain exactly one page.")

        page = template_reader.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        extra_row_count = max(0, len(subjects) - TEMPLATE_SUBJECT_ROW_COUNT)
        page_extension = extra_row_count * _TABLE_ROW_HEIGHT
        overlay_buffer = BytesIO()
        overlay = canvas.Canvas(
            overlay_buffer,
            pagesize=(page_width, page_height + page_extension),
            pageCompression=1,
        )
        overlay.translate(0, page_extension)

        for x, y, width, height in _TEMPLATE_TEXT_FIELDS:
            _paint_field(overlay, x, y, width, height)

        header = " | ".join(
            str(value).strip()
            for value in (
                student_data.get("Class"),
                student_data.get("Term"),
                student_data.get("Session") or student_data.get("Year"),
            )
            if value
        ).upper()
        _paint_field(overlay, 155, 716, 375, 15)
        overlay.setFillColor(colors.HexColor("#6CB52D"))
        _draw_fitted_text(overlay, header, 158, 718.8898, 370, "Helvetica-Bold", 11)

        overlay.setFillColor(colors.black)
        _draw_fitted_text(
            overlay,
            str(student_data.get("Student Name", "")).upper(),
            148,
            668.3898,
            176,
            "Helvetica-Bold",
            11,
        )
        _draw_fitted_text(
            overlay,
            str(student_data.get("Class", "")).upper(),
            106,
            640.3898,
            34,
            "Helvetica-Bold",
            11,
        )
        _draw_fitted_text(
            overlay,
            student_data.get("Roll No") or student_data.get("Admission No", ""),
            250,
            640.3898,
            77,
            "Helvetica-Bold",
            11,
        )
        _draw_fitted_text(
            overlay,
            student_data.get("Section", ""),
            402,
            640.3898,
            57,
            "Helvetica-Bold",
            11,
        )

        row_baseline = 568.3898
        overlay.setFillColor(colors.black)
        for row_index in range(min(len(subjects), TEMPLATE_SUBJECT_ROW_COUNT)):
            baseline = row_baseline - row_index * _TABLE_ROW_HEIGHT
            row_color = (
                colors.white
                if row_index % 2 == 0
                else colors.HexColor("#EEF3F8")
            )
            for left, right in _TABLE_VALUE_COLUMNS:
                _paint_field(
                    overlay,
                    left,
                    baseline - 3,
                    right - left,
                    12,
                    row_color,
                )

            if row_index < len(subjects):
                _draw_subject_values(
                    overlay,
                    subjects[row_index],
                    row_index,
                    baseline,
                    calculate_grade,
                )

        if extra_row_count:
            _draw_extended_rows(
                overlay,
                subjects,
                calculate_grade,
                calculate_total_percentage,
            )
        else:
            _paint_field(overlay, 268, 235, 72, 24)
            overlay.setFillColor(colors.black)
            overlay.setFont("Helvetica-Bold", 16)
            overlay.drawCentredString(
                300.6,
                239.8898,
                f"{calculate_total_percentage(subjects):.2f}%",
            )

            _paint_field(overlay, 66, 202, 150, 15)
            overlay.setFillColor(colors.black)
            overlay.setFont("Helvetica-Bold", 10)
            overlay.drawString(
                68,
                204.8898,
                f"ISSUE ON {datetime.now().strftime('%d %B %Y')}",
            )

        overlay.save()
        overlay_buffer.seek(0)
        overlay_page = PdfReader(overlay_buffer).pages[0]
        if page_extension:
            expanded_lower_left = (0, -page_extension)
            page.mediabox.lower_left = expanded_lower_left
            page.cropbox.lower_left = expanded_lower_left
            page.merge_translated_page(overlay_page, 0, -page_extension)
        else:
            page.merge_page(overlay_page)

        writer = PdfWriter()
        writer.add_page(page)
        output = BytesIO()
        writer.write(output)

    output.seek(0)
    return output
