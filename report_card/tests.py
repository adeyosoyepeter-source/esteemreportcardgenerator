import os
import tempfile
import unittest
from unittest.mock import patch

import django
import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from report_card.utils import read_broadsheet
from report_card.views import upload_broadsheet


class ReadBroadsheetTests(unittest.TestCase):
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
