
import ast
import os
import sys
import trace
import unittest


SOURCE_FILES = ["database.py", "interface.py", "main.py"]


def main():
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.base_prefix])
    test_suite = unittest.defaultTestLoader.discover("tests")
    test_runner = unittest.TextTestRunner(verbosity=2)

    result = tracer.runfunc(test_runner.run, test_suite)
    if not result.wasSuccessful():
        sys.exit(1)

    counts = tracer.results().counts
    print("\nCoverage report")
    total_executable = 0
    total_covered = 0

    for file_name in SOURCE_FILES:
        executable_lines = get_executable_lines(file_name)
        covered_lines = get_covered_lines(file_name, counts)
        covered_executable = executable_lines.intersection(covered_lines)
        percent = calculate_percent(len(covered_executable), len(executable_lines))

        total_executable += len(executable_lines)
        total_covered += len(covered_executable)
        print(
            f"{file_name}: {percent:.1f}% "
            f"({len(covered_executable)}/{len(executable_lines)} lines)"
        )

    total_percent = calculate_percent(total_covered, total_executable)
    print(f"Total: {total_percent:.1f}% ({total_covered}/{total_executable} lines)")

    if total_percent < 80:
        sys.exit(2)


def get_executable_lines(file_name):
    statement_types = (
        ast.Assign,
        ast.AugAssign,
        ast.Break,
        ast.Continue,
        ast.Delete,
        ast.ExceptHandler,
        ast.Expr,
        ast.For,
        ast.If,
        ast.Pass,
        ast.Raise,
        ast.Return,
        ast.Try,
        ast.With,
    )
    executable_lines = set()
    with open(file_name, "r", encoding="utf-8") as source_file:
        tree = ast.parse(source_file.read(), filename=file_name)

    docstring_lines = get_docstring_lines(tree)
    for node in ast.walk(tree):
        if isinstance(node, statement_types):
            if node.lineno not in docstring_lines:
                executable_lines.add(node.lineno)

    return executable_lines


def get_docstring_lines(tree):
    docstring_lines = set()
    nodes = [tree]
    nodes.extend(node for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef)))

    for node in nodes:
        if not node.body:
            continue
        first_statement = node.body[0]
        if isinstance(first_statement, ast.Expr) and isinstance(
            first_statement.value, ast.Constant
        ):
            if isinstance(first_statement.value.value, str):
                docstring_lines.add(first_statement.lineno)

    return docstring_lines


def get_covered_lines(file_name, counts):
    expected_path = os.path.abspath(file_name)
    covered_lines = set()

    for (path, line_number), count in counts.items():
        if os.path.abspath(path) == expected_path and count > 0:
            covered_lines.add(line_number)

    return covered_lines


def calculate_percent(covered, total):
    if total == 0:
        return 100
    return covered / total * 100


if __name__ == "__main__":
    main()
