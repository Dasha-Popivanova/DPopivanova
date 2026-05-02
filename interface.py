from database import (
    add_record,
    create_database,
    create_table,
    delete_record,
    list_tables,
    read_records,
    update_record,
)


def run_console_app():
    database = create_database()
    create_demo_table(database)

    while True:
        print_menu()
        choice = input("Choose an action: ").strip()

        if choice == "1":
            handle_create_table(database)
        elif choice == "2":
            handle_add_record(database)
        elif choice == "3":
            handle_read_records(database)
        elif choice == "4":
            handle_update_record(database)
        elif choice == "5":
            handle_delete_record(database)
        elif choice == "6":
            handle_list_tables(database)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Error: unknown menu item.")


def create_demo_table(database):
    create_table(database, "books", ["title", "author", "year", "genre"])


def print_menu():
    print("\nIn-memory database")
    print("1. Create table")
    print("2. Add record")
    print("3. Read records")
    print("4. Update record")
    print("5. Delete record")
    print("6. Show tables")
    print("0. Exit")


def handle_create_table(database):
    table_name = input("Table name: ").strip()
    fields_line = input("Fields separated by commas: ").strip()
    fields = split_csv(fields_line)

    success, message = create_table(database, table_name, fields)
    print_result(success, message)


def handle_add_record(database):
    table_name = choose_table(database)
    if not table_name:
        return

    fields = database[table_name]["fields"]
    values = {}
    for field in fields:
        values[field] = input(f"{field}: ")

    success, message = add_record(database, table_name, values)
    print_result(success, message)


def handle_read_records(database):
    table_name = choose_table(database)
    if not table_name:
        return

    filters = ask_filters(database[table_name]["fields"])
    records, error = read_records(database, table_name, filters)
    if error:
        print(f"Error: {error}")
        return

    print_records(database[table_name]["fields"], records)


def handle_update_record(database):
    table_name = choose_table(database)
    if not table_name:
        return

    record_id = ask_record_id()
    if record_id is None:
        return

    updates = ask_updates(database[table_name]["fields"])
    if not updates:
        print("No fields were selected for updating.")
        return

    success, message = update_record(database, table_name, record_id, updates)
    print_result(success, message)


def handle_delete_record(database):
    table_name = choose_table(database)
    if not table_name:
        return

    record_id = ask_record_id()
    if record_id is None:
        return

    success, message = delete_record(database, table_name, record_id)
    print_result(success, message)


def handle_list_tables(database):
    tables = list_tables(database)
    if not tables:
        print("There are no tables.")
        return

    for table_name in tables:
        fields = ", ".join(database[table_name]["fields"])
        count = len(database[table_name]["records"])
        print(f"{table_name}: fields [{fields}], records: {count}")


def choose_table(database):
    tables = list_tables(database)
    if not tables:
        print("Error: there are no tables. Create a table first.")
        return ""

    print("Available tables:", ", ".join(tables))
    table_name = input("Table name: ").strip()
    if table_name not in database:
        print("Error: table not found.")
        return ""
    return table_name


def ask_filters(fields):
    available_fields = ["id"] + fields
    print("Available filter fields:", ", ".join(available_fields))
    filters_line = input("Filters (field=value, comma-separated, empty for all): ")
    filters = {}

    if not filters_line.strip():
        return filters

    for item in split_csv(filters_line):
        if "=" not in item:
            print(f"Filter '{item}' was skipped: expected field=value.")
            continue
        field, value = item.split("=", 1)
        field = field.strip()
        value = value.strip()
        if field == "id":
            record_id = parse_positive_int(value)
            if record_id is None:
                print("Filter 'id' was skipped: expected a positive integer.")
                continue
            filters[field] = record_id
        else:
            filters[field] = value

    return filters


def ask_updates(fields):
    print("Available fields:", ", ".join(fields))
    updates_line = input("Updates (field=value, comma-separated): ")
    updates = {}

    for item in split_csv(updates_line):
        if "=" not in item:
            print(f"Update '{item}' was skipped: expected field=value.")
            continue
        field, value = item.split("=", 1)
        updates[field.strip()] = value.strip()

    return updates


def ask_record_id():
    raw_id = input("Record id: ").strip()
    record_id = parse_positive_int(raw_id)
    if record_id is None:
        print("Error: id must be a positive integer.")
    return record_id


def parse_positive_int(value):
    try:
        number = int(value)
    except ValueError:
        return None
    if number <= 0:
        return None
    return number


def split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def print_result(success, message):
    prefix = "Success" if success else "Error"
    print(f"{prefix}: {message}")


def print_records(fields, records):
    if not records:
        print("No records found.")
        return

    columns = ["id"] + fields
    widths = calculate_widths(columns, records)
    separator = "-+-".join("-" * widths[column] for column in columns)

    print(format_row(columns, columns, widths))
    print(separator)
    for record in records:
        print(format_row(columns, record, widths))


def calculate_widths(columns, records):
    widths = {column: len(column) for column in columns}
    for record in records:
        for column in columns:
            widths[column] = max(widths[column], len(str(record[column])))
    return widths


def format_row(columns, record, widths):
    return " | ".join(str(record[column]).ljust(widths[column]) for column in columns)
