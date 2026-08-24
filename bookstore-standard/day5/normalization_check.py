import csv
import json
import sqlite3
import sys
from decimal import Decimal, InvalidOperation
from itertools import zip_longest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_COLUMNS = [
    "member_id",
    "member_name",
    "book_id",
    "book_name",
    "category_code",
    "category_name",
    "order_id",
    "order_datetime",
    "order_status_code",
    "quantity",
    "unit_price",
]
EXPECTED_ENTITY_IDS = {"member", "category", "book", "order", "order-item"}
DAY5_ARTIFACTS = [
    "relationship-rules.md",
    "normalized-model.md",
    "normalized-schema.sql",
    "normalization-report.json",
]


def write_json(file_name, value):
    path = BASE_DIR / file_name
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_day4_entity_ids():
    path = BASE_DIR / "entity-candidates.csv"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as file:
        return {
            row.get("entity_id", "")
            for row in csv.DictReader(file)
            if row.get("status", "").lower() == "accepted"
        }


def read_day4_validation():
    path = BASE_DIR / "day4-validation.json"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def canonical_source_row(row, line_number, issues):
    cleaned = {column: row.get(column, "").strip() for column in SOURCE_COLUMNS}
    empty_columns = [column for column, value in cleaned.items() if value == ""]
    if empty_columns:
        issues.append(
            {
                "type": "empty-required-value",
                "line": line_number,
                "columns": empty_columns,
            }
        )

    try:
        quantity = int(cleaned["quantity"])
        unit_price = Decimal(cleaned["unit_price"])
    except (ValueError, InvalidOperation):
        issues.append(
            {
                "type": "invalid-number",
                "line": line_number,
                "quantity": cleaned["quantity"],
                "unit_price": cleaned["unit_price"],
            }
        )
        return cleaned

    if quantity < 1 or quantity > 999:
        issues.append(
            {"type": "quantity-out-of-domain", "line": line_number, "value": quantity}
        )
    if unit_price < Decimal("0.00") or unit_price > Decimal("9999999999.99"):
        issues.append(
            {"type": "unit-price-out-of-domain", "line": line_number, "value": str(unit_price)}
        )
    if unit_price != unit_price.quantize(Decimal("0.01")):
        issues.append(
            {"type": "unit-price-scale-overflow", "line": line_number, "value": str(unit_price)}
        )

    cleaned["quantity"] = str(quantity)
    cleaned["unit_price"] = format(unit_price, ".2f")
    return cleaned


def remember(mapping, key, value, entity_name, line_number, issues):
    if key not in mapping:
        mapping[key] = value
        return
    if mapping[key] != value:
        issues.append(
            {
                "type": "identifier-description-conflict",
                "entity": entity_name,
                "key": key,
                "first_value": mapping[key],
                "conflicting_value": value,
                "line": line_number,
            }
        )


def build_outputs(
    source_name,
    issues,
    table_counts,
    foreign_key_violations,
    round_trip_match,
    mismatch_samples,
):
    normalization_passed = (
        len(issues) == 0
        and len(foreign_key_violations) == 0
        and round_trip_match
    )
    report = {
        "day": 5,
        "status": "ready" if normalization_passed else "blocked",
        "source": source_name,
        "source_grain": "one row per order_id and book_id",
        "issues": issues,
        "table_counts": table_counts,
        "foreign_key_violations": foreign_key_violations,
        "round_trip": {
            "matched": round_trip_match,
            "mismatch_samples": mismatch_samples,
        },
    }
    write_json("normalization-report.json", report)

    normalized_model_path = BASE_DIR / "normalized-model.md"
    normalized_model_text = (
        normalized_model_path.read_text(encoding="utf-8")
        if normalized_model_path.exists()
        else ""
    )
    schema_path = BASE_DIR / "normalized-schema.sql"
    schema_text = (
        schema_path.read_text(encoding="utf-8") if schema_path.exists() else ""
    )
    day4_ids = read_day4_entity_ids()
    day4_validation_path = BASE_DIR / "day4-validation.json"
    day4_validation = read_day4_validation()
    missing_artifacts = [
        file_name for file_name in DAY5_ARTIFACTS if not (BASE_DIR / file_name).exists()
    ]

    checks = {
        "day4_validation_exists": day4_validation_path.is_file(),
        "day4_validation_ready": (
            day4_validation.get("status") == "ready"
        ),
        "day5_artifacts_exist": len(missing_artifacts) == 0,
        "stable_entity_ids_preserved": day4_ids == EXPECTED_ENTITY_IDS,
        "normalized_model_mentions_stable_ids": all(
            f"stable_id: {entity_id}" in normalized_model_text
            for entity_id in EXPECTED_ENTITY_IDS
        ),
        "schema_has_five_tables": all(
            f"CREATE TABLE {table_name}" in schema_text
            for table_name in ["member", "category", "book", "book_order", "order_item"]
        ),
        "schema_has_pk_fk_and_checks": all(
            token in schema_text
            for token in ["PRIMARY KEY", "FOREIGN KEY", "CHECK", "ON DELETE RESTRICT"]
        ),
        "fixed_fixture_counts_match": all(
            table_counts.get(name) == expected
            for name, expected in {
                "source_rows": 6,
                "member": 4,
                "category": 3,
                "book": 5,
                "book_order": 5,
                "order_item": 6,
                "order_amount": "153000.00",
            }.items()
        ),
        "source_has_no_grain_or_description_conflict": len(issues) == 0,
        "foreign_keys_are_valid": len(foreign_key_violations) == 0,
        "join_restores_source_facts": round_trip_match,
    }
    validation_passed = normalization_passed and all(checks.values())
    validation = {
        "day": 5,
        "status": "ready" if validation_passed else "blocked",
        "checks": checks,
        "evidence": {
            "missing_artifacts": missing_artifacts,
            "day4_validation_file": "day4-validation.json",
            "day4_validation_status": day4_validation.get("status"),
            "day4_entity_ids": sorted(day4_ids),
            "normalization_report": "normalization-report.json",
            "write_model": "normalized-schema.sql",
        },
        "next_day": {
            "day": 6,
            "write_model_input": "normalized-schema.sql",
            "read_model_requirement": "ai-entity-scope.yaml",
        },
    }
    write_json("day5-validation.json", validation)
    return validation["status"]


def main():
    source_path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else BASE_DIR / "standardized-orders.csv"
    )
    schema_path = BASE_DIR / "normalized-schema.sql"
    issues = []
    day4_validation = read_day4_validation()

    if not source_path.exists():
        issues.append({"type": "missing-source", "path": str(source_path)})
    if not schema_path.exists():
        issues.append({"type": "missing-schema", "path": str(schema_path)})
    if day4_validation.get("status") != "ready":
        issues.append(
            {
                "type": "day4-validation-not-ready",
                "path": str(BASE_DIR / "day4-validation.json"),
                "actual_status": day4_validation.get("status"),
                "expected_status": "ready",
            }
        )
    if issues:
        status = build_outputs(
            source_path.name,
            issues,
            {},
            [],
            False,
            [],
        )
        print(f"{status.upper()}: day5-validation.json")
        return 1

    with source_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        missing_columns = [
            column for column in SOURCE_COLUMNS if column not in fieldnames
        ]
        if missing_columns:
            issues.append(
                {"type": "missing-columns", "columns": missing_columns}
            )
        raw_rows = list(reader)

    source_rows = [
        canonical_source_row(row, line_number, issues)
        for line_number, row in enumerate(raw_rows, start=2)
    ]

    members = {}
    categories = {}
    books = {}
    orders = {}
    order_items = {}

    for line_number, row in enumerate(source_rows, start=2):
        remember(
            members,
            row["member_id"],
            row["member_name"],
            "member",
            line_number,
            issues,
        )
        remember(
            categories,
            row["category_code"],
            row["category_name"],
            "category",
            line_number,
            issues,
        )
        remember(
            books,
            row["book_id"],
            (row["book_name"], row["category_code"]),
            "book",
            line_number,
            issues,
        )
        remember(
            orders,
            row["order_id"],
            (
                row["member_id"],
                row["order_datetime"],
                row["order_status_code"],
            ),
            "order",
            line_number,
            issues,
        )

        item_key = (row["order_id"], row["book_id"])
        if item_key in order_items:
            issues.append(
                {
                    "type": "duplicate-order-item-grain",
                    "line": line_number,
                    "order_id": row["order_id"],
                    "book_id": row["book_id"],
                }
            )
        else:
            order_items[item_key] = (row["quantity"], row["unit_price"])

    if issues:
        status = build_outputs(
            source_path.name,
            issues,
            {
                "source_rows": len(source_rows),
                "member": len(members),
                "category": len(categories),
                "book": len(books),
                "book_order": len(orders),
                "order_item": len(order_items),
            },
            [],
            False,
            [],
        )
        print(f"{status.upper()}: source issues found")
        return 1

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema_path.read_text(encoding="utf-8"))

    connection.executemany(
        "INSERT INTO member (member_id, member_name) VALUES (?, ?)",
        sorted(members.items()),
    )
    connection.executemany(
        "INSERT INTO category (category_code, category_name) VALUES (?, ?)",
        sorted(categories.items()),
    )
    connection.executemany(
        "INSERT INTO book (book_id, book_name, category_code) VALUES (?, ?, ?)",
        [
            (book_id, values[0], values[1])
            for book_id, values in sorted(books.items())
        ],
    )
    connection.executemany(
        """
        INSERT INTO book_order (
            order_id,
            member_id,
            order_datetime,
            order_status_code
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (order_id, values[0], values[1], values[2])
            for order_id, values in sorted(orders.items())
        ],
    )
    connection.executemany(
        """
        INSERT INTO order_item (
            order_id,
            book_id,
            quantity,
            unit_price
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (item_key[0], item_key[1], int(values[0]), values[1])
            for item_key, values in sorted(order_items.items())
        ],
    )
    connection.commit()

    foreign_key_violations = [
        list(row) for row in connection.execute("PRAGMA foreign_key_check")
    ]

    joined_rows = []
    query = """
        SELECT
            m.member_id,
            m.member_name,
            b.book_id,
            b.book_name,
            c.category_code,
            c.category_name,
            o.order_id,
            o.order_datetime,
            o.order_status_code,
            i.quantity,
            i.unit_price
        FROM order_item AS i
        JOIN book_order AS o ON o.order_id = i.order_id
        JOIN member AS m ON m.member_id = o.member_id
        JOIN book AS b ON b.book_id = i.book_id
        JOIN category AS c ON c.category_code = b.category_code
        ORDER BY o.order_id, b.book_id
    """
    for values in connection.execute(query):
        joined_row = {
            column: str(value)
            for column, value in zip(SOURCE_COLUMNS, values)
        }
        joined_row["quantity"] = str(int(joined_row["quantity"]))
        joined_row["unit_price"] = format(
            Decimal(joined_row["unit_price"]),
            ".2f",
        )
        joined_rows.append(joined_row)

    sorted_source_rows = sorted(
        source_rows,
        key=lambda row: (row["order_id"], row["book_id"]),
    )
    mismatch_samples = []
    for source_row, joined_row in zip_longest(sorted_source_rows, joined_rows):
        if source_row != joined_row:
            mismatch_samples.append(
                {"source": source_row, "joined": joined_row}
            )
        if len(mismatch_samples) == 5:
            break

    round_trip_match = (
        len(sorted_source_rows) == len(joined_rows)
        and len(mismatch_samples) == 0
    )
    order_amount_value = connection.execute(
        "SELECT SUM(quantity * unit_price) FROM order_item"
    ).fetchone()[0]
    order_amount = format(Decimal(str(order_amount_value or 0)), ".2f")
    table_counts = {
        "source_rows": len(source_rows),
        "member": connection.execute("SELECT COUNT(*) FROM member").fetchone()[0],
        "category": connection.execute("SELECT COUNT(*) FROM category").fetchone()[0],
        "book": connection.execute("SELECT COUNT(*) FROM book").fetchone()[0],
        "book_order": connection.execute(
            "SELECT COUNT(*) FROM book_order"
        ).fetchone()[0],
        "order_item": connection.execute(
            "SELECT COUNT(*) FROM order_item"
        ).fetchone()[0],
        "order_amount": order_amount,
    }
    connection.close()

    status = build_outputs(
        source_path.name,
        issues,
        table_counts,
        foreign_key_violations,
        round_trip_match,
        mismatch_samples,
    )
    print(f"{status.upper()}: day5-validation.json")
    print(json.dumps(table_counts, ensure_ascii=False, indent=2))
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())