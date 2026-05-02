
import unittest

from database import DatabaseError, InMemoryDatabase, Table


class TableTests(unittest.TestCase):

    def setUp(self):
        self.table = Table("books", ["title", "author", "year", "genre"])
        self.table.add_record(
            {
                "title": "Eugene Onegin",
                "author": "Pushkin",
                "year": "1833",
                "genre": "novel",
            }
        )
        self.table.add_record(
            {
                "title": "War and Peace",
                "author": "Tolstoy",
                "year": "1869",
                "genre": "novel",
            }
        )
        self.table.add_record(
            {
                "title": "Ruslan and Ludmila",
                "author": "Pushkin",
                "year": "1820",
                "genre": "poem",
            }
        )

    def test_add_record_assigns_id(self):
        record = self.table.add_record(
            {
                "title": "The Captain's Daughter",
                "author": "Pushkin",
                "year": "1836",
                "genre": "novel",
            }
        )

        self.assertEqual(record["id"], 4)
        self.assertEqual(len(self.table.records), 4)

    def test_add_record_requires_all_fields(self):
        with self.assertRaisesRegex(DatabaseError, "required"):
            self.table.add_record({"title": "Book"})

    def test_add_record_rejects_empty_values(self):
        with self.assertRaisesRegex(DatabaseError, "cannot be empty"):
            self.table.add_record(
                {"title": "  ", "author": "A", "year": "2020", "genre": "novel"}
            )

    def test_read_records_filters_by_one_field(self):
        records = self.table.read_records({"author": "Pushkin"})

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["title"], "Eugene Onegin")

    def test_read_records_filters_by_several_fields(self):
        records = self.table.read_records({"author": "Pushkin", "genre": "poem"})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Ruslan and Ludmila")

    def test_read_records_filters_by_id(self):
        records = self.table.read_records({"id": 2})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["author"], "Tolstoy")

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

    def test_update_record_changes_selected_fields(self):
        updated = self.table.update_record(1, {"genre": "verse novel"})

        self.assertEqual(updated["genre"], "verse novel")
        self.assertEqual(self.table.read_records({"id": 1})[0]["genre"], "verse novel")

    def test_update_record_rejects_unknown_record(self):
        with self.assertRaisesRegex(DatabaseError, "not found"):
            self.table.update_record(99, {"genre": "novel"})

    def test_update_record_rejects_id_change(self):
        with self.assertRaisesRegex(DatabaseError, "Unknown field|cannot be changed"):
            self.table.update_record(1, {"id": "5"})

    def test_update_record_rejects_empty_updates(self):
        with self.assertRaisesRegex(DatabaseError, "No fields"):
            self.table.update_record(1, {})

    def test_delete_record_removes_record(self):
        self.table.delete_record(2)

        self.assertEqual(len(self.table.records), 2)
        self.assertEqual(self.table.read_records({"id": 2}), [])

    def test_delete_record_rejects_unknown_record(self):
        with self.assertRaisesRegex(DatabaseError, "not found"):
            self.table.delete_record(99)

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
        created = self.database.add_record(
            "books", {"title": "Dead Souls", "author": "Gogol"}
        )
        found = self.database.read_records("books", {"author": "Gogol"})
        updated = self.database.update_record("books", created["id"], {"author": "N. Gogol"})
        self.database.delete_record("books", created["id"])

        self.assertEqual(found[0]["title"], "Dead Souls")
        self.assertEqual(updated["author"], "N. Gogol")
        self.assertEqual(self.database.read_records("books"), [])


if __name__ == "__main__":
    unittest.main()
