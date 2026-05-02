def create_database():
    return {}


def create_table(database, table_name, fields):
    normalized_name = table_name.strip()
    normalized_fields = [field.strip() for field in fields if field.strip()]

    if not normalized_name:
        return False, "Table name cannot be empty."
    if normalized_name in database:
        return False, "A table with this name already exists."
    if not normalized_fields:
        return False, "The table must contain at least one field."
    if "id" in normalized_fields:
        return False, "The field name 'id' is reserved."
    if len(normalized_fields) != len(set(normalized_fields)):
        return False, "Field names must not be repeated."

    database[normalized_name] = {
        "fields": normalized_fields,
        "records": [],
        "next_id": 1,
    }
    return True, f"Table '{normalized_name}' has been created."


def get_table(database, table_name):
    if table_name not in database:
        return None, "Table not found."
    return database[table_name], ""


def list_tables(database):
    return sorted(database.keys())


def add_record(database, table_name, values):
    table, error = get_table(database, table_name)
    if error:
        return False, error

    record = {"id": table["next_id"]}
    for field in table["fields"]:
        value = values.get(field, "").strip()
        if not value:
            return False, f"Field '{field}' cannot be empty."
        record[field] = value

    table["records"].append(record)
    table["next_id"] += 1
    return True, f"Record with id={record['id']} has been added."


def read_records(database, table_name, filters=None):
    table, error = get_table(database, table_name)
    if error:
        return None, error

    filters = filters or {}
    unknown_fields = [
        field for field in filters if field != "id" and field not in table["fields"]
    ]
    if unknown_fields:
        return None, f"Unknown fields: {', '.join(unknown_fields)}."

    records = []
    for record in table["records"]:
        if record_matches_filters(record, filters):
            records.append(record.copy())

    return records, ""


def record_matches_filters(record, filters):
    for field, expected_value in filters.items():
        actual_value = str(record.get(field, "")).lower()
        expected_value = str(expected_value).lower()
        if actual_value != expected_value:
            return False
    return True


def update_record(database, table_name, record_id, updates):
    table, error = get_table(database, table_name)
    if error:
        return False, error

    record = find_record_by_id(table, record_id)
    if record is None:
        return False, "Record not found."

    for field, value in updates.items():
        if field == "id":
            return False, "Record id cannot be changed."
        if field not in table["fields"]:
            return False, f"Unknown field: {field}."
        if not value.strip():
            return False, f"Field '{field}' cannot be empty."

    for field, value in updates.items():
        record[field] = value.strip()

    return True, "Record has been updated."


def delete_record(database, table_name, record_id):
    table, error = get_table(database, table_name)
    if error:
        return False, error

    for index, record in enumerate(table["records"]):
        if record["id"] == record_id:
            del table["records"][index]
            return True, "Record has been deleted."

    return False, "Record not found."


def find_record_by_id(table, record_id):
    for record in table["records"]:
        if record["id"] == record_id:
            return record
    return None
