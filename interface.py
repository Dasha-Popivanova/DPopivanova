
from database import CsvFileDatabase, DatabaseError, InMemoryDatabase, JsonFileDatabase


class ConsoleInterface:

    def __init__(self, database):
        self.database = database

    def run(self):
        self.create_demo_table()
        while True:
            self.print_menu()
            choice = input("Choose an action: ").strip()

            if choice == "1":
                self.handle_create_table()
            elif choice == "2":
                self.handle_add_record()
            elif choice == "3":
                self.handle_read_records()
            elif choice == "4":
                self.handle_update_record()
            elif choice == "5":
                self.handle_delete_record()
            elif choice == "6":
                self.handle_list_tables()
            elif choice == "7":
                self.handle_create_index()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Error: unknown menu item.")

    def create_demo_table(self):
        if "books" not in self.database.tables:
            self.database.create_table("books", ["title", "author", "year", "genre"])

    @staticmethod
    def print_menu():
        print("\nIn-memory database")
        print("1. Create table")
        print("2. Add record")
        print("3. Read records")
        print("4. Update record")
        print("5. Delete record")
        print("6. Show tables")
        print("7. Create index")
        print("0. Exit")

    def handle_create_table(self):
        table_name = input("Table name: ").strip()
        fields_line = input("Fields separated by commas: ").strip()
        try:
            self.database.create_table(table_name, self.split_csv(fields_line))
            print(f"Success: table '{table_name}' has been created.")
        except DatabaseError as error:
            print(f"Error: {error}")

    def handle_add_record(self):
        table = self.choose_table()
        if table is None:
            return

        values = {}
        for field in table.fields:
            values[field] = input(f"{field}: ")

        try:
            record = table.add_record(values)
            print(f"Success: record with id={record['id']} has been added.")
        except DatabaseError as error:
            print(f"Error: {error}")

    def handle_read_records(self):
        table = self.choose_table()
        if table is None:
            return

        filters = self.ask_filters(table.fields)
        sort_by, descending = self.ask_sorting(table.fields)
        try:
            records = table.read_records(filters, sort_by, descending)
            self.print_records(table.fields, records)
        except DatabaseError as error:
            print(f"Error: {error}")

    def handle_update_record(self):
        table = self.choose_table()
        if table is None:
            return

        record_id = self.ask_record_id()
        if record_id is None:
            return

        updates = self.ask_updates(table.fields)
        try:
            table.update_record(record_id, updates)
            print("Success: record has been updated.")
        except DatabaseError as error:
            print(f"Error: {error}")

    def handle_delete_record(self):
        table = self.choose_table()
        if table is None:
            return

        record_id = self.ask_record_id()
        if record_id is None:
            return

        try:
            table.delete_record(record_id)
            print("Success: record has been deleted.")
        except DatabaseError as error:
            print(f"Error: {error}")

    def handle_list_tables(self):
        table_names = self.database.list_tables()
        if not table_names:
            print("There are no tables.")
            return

        for table_name in table_names:
            table = self.database.get_table(table_name)
            fields = ", ".join(table.fields)
            indexes = ", ".join(sorted(table.indexed_fields)) or "none"
            print(
                f"{table.name}: fields [{fields}], records: {len(table.records)}, "
                f"indexes: {indexes}"
            )

    def handle_create_index(self):
        table = self.choose_table()
        if table is None:
            return

        print("Available fields:", ", ".join(["id"] + table.fields))
        fields = self.split_csv(input("Index fields separated by commas: "))
        try:
            self.database.create_index(table.name, fields)
            print("Success: index has been created.")
        except DatabaseError as error:
            print(f"Error: {error}")

    def choose_table(self):
        table_names = self.database.list_tables()
        if not table_names:
            print("Error: there are no tables. Create a table first.")
            return None

        print("Available tables:", ", ".join(table_names))
        table_name = input("Table name: ").strip()
        try:
            return self.database.get_table(table_name)
        except DatabaseError as error:
            print(f"Error: {error}")
            return None

    def ask_filters(self, fields):
        print("Available filter fields:", ", ".join(["id"] + fields))
        filters_line = input("Filters (field=value, comma-separated, empty for all): ")
        filters = {}
        if not filters_line.strip():
            return filters

        for item in self.split_csv(filters_line):
            if "=" not in item:
                print(f"Filter '{item}' was skipped: expected field=value.")
                continue
            field, value = item.split("=", 1)
            field = field.strip()
            value = value.strip()
            if field == "id":
                record_id = self.parse_positive_int(value)
                if record_id is None:
                    print("Filter 'id' was skipped: expected a positive integer.")
                    continue
                filters[field] = record_id
            else:
                filters[field] = value
        return filters

    def ask_sorting(self, fields):
        print("Available sort fields:", ", ".join(["id"] + fields))
        sort_by = input("Sort by field (empty to skip): ").strip()
        if not sort_by:
            return None, False
        direction = input("Direction (asc/desc): ").strip().lower()
        return sort_by, direction == "desc"

    def ask_updates(self, fields):
        print("Available fields:", ", ".join(fields))
        updates_line = input("Updates (field=value, comma-separated): ")
        updates = {}
        for item in self.split_csv(updates_line):
            if "=" not in item:
                print(f"Update '{item}' was skipped: expected field=value.")
                continue
            field, value = item.split("=", 1)
            updates[field.strip()] = value.strip()
        return updates

    def ask_record_id(self):
        record_id = self.parse_positive_int(input("Record id: ").strip())
        if record_id is None:
            print("Error: id must be a positive integer.")
        return record_id

    @staticmethod
    def parse_positive_int(value):
        try:
            number = int(value)
        except ValueError:
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def split_csv(value):
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def print_records(fields, records):
        if not records:
            print("No records found.")
            return

        columns = ["id"] + fields
        widths = ConsoleInterface.calculate_widths(columns, records)
        separator = "-+-".join("-" * widths[column] for column in columns)
        print(ConsoleInterface.format_row(columns, dict(zip(columns, columns)), widths))
        print(separator)
        for record in records:
            print(ConsoleInterface.format_row(columns, record, widths))

    @staticmethod
    def calculate_widths(columns, records):
        widths = {column: len(column) for column in columns}
        for record in records:
            for column in columns:
                widths[column] = max(widths[column], len(str(record[column])))
        return widths

    @staticmethod
    def format_row(columns, record, widths):
        return " | ".join(str(record[column]).ljust(widths[column]) for column in columns)


def create_database(database_type="json", storage_dir="data"):
    database_type = database_type.lower()
    if database_type == "memory":
        return InMemoryDatabase()
    if database_type == "json":
        return JsonFileDatabase(storage_dir)
    if database_type == "csv":
        return CsvFileDatabase(storage_dir)
    raise DatabaseError("Unknown database type. Use memory, json, or csv.")


def create_application(database_type="json", storage_dir="data"):
    return ConsoleInterface(create_database(database_type, storage_dir))
