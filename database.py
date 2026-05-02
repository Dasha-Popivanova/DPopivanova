from copy import deepcopy


class DatabaseError(Exception):
    """Base exception for database operation errors."""


class Table:

    RESERVED_FIELDS = {"id"}

    def __init__(self, name, fields):
        self.name = self._validate_name(name)
        self.fields = self._validate_fields(fields)
        self.records = []
        self.next_id = 1

    def add_record(self, values):
        record = {"id": self.next_id}

        for field in self.fields:
            value = self._get_required_value(values, field)
            record[field] = value

        self.records.append(record)
        self.next_id += 1
        return deepcopy(record)

    def read_records(self, filters=None, sort_by=None, descending=False):
        filters = filters or {}
        self._validate_field_names(filters.keys(), allow_id=True)

        result = []
        for record in self.records:
            if self._record_matches(record, filters):
                result.append(deepcopy(record))

        if sort_by:
            self._validate_field_names([sort_by], allow_id=True)
            result.sort(key=lambda record: self._sort_value(record[sort_by]))
            if descending:
                result.reverse()

        return result

    def update_record(self, record_id, updates):
        record = self._find_record(record_id)
        if record is None:
            raise DatabaseError("Record not found.")

        if not updates:
            raise DatabaseError("No fields were provided for updating.")

        self._validate_field_names(updates.keys(), allow_id=False)
        for field, value in updates.items():
            record[field] = self._validate_value(field, value)

        return deepcopy(record)

    def delete_record(self, record_id):
        for index, record in enumerate(self.records):
            if record["id"] == self._validate_record_id(record_id):
                del self.records[index]
                return

        raise DatabaseError("Record not found.")

    def _find_record(self, record_id):
        checked_id = self._validate_record_id(record_id)
        for record in self.records:
            if record["id"] == checked_id:
                return record
        return None

    def _record_matches(self, record, filters):
        for field, expected_value in filters.items():
            actual_value = str(record[field]).lower()
            expected_value = str(expected_value).lower()
            if actual_value != expected_value:
                return False
        return True

    def _validate_field_names(self, fields, allow_id):
        available_fields = set(self.fields)
        if allow_id:
            available_fields.add("id")

        for field in fields:
            if field not in available_fields:
                raise DatabaseError(f"Unknown field: {field}.")
            if field == "id" and not allow_id:
                raise DatabaseError("Record id cannot be changed.")

    def _get_required_value(self, values, field):
        if field not in values:
            raise DatabaseError(f"Field '{field}' is required.")
        return self._validate_value(field, values[field])

    @staticmethod
    def _validate_name(name):
        normalized_name = str(name).strip()
        if not normalized_name:
            raise DatabaseError("Table name cannot be empty.")
        return normalized_name

    @classmethod
    def _validate_fields(cls, fields):
        normalized_fields = [str(field).strip() for field in fields if str(field).strip()]

        if not normalized_fields:
            raise DatabaseError("The table must contain at least one field.")
        if cls.RESERVED_FIELDS.intersection(normalized_fields):
            raise DatabaseError("The field name 'id' is reserved.")
        if len(normalized_fields) != len(set(normalized_fields)):
            raise DatabaseError("Field names must not be repeated.")

        return normalized_fields

    @staticmethod
    def _validate_record_id(record_id):
        try:
            checked_id = int(record_id)
        except (TypeError, ValueError) as exc:
            raise DatabaseError("Record id must be a positive integer.") from exc

        if checked_id <= 0:
            raise DatabaseError("Record id must be a positive integer.")
        return checked_id

    @staticmethod
    def _validate_value(field, value):
        checked_value = str(value).strip()
        if not checked_value:
            raise DatabaseError(f"Field '{field}' cannot be empty.")
        return checked_value

    @staticmethod
    def _sort_value(value):
        text_value = str(value)
        try:
            return 0, int(text_value)
        except ValueError:
            pass

        try:
            return 1, float(text_value)
        except ValueError:
            return 2, text_value.lower()


class InMemoryDatabase:

    def __init__(self):
        self.tables = {}

    def create_table(self, table_name, fields):
        table = Table(table_name, fields)
        if table.name in self.tables:
            raise DatabaseError("A table with this name already exists.")

        self.tables[table.name] = table
        return table

    def get_table(self, table_name):
        normalized_name = str(table_name).strip()
        if normalized_name not in self.tables:
            raise DatabaseError("Table not found.")
        return self.tables[normalized_name]

    def list_tables(self):
        return sorted(self.tables.keys())

    def add_record(self, table_name, values):
        return self.get_table(table_name).add_record(values)

    def read_records(self, table_name, filters=None, sort_by=None, descending=False):
        return self.get_table(table_name).read_records(filters, sort_by, descending)

    def update_record(self, table_name, record_id, updates):
        return self.get_table(table_name).update_record(record_id, updates)

    def delete_record(self, table_name, record_id):
        self.get_table(table_name).delete_record(record_id)
