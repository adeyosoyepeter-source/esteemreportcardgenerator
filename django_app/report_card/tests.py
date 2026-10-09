import os
import tempfile
import unittest
from unittest.mock import patch

import django
import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from pypdf import PdfReader
from pypdf.generic import ContentStream

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from report_card.utils import generate_pdf_bytes, read_broadsheet
from report_card.views import upload_broadsheet


class ReadBroadsheetTests(unittest.TestCase):
    def test_subject_row_values_are_drawn_in_visible_black(self):
        pdf_buffer = generate_pdf_bytes(
            {"Student Name": "Ada Lovelace", "Class": "JSS 1"},
            [{"name": "UNIQUE REGRESSION SUBJECT", "score": 88, "max_mark": 100}],
        )
        reader = PdfReader(pdf_buffer)
        content = ContentStream(reader.pages[0].get_contents(), reader)
        current_fill = None
        visible_subject_values = {}

        for operands, operator in content.operations:
            if operator == b"rg":
                current_fill = tuple(float(value) for value in operands)
            elif operator == b"Tj" and str(operands[0]) in {
                "UNIQUE REGRESSION SUBJECT",
                "100",
                "88",
                "88.00%",
                "A",
            }:
                visible_subject_values[str(operands[0])] = current_fill

        self.assertEqual(
            visible_subject_values,
            {
                "UNIQUE REGRESSION SUBJECT": (0.0, 0.0, 0.0),
                "100": (0.0, 0.0, 0.0),
                "88": (0.0, 0.0, 0.0),
                "88.00%": (0.0, 0.0, 0.0),
                "A": (0.0, 0.0, 0.0),
            },
        )

    def test_generated_pdf_uses_reference_template_with_student_values(self):
        subjects = [
            {"name": "English Studies", "score": 60, "max_mark": 100},
            {"name": "Mathematics", "score": 68, "max_mark": 100},
        ]
        pdf_buffer = generate_pdf_bytes(
            {
                "Student Name": "Ada Lovelace",
                "Class": "JSS 1",
                "Term": "Second Term",
                "Session": "2025/2026",
                "Admission No": "ADM001",
            },
            subjects,
        )

        page = PdfReader(pdf_buffer).pages[0]
        text = page.extract_text()
        self.assertIn("ESTEEM STANDARD CHOICE", text)
        self.assertIn("ADA LOVELACE", text)
        self.assertIn("JSS 1 | SECOND TERM | 2025/2026", text)
        self.assertIn("ENGLISH STUDIES", text)
        self.assertIn("60.00%", text)
        self.assertIn("GABRIEL PROMISE", text)
        self.assertEqual(len(PdfReader(pdf_buffer).pages), 1)

    def test_template_extends_rows_and_page_for_more_than_thirteen_subjects(self):
        subjects = [
            {"name": f"EXTRA SUBJECT {index:02}", "score": 50 + index, "max_mark": 100}
            for index in range(16)
        ]
        pdf_buffer = generate_pdf_bytes(
            {"Student Name": "Ada Lovelace", "Class": "JSS 1"},
            subjects,
        )

        page = PdfReader(pdf_buffer).pages[0]
        text = page.extract_text()
        self.assertIn("EXTRA SUBJECT 13", text)
        self.assertIn("EXTRA SUBJECT 14", text)
        self.assertIn("EXTRA SUBJECT 15", text)
        self.assertIn("63.00%", text)
        self.assertIn("100", text)
        self.assertIn("57.50%", text)
        self.assertEqual(len(PdfReader(pdf_buffer).pages), 1)
        self.assertAlmostEqual(float(page.mediabox.height), 841.8898 + 3 * 22)
        self.assertAlmostEqual(float(page.mediabox.lower_left[1]), -3 * 22)
        self.assertAlmostEqual(float(page.mediabox.upper_right[1]), 841.8898)

        content = ContentStream(page.get_contents(), PdfReader(pdf_buffer))
        subject_14_color = None
        current_fill = None
        extra_row_fills = []
        for operands, operator in content.operations:
            if operator == b"rg":
                current_fill = tuple(float(value) for value in operands)
            elif operator == b"re" and (
                float(operands[2]) == 465.2756
                and float(operands[3]) == 22
            ):
                extra_row_fills.append(current_fill)
            elif operator == b"Tj" and str(operands[0]) == "EXTRA SUBJECT 13":
                subject_14_color = current_fill
        self.assertEqual(subject_14_color, (0.0, 0.0, 0.0))
        self.assertEqual(
            extra_row_fills[-3:],
            [
                (0.933333, 0.952941, 0.972549),
                (1.0, 1.0, 1.0),
                (0.933333, 0.952941, 0.972549),
            ],
        )

    def test_parses_school_broadsheet_format_with_header_row_in_row_three(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "broadsheet.xlsx")

            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                rows = [
                    ["ESTEEM STANDARD CHOICE ACADEMY"],
                    ["JSS 1 FIRST TERM RESULT ACADEMIC SESSION FOR 2025/2026"],
                    ["S/N", "ADMISSION NO", "NAMES OF STUDENT", "HOME ADDRESS", "TELEPHONE", "English", "Mathematics", "TOTAL", "AVERAGE"],
                    [1, "ADM001", "Ada Lovelace", "Lagos", "08011111111", 70, 80, None, None],
                ]
                df = pd.DataFrame(rows)
                df.to_excel(writer, sheet_name="JSS 1", index=False, header=False)

            records = read_broadsheet(path)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["student_data"]["Student Name"], "Ada Lovelace")
            self.assertEqual(records[0]["student_data"]["Class"], "JSS 1")
            self.assertEqual(records[0]["student_data"]["Term"], "FIRST TERM")
            self.assertEqual(records[0]["student_data"]["Session"], "2025/2026")
            self.assertEqual(records[0]["subjects"][0]["name"], "English")
            self.assertEqual(records[0]["subjects"][0]["score"], 70)
            self.assertEqual(records[0]["student_data"]["Total"], 150)
            self.assertEqual(records[0]["student_data"]["Average"], 75.0)

    def test_upload_accepts_file_without_metadata_fields(self):
        factory = RequestFactory()
        uploaded_file = SimpleUploadedFile(
            "broadsheet.xlsx",
            b"dummy",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        request = factory.post(
            "/api/upload/",
            data={"file": uploaded_file},
            format="multipart",
        )

        with patch("report_card.views.read_broadsheet", return_value=[{
            "student_data": {"Student Name": "Ada Lovelace", "Class": "JSS 1"},
            "subjects": [],
        }]):
            response = upload_broadsheet(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('"success": true'), 1)


if __name__ == "__main__":
    unittest.main()
