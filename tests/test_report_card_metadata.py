import unittest

from django_app.report_card.utils import apply_report_metadata


class ReportMetadataTests(unittest.TestCase):
    def test_apply_report_metadata_updates_term_and_year(self):
        student_data = {
            "Student Name": "Ada Lovelace",
            "Class": "JSS 1",
            "Term": "",
            "Session": "",
        }

        updated = apply_report_metadata(student_data, term="Second Term", year="2026")

        self.assertEqual(updated["Term"], "Second Term")
        self.assertEqual(updated["Session"], "2026")
        self.assertEqual(updated["Year"], "2026")


if __name__ == "__main__":
    unittest.main()
