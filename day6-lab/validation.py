import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DAY5_DIR = BASE_DIR.parent / "bookstore-standard" / "day5"

SOURCE_SCHEMAS = {
    "members.csv": ["member_id", "member_name"],
    "categories.csv": ["category_code", "category_name"],
    "books.csv": ["book_id", "book_name", "category_code"],
    "orders.csv": [
        "order_id",
        "member_id",
        "order_datetime",
        "order_status_code",
    ],
    "order-items.csv": ["order_id", "book_id", "quantity", "unit_price"],
}

FEATURE_FIELDS = [
    "member_id",
    "as_of_date",
    "order_count_30d",
    "quantity_sum_30d",
    "spend_sum_30d",
    "preferred_category_code_30d",
    "last_order_days_ago",
]

EXPECTED_FIXTURE_COUNTS = {
    "member": 4,
    "category": 3,
    "book": 5,
    "book_order": 5,
    "order_item": 6,
}

WRITE_MODEL_STATUSES = {"PAID", "SHIPPING", "DONE", "CANCELLED"}
FEATURE_STATUSES = {"PAID", "SHIPPING", "DONE"}

DAY6_ARTIFACTS = [
    "build_features.py",
    "feature-view-spec.yaml",
    "feature-standard-extension.yaml",
    "denormalization-decision.md",
    "db-catalog.csv",
    "check_catalog.py",
    "catalog-standard-check.json",
    "feature-sample.csv",
]

CATALOG_STANDARD = {
    ("members", "member_id"): ("VARCHAR", "20", "N"),
    ("members", "member_name"): ("VARCHAR", "100", "N"),
    ("categories", "category_code"): ("VARCHAR", "20", "N"),
    ("categories", "category_name"): ("VARCHAR", "100", "N"),
    ("books", "book_id"): ("VARCHAR", "20", "N"),
    ("books", "book_name"): ("VARCHAR", "200", "N"),
    ("books", "category_code"): ("VARCHAR", "20", "N"),
    ("orders", "order_id"): ("VARCHAR", "20", "N"),
    ("orders", "member_id"): ("VARCHAR", "20", "N"),
    ("orders", "order_datetime"): ("DATETIME", "", "N"),
    ("orders", "order_status_code"): ("VARCHAR", "20", "N"),
    ("order_items", "order_id"): ("VARCHAR", "20", "N"),
    ("order_items", "book_id"): ("VARCHAR", "20", "N"),
    ("order_items", "quantity"): ("INTEGER", "", "N"),
    ("order_items", "unit_price"): ("DECIMAL", "12", "N"),
}

FEATURE_DOMAINS = {
    "as_of_date": "DATE_ISO",
    "order_count_30d": "NON_NEGATIVE_INTEGER",
    "quantity_sum_30d": "NON_NEGATIVE_INTEGER",
    "spend_sum_30d": "MONEY_12_2",
    "preferred_category_code_30d": "OPTIONAL_CODE_20",
    "last_order_days_ago": "OPTIONAL_NON_NEGATIVE_INTEGER",
}


def add_issue(issues, issue_type, message, **evidence):
    issue = {"type": issue_type, "message": message}
    if evidence:
        issue["evidence"] = evidence
    issues.append(issue)


def read_json(path, issues):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        add_issue(
            issues,
            "invalid-json",
            f"{path.name}을 JSON으로 읽을 수 없습니다.",
            path=str(path),
            error=str(error),
        )
        return {}


def read_text(path, issues):
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        add_issue(
            issues,
            "unreadable-file",
            f"{path.name}을 읽을 수 없습니다.",
            path=str(path),
            error=str(error),
        )
        return ""


def read_csv_checked(path, expected_fields, issues):
    if not path.is_file():
        return [], False
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            actual_fields = reader.fieldnames or []
            schema_matches = actual_fields == expected_fields
            if not schema_matches:
                add_issue(
                    issues,
                    "csv-schema-mismatch",
                    f"{path.name}의 컬럼이 기대 스키마와 다릅니다.",
                    file=path.name,
                    expected=expected_fields,
                    actual=actual_fields,
                )
            return [
                {
                    key: (value.strip() if isinstance(value, str) else value)
                    for key, value in row.items()
                    if key is not None
                }
                for row in reader
            ], schema_matches
    except (OSError, csv.Error) as error:
        add_issue(
            issues,
            "invalid-csv",
            f"{path.name}을 CSV로 읽을 수 없습니다.",
            file=path.name,
            error=str(error),
        )
        return [], False


def duplicate_values(rows, columns):
    counts = Counter(tuple(row.get(column, "") for column in columns) for row in rows)
    return [list(key) for key, count in counts.items() if count > 1]


def binding_has_domain(text, physical_name, domain_id):
    pattern = (
        rf"^\s*-\s+physical_name:\s*{re.escape(physical_name)}\s*$"
        rf"(?P<body>.*?)(?=^\s*-\s+physical_name:|\Z)"
    )
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if match is None:
        return False
    return re.search(
        rf"^\s+domain_id:\s*{re.escape(domain_id)}\s*$",
        match.group("body"),
        re.MULTILINE,
    ) is not None


def canonical_money(value):
    return format(Decimal(value), ".2f")


def infer_as_of_date(argument, feature_rows, issues):
    raw_values = sorted(
        {row.get("as_of_date", "") for row in feature_rows if row.get("as_of_date", "")}
    )
    value = argument or (raw_values[0] if len(raw_values) == 1 else "")

    if not argument and len(raw_values) != 1:
        add_issue(
            issues,
            "ambiguous-as-of-date",
            "feature-sample.csv에서 단 하나의 as_of_date를 결정할 수 없습니다.",
            values=raw_values,
        )
    if argument and raw_values and raw_values != [argument]:
        add_issue(
            issues,
            "as-of-date-mismatch",
            "명령행 기준일과 feature-sample.csv의 기준일이 다릅니다.",
            argument=argument,
            feature_values=raw_values,
        )

    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        add_issue(
            issues,
            "invalid-as-of-date",
            "as_of_date는 ISO 형식이어야 합니다.",
            value=value,
        )
        return None


def validate_source_rows(source_rows, source_schema_checks, issues):
    members = source_rows["members.csv"]
    categories = source_rows["categories.csv"]
    books = source_rows["books.csv"]
    orders = source_rows["orders.csv"]
    order_items = source_rows["order-items.csv"]

    required_values_complete = all(
        all(row.get(field, "") != "" for field in SOURCE_SCHEMAS[file_name])
        for file_name, rows in source_rows.items()
        for row in rows
    )
    if not required_values_complete:
        for file_name, rows in source_rows.items():
            for line_number, row in enumerate(rows, start=2):
                missing = [
                    field
                    for field in SOURCE_SCHEMAS[file_name]
                    if row.get(field, "") == ""
                ]
                if missing:
                    add_issue(
                        issues,
                        "empty-required-value",
                        f"{file_name} {line_number}행에 필수값이 없습니다.",
                        file=file_name,
                        line=line_number,
                        columns=missing,
                    )

    duplicate_keys = {
        "member": duplicate_values(members, ["member_id"]),
        "category": duplicate_values(categories, ["category_code"]),
        "book": duplicate_values(books, ["book_id"]),
        "book_order": duplicate_values(orders, ["order_id"]),
        "order_item": duplicate_values(order_items, ["order_id", "book_id"]),
    }
    primary_keys_unique = not any(duplicate_keys.values())
    if not primary_keys_unique:
        add_issue(
            issues,
            "duplicate-primary-key",
            "정규화 입력에서 PK 또는 복합 PK 중복을 발견했습니다.",
            duplicates=duplicate_keys,
        )

    member_ids = {row.get("member_id", "") for row in members}
    category_codes = {row.get("category_code", "") for row in categories}
    book_ids = {row.get("book_id", "") for row in books}
    order_ids = {row.get("order_id", "") for row in orders}
    foreign_key_violations = []

    for line_number, row in enumerate(books, start=2):
        if row.get("category_code", "") not in category_codes:
            foreign_key_violations.append(
                {
                    "file": "books.csv",
                    "line": line_number,
                    "foreign_key": "category_code",
                    "value": row.get("category_code", ""),
                }
            )
    for line_number, row in enumerate(orders, start=2):
        if row.get("member_id", "") not in member_ids:
            foreign_key_violations.append(
                {
                    "file": "orders.csv",
                    "line": line_number,
                    "foreign_key": "member_id",
                    "value": row.get("member_id", ""),
                }
            )
    for line_number, row in enumerate(order_items, start=2):
        if row.get("order_id", "") not in order_ids:
            foreign_key_violations.append(
                {
                    "file": "order-items.csv",
                    "line": line_number,
                    "foreign_key": "order_id",
                    "value": row.get("order_id", ""),
                }
            )
        if row.get("book_id", "") not in book_ids:
            foreign_key_violations.append(
                {
                    "file": "order-items.csv",
                    "line": line_number,
                    "foreign_key": "book_id",
                    "value": row.get("book_id", ""),
                }
            )
    if foreign_key_violations:
        add_issue(
            issues,
            "foreign-key-violation",
            "정규화 입력의 참조 무결성 위반을 발견했습니다.",
            violations=foreign_key_violations,
        )

    parsed_order_datetimes = {}
    domain_violations = []
    for line_number, row in enumerate(orders, start=2):
        order_id = row.get("order_id", "")
        try:
            parsed_order_datetimes[order_id] = datetime.fromisoformat(
                row.get("order_datetime", "")
            )
        except ValueError:
            domain_violations.append(
                {
                    "file": "orders.csv",
                    "line": line_number,
                    "column": "order_datetime",
                    "value": row.get("order_datetime", ""),
                }
            )
        if row.get("order_status_code", "") not in WRITE_MODEL_STATUSES:
            domain_violations.append(
                {
                    "file": "orders.csv",
                    "line": line_number,
                    "column": "order_status_code",
                    "value": row.get("order_status_code", ""),
                }
            )

    parsed_items = {}
    for line_number, row in enumerate(order_items, start=2):
        key = (row.get("order_id", ""), row.get("book_id", ""))
        try:
            quantity = int(row.get("quantity", ""))
            unit_price = Decimal(row.get("unit_price", ""))
            if not 1 <= quantity <= 999:
                raise ValueError("quantity out of range")
            if not Decimal("0.00") <= unit_price <= Decimal("9999999999.99"):
                raise ValueError("unit_price out of range")
            if unit_price != unit_price.quantize(Decimal("0.01")):
                raise ValueError("unit_price scale overflow")
            parsed_items[key] = (quantity, unit_price)
        except (ValueError, InvalidOperation) as error:
            domain_violations.append(
                {
                    "file": "order-items.csv",
                    "line": line_number,
                    "columns": ["quantity", "unit_price"],
                    "values": [row.get("quantity", ""), row.get("unit_price", "")],
                    "error": str(error),
                }
            )
    if domain_violations:
        add_issue(
            issues,
            "domain-violation",
            "정규화 입력의 날짜·상태·수량·단가 도메인 위반을 발견했습니다.",
            violations=domain_violations,
        )

    counts = {
        "member": len(members),
        "category": len(categories),
        "book": len(books),
        "book_order": len(orders),
        "order_item": len(order_items),
    }
    checks = {
        "source_csv_schemas_match": all(source_schema_checks.values()),
        "source_required_values_complete": required_values_complete,
        "source_primary_keys_are_unique": primary_keys_unique,
        "source_foreign_keys_are_valid": len(foreign_key_violations) == 0,
        "source_domains_are_valid": len(domain_violations) == 0,
        "fixed_fixture_counts_match": counts == EXPECTED_FIXTURE_COUNTS,
    }
    return checks, counts, duplicate_keys, foreign_key_violations, parsed_order_datetimes, parsed_items


def calculate_expected_features(
    source_rows,
    parsed_order_datetimes,
    parsed_items,
    as_of_date,
):
    members = source_rows["members.csv"]
    books = source_rows["books.csv"]
    orders = source_rows["orders.csv"]
    order_items = source_rows["order-items.csv"]
    book_category = {
        row["book_id"]: row["category_code"]
        for row in books
        if row.get("book_id") and row.get("category_code")
    }
    items_by_order = defaultdict(list)
    for row in order_items:
        key = (row.get("order_id", ""), row.get("book_id", ""))
        if key in parsed_items:
            quantity, unit_price = parsed_items[key]
            items_by_order[row["order_id"]].append(
                (row["book_id"], quantity, unit_price)
            )

    window_start = as_of_date - timedelta(days=30)
    orders_by_member = defaultdict(list)
    excluded = {"status": 0, "before_window": 0, "as_of_or_future": 0}
    eligible_order_ids = []
    for row in orders:
        order_datetime = parsed_order_datetimes.get(row.get("order_id", ""))
        if order_datetime is None:
            continue
        if row.get("order_status_code", "") not in FEATURE_STATUSES:
            excluded["status"] += 1
            continue
        if order_datetime < window_start:
            excluded["before_window"] += 1
            continue
        if order_datetime >= as_of_date:
            excluded["as_of_or_future"] += 1
            continue
        orders_by_member[row["member_id"]].append((row, order_datetime))
        eligible_order_ids.append(row["order_id"])

    expected = []
    for member in members:
        member_id = member.get("member_id", "")
        member_orders = orders_by_member.get(member_id, [])
        quantity_sum = 0
        spend_sum = Decimal("0.00")
        category_quantity = Counter()

        for order, _ in member_orders:
            for book_id, quantity, unit_price in items_by_order.get(order["order_id"], []):
                quantity_sum += quantity
                spend_sum += quantity * unit_price
                category_code = book_category.get(book_id, "")
                if category_code:
                    category_quantity[category_code] += quantity

        preferred = ""
        if category_quantity:
            preferred = sorted(
                category_quantity.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]

        last_days = ""
        if member_orders:
            last_datetime = max(value[1] for value in member_orders)
            last_days = str((as_of_date.date() - last_datetime.date()).days)

        expected.append(
            {
                "member_id": member_id,
                "as_of_date": as_of_date.date().isoformat(),
                "order_count_30d": str(len(member_orders)),
                "quantity_sum_30d": str(quantity_sum),
                "spend_sum_30d": format(spend_sum, ".2f"),
                "preferred_category_code_30d": preferred,
                "last_order_days_ago": last_days,
            }
        )

    return expected, sorted(eligible_order_ids), excluded


def validate_feature_rows(feature_rows, category_codes, as_of_date, issues):
    violations = []
    for line_number, row in enumerate(feature_rows, start=2):
        member_id = row.get("member_id", "")
        try:
            order_count = int(row.get("order_count_30d", ""))
            quantity_sum = int(row.get("quantity_sum_30d", ""))
            spend_sum = Decimal(row.get("spend_sum_30d", ""))
            if min(order_count, quantity_sum) < 0 or spend_sum < 0:
                raise ValueError("negative feature value")
            if spend_sum != spend_sum.quantize(Decimal("0.01")):
                raise ValueError("spend_sum_30d scale overflow")
        except (ValueError, InvalidOperation) as error:
            violations.append(
                {
                    "line": line_number,
                    "member_id": member_id,
                    "columns": [
                        "order_count_30d",
                        "quantity_sum_30d",
                        "spend_sum_30d",
                    ],
                    "error": str(error),
                }
            )
            continue

        preferred = row.get("preferred_category_code_30d", "")
        if preferred and (
            preferred not in category_codes
            or re.fullmatch(r"[A-Z][A-Z0-9_-]{0,19}", preferred) is None
        ):
            violations.append(
                {
                    "line": line_number,
                    "member_id": member_id,
                    "column": "preferred_category_code_30d",
                    "value": preferred,
                }
            )

        last_days = row.get("last_order_days_ago", "")
        if last_days:
            try:
                if int(last_days) < 0:
                    raise ValueError("negative last_order_days_ago")
            except ValueError as error:
                violations.append(
                    {
                        "line": line_number,
                        "member_id": member_id,
                        "column": "last_order_days_ago",
                        "value": last_days,
                        "error": str(error),
                    }
                )

        if order_count == 0 and (
            quantity_sum != 0
            or spend_sum != Decimal("0.00")
            or preferred != ""
            or last_days != ""
        ):
            violations.append(
                {
                    "line": line_number,
                    "member_id": member_id,
                    "reason": "zero-order member must have zero totals and null optional features",
                }
            )
        if order_count > 0 and (preferred == "" or last_days == ""):
            violations.append(
                {
                    "line": line_number,
                    "member_id": member_id,
                    "reason": "member with eligible orders needs preferred category and last order days",
                }
            )

        if as_of_date is not None and row.get("as_of_date", "") != as_of_date.date().isoformat():
            violations.append(
                {
                    "line": line_number,
                    "member_id": member_id,
                    "column": "as_of_date",
                    "value": row.get("as_of_date", ""),
                    "expected": as_of_date.date().isoformat(),
                }
            )

    if violations:
        add_issue(
            issues,
            "feature-domain-violation",
            "feature-sample.csv에서 도메인 또는 영(0)건 회원 규칙 위반을 발견했습니다.",
            violations=violations,
        )
    return violations


def compare_feature_rows(actual_rows, expected_rows):
    actual_by_member = {row.get("member_id", ""): row for row in actual_rows}
    expected_by_member = {row["member_id"]: row for row in expected_rows}
    mismatches = []

    for member_id in sorted(set(actual_by_member) | set(expected_by_member)):
        actual = actual_by_member.get(member_id)
        expected = expected_by_member.get(member_id)
        if actual is None or expected is None:
            mismatches.append(
                {"member_id": member_id, "expected": expected, "actual": actual}
            )
            continue
        for field in FEATURE_FIELDS:
            actual_value = actual.get(field, "")
            if field == "spend_sum_30d" and actual_value:
                try:
                    actual_value = canonical_money(actual_value)
                except InvalidOperation:
                    pass
            if actual_value != expected[field]:
                mismatches.append(
                    {
                        "member_id": member_id,
                        "field": field,
                        "expected": expected[field],
                        "actual": actual.get(field, ""),
                    }
                )
    return mismatches


def parse_args():
    parser = argparse.ArgumentParser(
        description="Day 6 feature projection과 표준 카탈로그를 검증합니다."
    )
    parser.add_argument(
        "--input-dir",
        default=str(BASE_DIR),
        help="정규화 입력 CSV가 있는 폴더(기본값: validation.py 폴더)",
    )
    parser.add_argument(
        "--feature-file",
        default="feature-sample.csv",
        help="검증할 feature CSV 이름 또는 경로",
    )
    parser.add_argument(
        "--as-of-date",
        help="기준일(예: 2026-08-12). 생략하면 feature CSV에서 자동 인식",
    )
    parser.add_argument(
        "--output",
        default=str(BASE_DIR / "day6-validation.json"),
        help="검증 JSON 저장 경로",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    feature_path = Path(args.feature_file)
    if not feature_path.is_absolute():
        feature_path = input_dir / feature_path
    output_path = Path(args.output).resolve()

    issues = []
    checks = {}
    missing_artifacts = [
        file_name for file_name in DAY6_ARTIFACTS if not (BASE_DIR / file_name).is_file()
    ]
    missing_inputs = [
        file_name for file_name in SOURCE_SCHEMAS if not (input_dir / file_name).is_file()
    ]
    checks["day6_artifacts_exist"] = len(missing_artifacts) == 0
    checks["normalized_input_files_exist"] = len(missing_inputs) == 0
    if missing_artifacts:
        add_issue(
            issues,
            "missing-day6-artifact",
            "Day 6 필수 산출물이 없습니다.",
            files=missing_artifacts,
        )
    if missing_inputs:
        add_issue(
            issues,
            "missing-normalized-input",
            "feature 생성에 필요한 정규화 입력 CSV가 없습니다.",
            input_dir=str(input_dir),
            files=missing_inputs,
        )

    normalization_report = read_json(DAY5_DIR / "normalization-report.json", issues)
    checks["day5_normalization_is_ready"] = normalization_report.get("status") == "ready"

    schema_text = read_text(DAY5_DIR / "normalized-schema.sql", issues)
    checks["normalized_schema_keeps_five_entity_write_model"] = all(
        token in schema_text
        for token in [
            "CREATE TABLE member",
            "CREATE TABLE category",
            "CREATE TABLE book",
            "CREATE TABLE book_order",
            "CREATE TABLE order_item",
            "PRIMARY KEY",
            "FOREIGN KEY",
        ]
    )

    feature_spec_text = read_text(BASE_DIR / "feature-view-spec.yaml", issues)
    checks["feature_view_spec_matches_30_day_contract"] = all(
        token in feature_spec_text
        for token in [
            "name: member_book_preference_features",
            "entity_key: member_id",
            "as_of_column: as_of_date",
            "window_days: 30",
            "include_start: true",
            "include_as_of: false",
            "- PAID",
            "- SHIPPING",
            "- DONE",
            "tie_breaker: category_code_ascending",
        ]
    )

    extension_text = read_text(BASE_DIR / "feature-standard-extension.yaml", issues)
    checks["feature_terms_are_approved_and_domain_bound"] = (
        "status: approved" in extension_text
        and all(
            binding_has_domain(extension_text, field, domain)
            for field, domain in FEATURE_DOMAINS.items()
        )
    )

    decision_text = read_text(BASE_DIR / "denormalization-decision.md", issues)
    checks["denormalization_decision_has_controls"] = all(
        token in decision_text
        for token in [
            "member_book_preference_features",
            "정규화 쓰기 모델을 정본으로 유지",
            "projection을 사람이 직접 수정하지 않는다",
            "같은 입력과 같은 as_of_date",
            "order_datetime이 as_of_date보다 작은 주문만 사용",
        ]
    )

    catalog_rows, catalog_schema_ok = read_csv_checked(
        BASE_DIR / "db-catalog.csv",
        ["table_name", "column_name", "data_type", "max_length", "nullable"],
        issues,
    )
    catalog_keys = [
        (row.get("table_name", ""), row.get("column_name", "")) for row in catalog_rows
    ]
    catalog_duplicates = [
        list(key) for key, count in Counter(catalog_keys).items() if count > 1
    ]
    catalog_actual = {
        (row.get("table_name", ""), row.get("column_name", "")): (
            row.get("data_type", ""),
            row.get("max_length", ""),
            row.get("nullable", ""),
        )
        for row in catalog_rows
    }
    catalog_mismatches = []
    for key in sorted(set(CATALOG_STANDARD) | set(catalog_actual)):
        if CATALOG_STANDARD.get(key) != catalog_actual.get(key):
            catalog_mismatches.append(
                {
                    "table_name": key[0],
                    "column_name": key[1],
                    "expected": CATALOG_STANDARD.get(key),
                    "actual": catalog_actual.get(key),
                }
            )
    checks["catalog_has_15_unique_standard_columns"] = (
        catalog_schema_ok
        and len(catalog_rows) == 15
        and not catalog_duplicates
        and not catalog_mismatches
    )
    catalog_report = read_json(BASE_DIR / "catalog-standard-check.json", issues)
    checks["catalog_check_report_is_pass"] = (
        catalog_report.get("overall_status") == "PASS"
        and catalog_report.get("checked_column_count") == 15
        and catalog_report.get("pass_count") == 15
        and catalog_report.get("fail_count") == 0
    )

    source_rows = {}
    source_schema_checks = {}
    for file_name, expected_fields in SOURCE_SCHEMAS.items():
        rows, schema_ok = read_csv_checked(input_dir / file_name, expected_fields, issues)
        source_rows[file_name] = rows
        source_schema_checks[file_name] = schema_ok

    (
        source_checks,
        source_counts,
        duplicate_keys,
        foreign_key_violations,
        parsed_order_datetimes,
        parsed_items,
    ) = validate_source_rows(source_rows, source_schema_checks, issues)
    checks.update(source_checks)

    feature_rows, feature_schema_ok = read_csv_checked(feature_path, FEATURE_FIELDS, issues)
    checks["feature_csv_schema_matches"] = feature_schema_ok
    feature_duplicate_grain = duplicate_values(feature_rows, ["member_id", "as_of_date"])
    checks["feature_grain_is_unique"] = len(feature_duplicate_grain) == 0
    if feature_duplicate_grain:
        add_issue(
            issues,
            "duplicate-feature-grain",
            "feature의 (member_id, as_of_date) grain이 중복됩니다.",
            duplicates=feature_duplicate_grain,
        )

    as_of_date = infer_as_of_date(args.as_of_date, feature_rows, issues)
    checks["single_valid_as_of_date"] = as_of_date is not None and all(
        row.get("as_of_date", "") == as_of_date.date().isoformat()
        for row in feature_rows
    )

    category_codes = {
        row.get("category_code", "") for row in source_rows["categories.csv"]
    }
    feature_domain_violations = validate_feature_rows(
        feature_rows,
        category_codes,
        as_of_date,
        issues,
    )
    checks["feature_domains_are_valid"] = len(feature_domain_violations) == 0

    member_ids = {row.get("member_id", "") for row in source_rows["members.csv"]}
    feature_member_ids = {row.get("member_id", "") for row in feature_rows}
    checks["feature_has_one_row_per_member"] = (
        len(feature_rows) == len(member_ids)
        and feature_member_ids == member_ids
        and not feature_duplicate_grain
    )

    source_ready_for_recalculation = all(source_checks.values()) and as_of_date is not None
    expected_features = []
    eligible_order_ids = []
    excluded_orders = {"status": 0, "before_window": 0, "as_of_or_future": 0}
    feature_mismatches = []
    if source_ready_for_recalculation:
        expected_features, eligible_order_ids, excluded_orders = calculate_expected_features(
            source_rows,
            parsed_order_datetimes,
            parsed_items,
            as_of_date,
        )
        feature_mismatches = compare_feature_rows(feature_rows, expected_features)
    checks["feature_values_match_independent_recalculation"] = (
        source_ready_for_recalculation
        and feature_schema_ok
        and not feature_duplicate_grain
        and not feature_domain_violations
        and not feature_mismatches
    )
    checks["time_filter_prevents_future_leakage"] = (
        checks["feature_view_spec_matches_30_day_contract"]
        and checks["feature_values_match_independent_recalculation"]
    )
    checks["empty_member_is_preserved_with_zero_features"] = any(
        row.get("order_count_30d") == "0"
        and row.get("quantity_sum_30d") == "0"
        and row.get("spend_sum_30d") in {"0", "0.0", "0.00"}
        and row.get("preferred_category_code_30d", "") == ""
        and row.get("last_order_days_ago", "") == ""
        for row in feature_rows
    )

    if feature_mismatches:
        add_issue(
            issues,
            "feature-value-mismatch",
            "feature-sample.csv가 정규화 입력의 독립 재계산 결과와 다릅니다.",
            mismatch_count=len(feature_mismatches),
            samples=feature_mismatches[:20],
        )

    failed_checks = [name for name, passed in checks.items() if not passed]
    status = "ready" if not failed_checks and not issues else "blocked"
    report = {
        "day": 6,
        "status": status,
        "as_of_date": as_of_date.date().isoformat() if as_of_date else None,
        "checks": checks,
        "evidence": {
            "input_dir": str(input_dir),
            "feature_file": str(feature_path),
            "day5_normalization_report": str(DAY5_DIR / "normalization-report.json"),
            "day5_normalized_schema": str(DAY5_DIR / "normalized-schema.sql"),
            "missing_artifacts": missing_artifacts,
            "missing_inputs": missing_inputs,
            "source_counts": source_counts,
            "expected_source_counts": EXPECTED_FIXTURE_COUNTS,
            "duplicate_source_keys": duplicate_keys,
            "foreign_key_violations": foreign_key_violations,
            "catalog_duplicate_columns": catalog_duplicates,
            "catalog_mismatches": catalog_mismatches,
            "eligible_order_ids": eligible_order_ids,
            "excluded_order_counts": excluded_orders,
            "feature_row_count": len(feature_rows),
            "expected_feature_row_count": len(member_ids),
            "feature_mismatches": feature_mismatches[:20],
            "failed_checks": failed_checks,
            "issues": issues,
        },
        "artifacts": DAY6_ARTIFACTS + [output_path.name],
        "next_day": {
            "day": 7,
            "ready_input": "feature-sample.csv",
            "grain": "one row per member_id and as_of_date",
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"{status.upper()}: {output_path.name}")
    for check_name, passed in checks.items():
        print(f"- {check_name}: {'PASS' if passed else 'FAIL'}")
    if failed_checks:
        print("failed_checks=" + ", ".join(failed_checks))
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
