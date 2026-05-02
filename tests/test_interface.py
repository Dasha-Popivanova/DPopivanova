
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from database import CsvFileDatabase, InMemoryDatabase, JsonFileDatabase
from interface import ConsoleInterface, create_application, create_database
from main import main


class ConsoleInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.database = InMemoryDatabase()
        self.database.create_table("books", ["title", "author", "year"])
        self.interface = ConsoleInterface(self.database)

    def test_create_application_returns_interface(self):
        self.assertIsInstance(create_application("memory"), ConsoleInterface)

    def test_create_database_selects_implementation(self):
        self.assertIsInstance(create_database("memory"), InMemoryDatabase)
        temp_root = Path.cwd() / "test_data"
        temp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=temp_root) as storage_dir:
            self.assertIsInstance(create_database("json", storage_dir), JsonFileDatabase)
            self.assertIsInstance(create_database("csv", storage_dir), CsvFileDatabase)

        with self.assertRaisesRegex(Exception, "Unknown database type"):
            create_database("unknown")

    def test_split_csv_removes_empty_items(self):
        self.assertEqual(self.interface.split_csv("title, author, , year"), ["title", "author", "year"])

    def test_parse_positive_int(self):
        self.assertEqual(self.interface.parse_positive_int("10"), 10)
        self.assertIsNone(self.interface.parse_positive_int("0"))
        self.assertIsNone(self.interface.parse_positive_int("abc"))

    def test_ask_filters_reads_id_and_text_filters(self):
        with patch("builtins.input", return_value="id=2, author=Pushkin"):
            self.assertEqual(self.interface.ask_filters(["title", "author"]), {"id": 2, "author": "Pushkin"})

    def test_ask_filters_skips_invalid_items(self):
        with patch("builtins.input", return_value="bad-filter, id=no"):
            self.assertEqual(self.interface.ask_filters(["title", "author"]), {})

    def test_ask_sorting_reads_descending_direction(self):
        with patch("builtins.input", side_effect=["year", "desc"]):
            sort_by, descending = self.interface.ask_sorting(["title", "year"])
        self.assertEqual(sort_by, "year")
        self.assertTrue(descending)

    def test_ask_sorting_can_be_skipped(self):
        with patch("builtins.input", return_value=""):
            sort_by, descending = self.interface.ask_sorting(["title", "year"])
        self.assertIsNone(sort_by)
        self.assertFalse(descending)

    def test_ask_updates_reads_and_skips_values(self):
        with patch("builtins.input", return_value="broken, title=New title, year=2026"):
            updates = self.interface.ask_updates(["title", "year"])
        self.assertEqual(updates, {"title": "New title", "year": "2026"})

    def test_ask_record_id(self):
        with patch("builtins.input", return_value="3"):
            self.assertEqual(self.interface.ask_record_id(), 3)
        with patch("builtins.input", return_value="-1"):
            self.assertIsNone(self.interface.ask_record_id())

    def test_print_records(self):
        records = [{"id": 1, "title": "Book", "author": "Author"}]
        with patch("builtins.print") as mocked_print:
            self.interface.print_records(["title", "author"], records)
        self.assertGreaterEqual(mocked_print.call_count, 3)

    def test_print_records_handles_empty_result(self):
        with patch("builtins.print") as mocked_print:
            self.interface.print_records(["title"], [])
        mocked_print.assert_called_with("No records found.")

    def test_calculate_widths_and_format_row(self):
        records = [{"id": 1, "title": "Long title"}]
        widths = self.interface.calculate_widths(["id", "title"], records)
        self.assertIn("Long title", self.interface.format_row(["id", "title"], records[0], widths))

    def test_choose_table(self):
        with patch("builtins.input", return_value="books"):
            self.assertEqual(self.interface.choose_table().name, "books")
        with patch("builtins.input", return_value="unknown"):
            self.assertIsNone(self.interface.choose_table())
        self.assertIsNone(ConsoleInterface(InMemoryDatabase()).choose_table())

    def test_create_demo_table_adds_books_once(self):
        interface = ConsoleInterface(InMemoryDatabase())
        interface.create_demo_table()
        interface.create_demo_table()
        self.assertEqual(interface.database.list_tables(), ["books"])

    def test_print_menu_outputs_items(self):
        with patch("builtins.print") as mocked_print:
            self.interface.print_menu()
        self.assertGreaterEqual(mocked_print.call_count, 8)

    def test_handle_create_table_success_and_error(self):
        with patch("builtins.input", side_effect=["users", "name, email"]):
            self.interface.handle_create_table()
        self.assertIn("users", self.database.list_tables())

        with patch("builtins.input", side_effect=["books", "title"]):
            with patch("builtins.print") as mocked_print:
                self.interface.handle_create_table()
        self.assertTrue(any("Error:" in str(call) for call in mocked_print.call_args_list))

    def test_handle_add_record_success_and_missing_table(self):
        with patch("builtins.input", side_effect=["books", "Book", "Author", "2026"]):
            self.interface.handle_add_record()
        self.assertEqual(len(self.database.read_records("books")), 1)

        with patch("builtins.input", return_value="unknown"):
            self.interface.handle_add_record()
        self.assertEqual(len(self.database.read_records("books")), 1)

    def test_handle_read_records_prints_sorted_records(self):
        self.database.add_record("books", {"title": "B", "author": "Author", "year": "2025"})
        self.database.add_record("books", {"title": "A", "author": "Author", "year": "2026"})
        with patch("builtins.input", side_effect=["books", "", "title", "asc"]):
            with patch("builtins.print") as mocked_print:
                self.interface.handle_read_records()
        self.assertGreater(mocked_print.call_count, 3)

    def test_handle_update_record(self):
        self.database.add_record("books", {"title": "Old", "author": "Author", "year": "2026"})
        with patch("builtins.input", side_effect=["books", "1", "title=New"]):
            self.interface.handle_update_record()
        self.assertEqual(self.database.read_records("books", {"id": 1})[0]["title"], "New")

        with patch("builtins.input", side_effect=["books", "bad"]):
            self.interface.handle_update_record()

    def test_handle_delete_record(self):
        self.database.add_record("books", {"title": "Book", "author": "Author", "year": "2026"})
        with patch("builtins.input", side_effect=["books", "1"]):
            self.interface.handle_delete_record()
        self.assertEqual(self.database.read_records("books"), [])

        with patch("builtins.input", side_effect=["books", "99"]):
            with patch("builtins.print") as mocked_print:
                self.interface.handle_delete_record()
        self.assertTrue(any("Error:" in str(call) for call in mocked_print.call_args_list))

    def test_handle_list_tables(self):
        with patch("builtins.print") as mocked_print:
            self.interface.handle_list_tables()
        self.assertTrue(any("books" in str(call) for call in mocked_print.call_args_list))

        with patch("builtins.print") as mocked_print:
            ConsoleInterface(InMemoryDatabase()).handle_list_tables()
        mocked_print.assert_called_with("There are no tables.")

    def test_handle_create_index(self):
        with patch("builtins.input", side_effect=["books", "author, year"]):
            self.interface.handle_create_index()

        table = self.database.get_table("books")
        self.assertEqual(table.indexed_fields, {"author", "year"})

    def test_handle_create_index_reports_errors(self):
        with patch("builtins.input", side_effect=["books", "unknown"]):
            with patch("builtins.print") as mocked_print:
                self.interface.handle_create_index()

        self.assertTrue(any("Error:" in str(call) for call in mocked_print.call_args_list))

    def test_run_exits_and_reports_unknown_item(self):
        interface = ConsoleInterface(InMemoryDatabase())
        with patch("builtins.input", side_effect=["x", "0"]):
            with patch("builtins.print") as mocked_print:
                interface.run()
        self.assertTrue(any("unknown menu" in str(call) for call in mocked_print.call_args_list))

    def test_main_starts_application(self):
        with patch("sys.argv", ["main.py", "memory", "data"]):
            with patch("main.create_application") as mocked_factory:
                main()
        mocked_factory.assert_called_once_with("memory", "data")
        mocked_factory.return_value.run.assert_called_once()

    def test_main_uses_defaults(self):
        with patch("sys.argv", ["main.py"]):
            with patch("main.create_application") as mocked_factory:
                main()
        mocked_factory.assert_called_once_with("json", "data")


if __name__ == "__main__":
    unittest.main()
