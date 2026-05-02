
import sys

from interface import create_application


def main():
    database_type = sys.argv[1] if len(sys.argv) > 1 else "json"
    storage_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    application = create_application(database_type, storage_dir)
    application.run()


if __name__ == "__main__":
    main()
