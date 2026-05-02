
import csv
import json
from copy import deepcopy
from json import JSONDecodeError
from pathlib import Path
from urllib.parse import quote


class DatabaseError(Exception):
    """Base exception for database operation errors."""


class Table:
    """A single table with CRUD, filtering, sorting, and optional indexes."""

    RESERVED_FIELDS = {"id"}

    def __init__(self, name, fields, records=None, next_id=1, indexed_fields=None):
        self.name = self._validate_name(name)
        self.fields = self._validate_fields(fields)
        self.records = []
        self.next_id = self._validate_next_id(next_id)
        self.indexed_fields = set()
        self.indexes = {}
        self.last_read_used_index = False

        for record in records or []:
            self.records.append(self._validate_loaded_record(record))

        if self.records:
            max_id = max(record["id"] for record in self.records)
            self.next_id = max(self.next_id, max_id + 1)

        for field in indexed_fields or []:
            self.create_index(field)

    def add_record(self, values):
        record = {"id": self.next_id}
        for field in self.fields:
            record[field] = self._get_required_value(values, field)

        self.records.append(record)
        self.next_id += 1
        self._add_record_to_indexes(record)
        return deepcopy(record)

    def read_records(self, filters=None, sort_by=None, descending=False):
        filters = filters or {}
        self._validate_field_names(filters.keys(), allow_id=True)

        source_records = self._get_indexed_candidates(filters)
        result = []
        for record in source_records:
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
        self._remove_record_from_indexes(record)
        for field, value in updates.items():
            record[field] = self._validate_value(field, value)
        self._add_record_to_indexes(record)
        return deepcopy(record)

    def delete_record(self, record_id):
        checked_id = self._validate_record_id(record_id)
        for index, record in enumerate(self.records):
            if record["id"] == checked_id:
                self._remove_record_from_indexes(record)
                del self.records[index]
                return
        raise DatabaseError("Record not found.")

    def create_index(self, fields):
        """Create indexes by one field or by several fields."""
        if isinstance(fields, str):
            fields = [fields]

        self._validate_field_names(fields, allow_id=True)
        for field in fields:
            if field not in self.indexed_fields:
                self.indexed_fields.add(field)
                self.indexes[field] = {}
                for record in self.records:
                    self._add_record_to_index(field, record)

    def to_dict(self):
        """Convert the table to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "fields": list(self.fields),
            "records": deepcopy(self.records),
            "next_id": self.next_id,
            "indexed_fields": sorted(self.indexed_fields),
        }

    @classmethod
    def from_dict(cls, data):
        """Create a table from serialized data."""
        if not isinstance(data, dict):
            raise DatabaseError("Table file must contain an object.")

        required_keys = {"name", "fields", "records", "next_id"}
        missing_keys = required_keys.difference(data)
        if missing_keys:
            raise DatabaseError(f"Table file has missing keys: {', '.join(missing_keys)}.")

        return cls(
            data["name"],
            data["fields"],
            records=data["records"],
            next_id=data["next_id"],
            indexed_fields=data.get("indexed_fields", []),
        )

    def _get_indexed_candidates(self, filters):
        indexed_filters = [
            (field, value) for field, value in filters.items() if field in self.indexed_fields
        ]

        if not indexed_filters:
            self.last_read_used_index = False
            return self.records

        candidate_ids = None
        for field, value in indexed_filters:
            ids = set(self.indexes[field].get(self._index_key(value), set()))
            candidate_ids = ids if candidate_ids is None else candidate_ids.intersection(ids)

        self.last_read_used_index = True
        if not candidate_ids:
            return []
        return [record for record in self.records if record["id"] in candidate_ids]

    def _find_record(self, record_id):
        checked_id = self._validate_record_id(record_id)
        for record in self.records:
            if record["id"] == checked_id:
                return record
        return None

    def _record_matches(self, record, filters):
        for field, expected_value in filters.items():
            if str(record[field]).lower() != str(expected_value).lower():
                return False
        return True

    def _validate_loaded_record(self, record):
        if not isinstance(record, dict):
            raise DatabaseError("Every record must be an object.")

        loaded_record = {"id": self._validate_record_id(record.get("id"))}
        for field in self.fields:
            if field not in record:
                raise DatabaseError(f"Field '{field}' is required.")
            loaded_record[field] = self._validate_value(field, record[field])
        return loaded_record

    def _validate_field_names(self, fields, allow_id):
        available_fields = set(self.fields)
        if allow_id:
            available_fields.add("id")

        for field in fields:
            if field == "id" and not allow_id:
                raise DatabaseError("Record id cannot be changed.")
            if field not in available_fields:
                raise DatabaseError(f"Unknown field: {field}.")

    def _get_required_value(self, values, field):
        if field not in values:
            raise DatabaseError(f"Field '{field}' is required.")
        return self._validate_value(field, values[field])

    def _add_record_to_indexes(self, record):
        for field in self.indexed_fields:
            self._add_record_to_index(field, record)

    def _add_record_to_index(self, field, record):
        key = self._index_key(record[field])
        self.indexes.setdefault(field, {}).setdefault(key, set()).add(record["id"])

    def _remove_record_from_indexes(self, record):
        for field in self.indexed_fields:
            key = self._index_key(record[field])
            ids = self.indexes.get(field, {}).get(key)
            if ids is None:
                continue
            ids.discard(record["id"])
            if not ids:
                del self.indexes[field][key]

    @staticmethod
    def _index_key(value):
        return str(value).lower()

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
    def _validate_next_id(next_id):
        checked_id = Table._validate_record_id(next_id)
        return checked_id

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
    """A database that stores tables in RAM."""

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

    def create_index(self, table_name, fields):
        self.get_table(table_name).create_index(fields)


class JsonFileDatabase(InMemoryDatabase):
    """A file database that stores every table in a JSON file."""

    extension = ".json"

    def __init__(self, storage_dir):
        super().__init__()
        self.storage_dir = Path(storage_dir)
        self._ensure_storage_dir()
        self._load_tables()

    def create_table(self, table_name, fields):
        table = super().create_table(table_name, fields)
        self._save_table(table)
        return table

    def add_record(self, table_name, values):
        record = super().add_record(table_name, values)
        self._save_table(self.get_table(table_name))
        return record

    def update_record(self, table_name, record_id, updates):
        record = super().update_record(table_name, record_id, updates)
        self._save_table(self.get_table(table_name))
        return record

    def delete_record(self, table_name, record_id):
        super().delete_record(table_name, record_id)
        self._save_table(self.get_table(table_name))

    def create_index(self, table_name, fields):
        super().create_index(table_name, fields)
        self._save_table(self.get_table(table_name))

    def _load_tables(self):
        for path in self.storage_dir.glob(f"*{self.extension}"):
            table = self._load_table(path)
            if table.name in self.tables:
                raise DatabaseError(f"Duplicate table name in files: {table.name}.")
            self.tables[table.name] = table

    def _load_table(self, path):
        try:
            with path.open("r", encoding="utf-8") as table_file:
                data = json.load(table_file)
        except JSONDecodeError as exc:
            raise DatabaseError(f"Invalid JSON table file: {path.name}.") from exc
        except OSError as exc:
            raise DatabaseError(f"Cannot read table file: {path.name}.") from exc
        return Table.from_dict(data)

    def _save_table(self, table):
        path = self._table_path(table.name)
        try:
            with path.open("w", encoding="utf-8") as table_file:
                json.dump(table.to_dict(), table_file, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise DatabaseError(f"Cannot write table file: {path.name}.") from exc

    def _table_path(self, table_name):
        return self.storage_dir / f"{quote(table_name, safe='')}{self.extension}"

    def _ensure_storage_dir(self):
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError("Cannot create storage directory.") from exc


class CsvFileDatabase(JsonFileDatabase):
    """A file database that stores every table in a CSV file."""

    extension = ".csv"

    def _load_table(self, path):
        try:
            with path.open("r", encoding="utf-8", newline="") as table_file:
                rows = list(csv.reader(table_file))
        except OSError as exc:
            raise DatabaseError(f"Cannot read table file: {path.name}.") from exc

        if len(rows) < 4 or rows[0][0] != "__table__" or rows[1][0] != "__fields__":
            raise DatabaseError(f"Invalid CSV table file: {path.name}.")
        if rows[2] != ["__records__"]:
            raise DatabaseError(f"Invalid CSV table file: {path.name}.")

        name = rows[0][1]
        next_id = rows[0][2]
        indexed_fields = rows[0][3].split("|") if len(rows[0]) > 3 and rows[0][3] else []
        fields = rows[1][1:]
        header = rows[3]
        expected_header = ["id"] + fields
        if header != expected_header:
            raise DatabaseError(f"Invalid CSV table header: {path.name}.")

        records = []
        for row in rows[4:]:
            if len(row) != len(expected_header):
                raise DatabaseError(f"Invalid CSV record: {path.name}.")
            records.append(dict(zip(expected_header, row)))

        return Table(name, fields, records=records, next_id=next_id, indexed_fields=indexed_fields)

    def _save_table(self, table):
        path = self._table_path(table.name)
        try:
            with path.open("w", encoding="utf-8", newline="") as table_file:
                writer = csv.writer(table_file)
                writer.writerow(
                    ["__table__", table.name, table.next_id, "|".join(sorted(table.indexed_fields))]
                )
                writer.writerow(["__fields__", *table.fields])
                writer.writerow(["__records__"])
                writer.writerow(["id", *table.fields])
                for record in table.records:
                    writer.writerow([record["id"], *[record[field] for field in table.fields]])
        except OSError as exc:
            raise DatabaseError(f"Cannot write table file: {path.name}.") from exc
