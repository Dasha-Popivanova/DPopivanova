
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from database import CsvFileDatabase, DatabaseError, InMemoryDatabase, JsonFileDatabase, Table


def create_project_temp_dir():
    temp_root = Path.cwd() / "test_data"
    temp_root.mkdir(exist_ok=True)
    return TemporaryDirectory(dir=temp_root)


class TableTests(unittest.TestCase):
    def setUp(self):
        self.table = Table("books", ["title", "author", "year", "genre"])
        self.table.add_record(
            {"title": "Eugene Onegin", "author": "Pushkin", "year": "1833", "genre": "novel"}
        )
        self.table.add_record(
            {"title": "War and Peace", "author": "Tolstoy", "year": "1869", "genre": "novel"}
        )
        self.table.add_record(
            {"title": "Ruslan and Ludmila", "author": "Pushkin", "year": "1820", "genre": "poem"}
        )

    def test_add_record_assigns_id(self):
        record = self.table.add_record(
            {"title": "The Captain's Daughter", "author": "Pushkin", "year": "1836", "genre": "novel"}
        )
        self.assertEqual(record["id"], 4)

    def test_add_record_requires_all_fields(self):
        with self.assertRaisesRegex(DatabaseError, "required"):
            self.table.add_record({"title": "Book"})

    def test_add_record_rejects_empty_values(self):
        with self.assertRaisesRegex(DatabaseError, "cannot be empty"):
            self.table.add_record({"title": " ", "author": "A", "year": "2020", "genre": "novel"})

    def test_read_records_filters_by_one_field(self):
        self.assertEqual(len(self.table.read_records({"author": "Pushkin"})), 2)

    def test_read_records_filters_by_several_fields(self):
        records = self.table.read_records({"author": "Pushkin", "genre": "poem"})
        self.assertEqual(records[0]["title"], "Ruslan and Ludmila")

    def test_read_records_filters_by_id(self):
        self.assertEqual(self.table.read_records({"id": 2})[0]["author"], "Tolstoy")

    def test_read_records_rejects_unknown_filter(self):
        with self.assertRaisesRegex(DatabaseError, "Unknown field"):
            self.table.read_records({"rating": "5"})

    def test_read_records_sorts_ascending(self):
        records = self.table.read_records(sort_by="year")
        self.assertEqual([record["year"] for record in records], ["1820", "1833", "1869"])

    def test_read_records_sorts_descending(self):
        records = self.table.read_records(sort_by="title", descending=True)
        self.assertEqual(
            [record["title"] for record in records],
            ["War and Peace", "Ruslan and Ludmila", "Eugene Onegin"],
        )

    def test_read_records_rejects_unknown_sort_field(self):
        with self.assertRaisesRegex(DatabaseError, "Unknown field"):
            self.table.read_records(sort_by="price")

    def test_index_is_used_for_filtering(self):
        self.table.create_index("author")
        records = self.table.read_records({"author": "Pushkin"})

        self.assertTrue(self.table.last_read_used_index)
        self.assertEqual(len(records), 2)

    def test_indexes_are_updated_after_crud_operations(self):
        self.table.create_index(["author", "genre"])
        created = self.table.add_record(
            {"title": "New", "author": "Pushkin", "year": "2026", "genre": "draft"}
        )
        self.table.update_record(created["id"], {"author": "Updated"})
        self.table.delete_record(created["id"])

        self.assertEqual(self.table.read_records({"author": "Pushkin", "genre": "draft"}), [])
        self.assertTrue(self.table.last_read_used_index)

    def test_update_record_changes_selected_fields(self):
        updated = self.table.update_record(1, {"genre": "verse novel"})
        self.assertEqual(updated["genre"], "verse novel")

    def test_update_record_rejects_unknown_record(self):
        with self.assertRaisesRegex(DatabaseError, "not found"):
            self.table.update_record(99, {"genre": "novel"})

    def test_update_record_rejects_id_change(self):
        with self.assertRaisesRegex(DatabaseError, "cannot be changed"):
            self.table.update_record(1, {"id": "5"})

    def test_update_record_rejects_empty_updates(self):
        with self.assertRaisesRegex(DatabaseError, "No fields"):
            self.table.update_record(1, {})

    def test_delete_record_removes_record(self):
        self.table.delete_record(2)
        self.assertEqual(self.table.read_records({"id": 2}), [])

    def test_delete_record_rejects_unknown_record(self):
        with self.assertRaisesRegex(DatabaseError, "not found"):
            self.table.delete_record(99)

    def test_record_id_must_be_positive_integer(self):
        with self.assertRaisesRegex(DatabaseError, "positive integer"):
            self.table.delete_record("bad")
        with self.assertRaisesRegex(DatabaseError, "positive integer"):
            self.table.delete_record(0)

    def test_table_rejects_invalid_definition(self):
        invalid_cases = [
            ("", ["name"]),
            ("users", []),
            ("users", ["id"]),
            ("users", ["name", "name"]),
        ]
        for name, fields in invalid_cases:
            with self.subTest(name=name, fields=fields):
                with self.assertRaises(DatabaseError):
                    Table(name, fields)


class InMemoryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.database = InMemoryDatabase()
        self.database.create_table("books", ["title", "author"])

    def test_create_table_adds_table(self):
        self.database.create_table("users", ["name", "email"])
        self.assertEqual(self.database.list_tables(), ["books", "users"])

    def test_create_table_rejects_duplicate_name(self):
        with self.assertRaisesRegex(DatabaseError, "already exists"):
            self.database.create_table("books", ["name"])

    def test_get_table_rejects_unknown_name(self):
        with self.assertRaisesRegex(DatabaseError, "Table not found"):
            self.database.get_table("unknown")

    def test_crud_methods_delegate_to_selected_table(self):
        created = self.database.add_record("books", {"title": "Dead Souls", "author": "Gogol"})
        found = self.database.read_records("books", {"author": "Gogol"})
        updated = self.database.update_record("books", created["id"], {"author": "N. Gogol"})
        self.database.delete_record("books", created["id"])

        self.assertEqual(found[0]["title"], "Dead Souls")
        self.assertEqual(updated["author"], "N. Gogol")
        self.assertEqual(self.database.read_records("books"), [])

    def test_create_index_delegates_to_selected_table(self):
        self.database.create_index("books", "author")

        self.assertIn("author", self.database.get_table("books").indexed_fields)


class FileDatabaseMixin:
    database_class = None

    def create_database(self, storage_dir):
        return self.database_class(storage_dir)

    def test_file_database_persists_records(self):
        with create_project_temp_dir() as storage_dir:
            database = self.create_database(storage_dir)
            database.create_table("books", ["title", "author", "year"])
            database.add_record(
                "books", {"title": "Book", "author": "Author", "year": "2026"}
            )

            loaded_database = self.create_database(storage_dir)
            records = loaded_database.read_records("books", {"author": "Author"})

        self.assertEqual(records[0]["title"], "Book")

    def test_file_database_persists_updates_deletes_and_indexes(self):
        with create_project_temp_dir() as storage_dir:
            database = self.create_database(storage_dir)
            database.create_table("books", ["title", "author"])
            created = database.add_record("books", {"title": "Old", "author": "Author"})
            database.create_index("books", "author")
            database.update_record("books", created["id"], {"title": "New"})

            loaded_database = self.create_database(storage_dir)
            table = loaded_database.get_table("books")
            records = loaded_database.read_records("books", {"author": "Author"})
            loaded_database.delete_record("books", created["id"])
            loaded_again = self.create_database(storage_dir)

        self.assertIn("author", table.indexed_fields)
        self.assertTrue(table.last_read_used_index)
        self.assertEqual(records[0]["title"], "New")
        self.assertEqual(loaded_again.read_records("books"), [])

    def test_file_database_rejects_duplicate_loaded_tables(self):
        with create_project_temp_dir() as storage_dir:
            database = self.create_database(storage_dir)
            database.create_table("books", ["title"])
            self.copy_table_file(storage_dir, "books", "books_copy")

            with self.assertRaisesRegex(DatabaseError, "Duplicate table"):
                self.create_database(storage_dir)


class JsonFileDatabaseTests(FileDatabaseMixin, unittest.TestCase):
    database_class = JsonFileDatabase

    def copy_table_file(self, storage_dir, source_name, target_name):
        import shutil

        source = Path(storage_dir) / f"{source_name}.json"
        target = Path(storage_dir) / f"{target_name}.json"
        shutil.copy(source, target)

    def test_json_file_database_rejects_invalid_json(self):
        with create_project_temp_dir() as storage_dir:
            Path(storage_dir, "broken.json").write_text("{broken", encoding="utf-8")

            with self.assertRaisesRegex(DatabaseError, "Invalid JSON"):
                JsonFileDatabase(storage_dir)


class CsvFileDatabaseTests(FileDatabaseMixin, unittest.TestCase):
    database_class = CsvFileDatabase

    def copy_table_file(self, storage_dir, source_name, target_name):
        import shutil

        source = Path(storage_dir) / f"{source_name}.csv"
        target = Path(storage_dir) / f"{target_name}.csv"
        shutil.copy(source, target)

    def test_csv_file_database_rejects_invalid_csv(self):
        with create_project_temp_dir() as storage_dir:
            Path(storage_dir, "broken.csv").write_text("bad,data\n", encoding="utf-8")

            with self.assertRaisesRegex(DatabaseError, "Invalid CSV"):
                CsvFileDatabase(storage_dir)


if __name__ == "__main__":
    unittest.main()
