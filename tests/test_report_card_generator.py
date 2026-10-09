import os
import tempfile
import unittest

import pandas as pd

from report_card_generator import calculate_grade, calculate_total_percentage, read_broadsheet


class ReadBroadsheetTests(unittest.TestCase):
    def test_grade_and_percentage_helpers_use_requested_letter_scale(self):
        self.assertEqual(calculate_grade(90)[0], "A")
        self.assertEqual(calculate_grade(80)[0], "A")
        self.assertEqual(calculate_grade(70)[0], "A")
        self.assertEqual(calculate_grade(69)[0], "B")
        self.assertEqual(calculate_grade(59)[0], "C")
        self.assertEqual(calculate_grade(49)[0], "D")
        self.assertEqual(calculate_grade(44)[0], "E")
        self.assertEqual(calculate_grade(39)[0], "F")
        self.assertEqual(calculate_grade(75)[1], "75.00%")
        self.assertEqual(calculate_total_percentage([{"score": 80}, {"score": 60}]), 70.0)

    def test_reads_multiple_sheets_and_skips_invalid_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "broadsheet.xlsx")

            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                sheet_data = [
                    (
                        "JSS 1",
                        [
                            ["ESTEEM STANDARD CHOICE ACADEMY"],
                            ["JSS 1 FIRST TERM RESULT ACADEMIC SESSION FOR 2025/2026"],
                            ["S/N", "ADMISSION NO", "NAMES OF STUDENT", "HOME ADDRESS", "TELEPHONE", "English", "Mathematics", "TOTAL", "AVERAGE"],
                            [1, "ADM001", "Ada Lovelace", "Lagos", "08011111111", 70, 80, None, None],
                            [2, "ADM002", "", "Lagos", "08022222222", None, None, None, None],
                            [3, "ADM003", "Grace Hopper", "Abuja", "08033333333", None, None, None, None],
                        ],
                    ),
                    (
                        "SS 1",
                        [
                            ["ESTEEM STANDARD CHOICE ACADEMY"],
                            ["SS 1 FIRST TERM RESULT BROADSHEET FOR 2025/2026 SESSION"],
                            ["S/N", "ADMISSION NO", "NAMES OF STUDENT", "HOME ADDRESS", "TELEPHONE", "Biology", "Chemistry", "TOTAL", "AVERAGE"],
                            [1, "ADM004", "Alan Turing", "Kano", "08044444444", 60, 90, None, None],
                        ],
                    ),
                    (
                        "Invalid",
                        [
                            ["ESTEEM STANDARD CHOICE ACADEMY"],
                            ["INVALID TITLE"],
                            ["S/N", "ADMISSION NO", "NAME", "HOME ADDRESS", "TELEPHONE", "English", "TOTAL", "AVERAGE"],
                            [1, "ADM005", "Should Skip", "Lagos", "08055555555", 50, None, None],
                        ],
                    ),
                ]

                for sheet_name, rows in sheet_data:
                    df = pd.DataFrame(rows)
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)

            records = read_broadsheet(path)

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["student_data"]["Class"], "JSS 1")
            self.assertEqual(records[0]["student_data"]["Term"], "FIRST TERM")
            self.assertEqual(records[0]["student_data"]["Session"], "2025/2026")
            self.assertEqual(records[0]["subjects"][0]["name"], "English")
            self.assertEqual(records[0]["subjects"][0]["score"], 70)
            self.assertEqual(records[0]["student_data"]["Total"], 150)
            self.assertEqual(records[0]["student_data"]["Average"], 75.0)
            self.assertEqual(records[1]["student_data"]["Class"], "SS 1")
            self.assertEqual(records[1]["student_data"]["Term"], "FIRST TERM")
            self.assertEqual(records[1]["student_data"]["Session"], "2025/2026")


if __name__ == "__main__":
    unittest.main()
