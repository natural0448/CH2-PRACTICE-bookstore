import csv
import io
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.db.models import DecimalField, ExpressionWrapper, F
from bookstore.repository.models import OrderItem
from django.db import connection
import hashlib


import yaml
from django.conf import settings


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def get_bookstore_standard_context():
    data_dir = Path(settings.BASE_DIR) / "bookstore-standard" / "day2"

    words = read_csv(data_dir / "standard-words.csv")
    terms = read_csv(data_dir / "standard-terms.csv")

    with (data_dir / "data-domains.yaml").open(encoding="utf-8") as file:
        domains = yaml.safe_load(file)["domains"]

    with (data_dir / "day2-validation.json").open(encoding="utf-8") as file:
        validation = json.load(file)

    unit_price = next(
        (term for term in terms if term["term_id"] == "UNIT_PRICE"),
        None,
    )

    context = {
        "validation": validation,
        "counts": {
            "words": len(words),
            "domains": len(domains),
            "terms": len(terms),
        },
        "terms": terms,
        "domains": domains,
        "unit_price": unit_price,
    }
    return context

def get_bookstore_Standardizated_data():
    data_dir = Path(settings.BASE_DIR) / "bookstore-standard" / "day3"

    standardized_rows = read_csv(data_dir / "standardized-orders.csv")
    rejected_rows = read_csv(data_dir / "rejected-orders.csv")

    with (data_dir / "profile-report.json").open(encoding="utf-8") as file:
        profile = json.load(file)

    with (data_dir / "day3-validation.json").open(encoding="utf-8") as file:
        validation = json.load(file)

    context = {
        "profile": profile,
        "validation": validation,
        "counts": {
            "standardized": len(standardized_rows),
            "rejected": len(rejected_rows),
            "total": len(standardized_rows) + len(rejected_rows),
        },
        "status_counts": dict(
            Counter(row["order_status_code"] for row in standardized_rows)
        ),
        "rejection_counts": dict(
            Counter(row["rejection_reason"] for row in rejected_rows)
        ),
        "standardized_rows": standardized_rows,
        "rejected_rows": rejected_rows,
    }
    return context


def get_bookstore_Standard_enterty():
    """Day 4 엔터티 결정 결과를 대시보드 context로 반환합니다."""
    data_dir = Path(settings.BASE_DIR) / "bookstore-standard" / "day4"

    order_rows = read_csv(data_dir / "standardized-orders.csv")
    rejected_rows = read_csv(data_dir / "rejected-orders.csv")
    entity_rows = read_csv(data_dir / "entity-candidates.csv")
    identifier_rows = read_csv(data_dir / "identifier-decisions.csv")

    with (data_dir / "day4-validation.json").open(encoding="utf-8") as file:
        validation = json.load(file)

    entity_order = ["member", "category", "book", "order", "order-item"]
    expected_counts = {
        "member": 4,
        "category": 3,
        "book": 5,
        "order": 5,
        "order-item": 6,
    }
    entities_by_id = {row["entity_id"]: row for row in entity_rows}
    entity_rows = [entities_by_id[entity_id] for entity_id in entity_order]

    selected_identifiers = {
        row["entity_id"]: row
        for row in identifier_rows
        if row["selected"].strip().upper() == "Y"
    }

    count_rows = []
    for entity in entity_rows:
        entity_id = entity["entity_id"]
        identifier = selected_identifiers[entity_id]
        identifier_columns = identifier["candidate_columns"].split("|")

        distinct_keys = {
            tuple(row[column] for column in identifier_columns)
            for row in order_rows
        }
        actual_count = len(distinct_keys)
        expected_count = expected_counts[entity_id]
        count_rows.append(
    {
        "entity_id": entity_id,
        "logical_name": entity["logical_name"],
        "identifier": " + ".join(identifier_columns),
        "grain": entity["grain"],
        "count": actual_count,
        "expected_count": expected_count,
        "matches": actual_count == expected_count,
    }
)

    order_amount = sum(
        (
            Decimal(row["quantity"]) * Decimal(row["unit_price"])
            for row in order_rows
        ),
        Decimal("0"),
    )

    context = {
        "validation": validation,
        "standardized_count": len(order_rows),
        "rejected_count": len(rejected_rows),
        "entity_rows": entity_rows,
        "count_rows": count_rows,
        "order_amount": order_amount,
    }
    return context

def get_day5_orm_dashboard():
    line_amount = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    items = (
        OrderItem.objects
        .select_related("order__member", "book__category")
        .annotate(line_amount=line_amount)
        .order_by("order_id", "book_id")
    )
    rows = [
        {
            "order_id": item.order_id,
            "member_name": item.order.member.member_name,
            "book_name": item.book.book_name,
            "category_name": item.book.category.category_name,
            "order_status_code": item.order.order_status_code,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_amount": item.line_amount,
        }
        for item in items
    ]
    return {
        "query_mode": "Django ORM",
        "rows": rows,
        "row_count": len(rows),
        "total_amount": sum(
            (row["line_amount"] for row in rows),
            Decimal("0.00"),
        ),
    }



def get_day5_raw_dashboard():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                o.order_id,
                m.member_name,
                b.book_name,
                c.category_name,
                o.order_status_code,
                oi.quantity,
                oi.unit_price,
                oi.quantity * oi.unit_price AS line_amount
            FROM order_item AS oi
            JOIN book_order AS o ON o.order_id = oi.order_id
            JOIN member AS m ON m.member_id = o.member_id
            JOIN book AS b ON b.book_id = oi.book_id
            JOIN category AS c ON c.category_code = b.category_code
            ORDER BY o.order_id, b.book_id
            """
        )
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return {
        "query_mode": "Raw Query",
        "rows": rows,
        "row_count": len(rows),
        "total_amount": sum(
            (row["line_amount"] for row in rows),
            Decimal("0.00"),
        ),
    }

def get_day6_feature_dashboard_context(as_of_date="2026-08-12"):
    """선택한 기준일로 Day 6 회원 feature를 다시 계산한다."""
    data_dir = Path(settings.BASE_DIR) / "day6-lab"

    try:
        selected_date = datetime.strptime(as_of_date, "%Y-%m-%d")
    except ValueError:
        selected_date = datetime.strptime("2026-08-12", "%Y-%m-%d")

    members = read_csv(data_dir / "members.csv")
    books = read_csv(data_dir / "books.csv")
    orders = read_csv(data_dir / "orders.csv")
    order_items = read_csv(data_dir / "order-items.csv")

    book_category = {
        row["book_id"]: row["category_code"]
        for row in books
    }
    items_by_order = defaultdict(list)
    for row in order_items:
        items_by_order[row["order_id"]].append(row)

    window_start = selected_date - timedelta(days=30)
    orders_by_member = defaultdict(list)
    for row in orders:
        order_datetime = datetime.fromisoformat(row["order_datetime"])
        if (
            row["order_status_code"] in {"PAID", "SHIPPING", "DONE"}
            and window_start <= order_datetime < selected_date
        ):
            orders_by_member[row["member_id"]].append(
                (row, order_datetime)
            )

    features = []
    for member in members:
        member_orders = orders_by_member.get(member["member_id"], [])
        quantity_sum = 0
        spend_sum = Decimal("0.00")
        category_quantity = Counter()

        for order, _ in member_orders:
            for item in items_by_order.get(order["order_id"], []):
                quantity = int(item["quantity"])
                unit_price = Decimal(item["unit_price"])
                category_code = book_category[item["book_id"]]

                quantity_sum += quantity
                spend_sum += quantity * unit_price
                category_quantity[category_code] += quantity

        preferred_category = ""
        if category_quantity:
            preferred_category = sorted(
                category_quantity.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0]

        last_order_days_ago = ""
        if member_orders:
            last_order_datetime = max(
                order_datetime
                for _, order_datetime in member_orders
            )
            last_order_days_ago = (
                selected_date.date() - last_order_datetime.date()
            ).days

        features.append(
            {
                "member_id": member["member_id"],
                "as_of_date": selected_date.date().isoformat(),
                "order_count_30d": len(member_orders),
                "quantity_sum_30d": quantity_sum,
                "spend_sum_30d": spend_sum,
                "preferred_category_code_30d": preferred_category,
                "last_order_days_ago": last_order_days_ago,
            }
        )

    with (data_dir / "catalog-standard-check.json").open(
        encoding="utf-8",
    ) as file:
        catalog_report = json.load(file)

    future_leak_count = sum(
        order_datetime >= selected_date
        for member_orders in orders_by_member.values()
        for _, order_datetime in member_orders
    )
    dashboard_pass = (
        len(features) == len(members)
        and future_leak_count == 0
        and catalog_report.get("overall_status") == "PASS"
        and catalog_report.get("fail_count") == 0
    )

    return {
        "features": features,
        "as_of_date": selected_date.date().isoformat(),
        "feature_row_count": len(features),
        "future_leak_count": future_leak_count,
        "catalog_report": catalog_report,
        "dashboard_pass": dashboard_pass,
    }


def get_day7_quality_dashboard_context():
    """Day 7 표준 카탈로그와 품질 결과를 화면 context로 만든다."""
    data_dir = (
        Path(settings.BASE_DIR) / "bookstore-standard" / "day7"
    )

    catalog_rows = read_csv(data_dir / "standardized-catalog.csv")
    with (data_dir / "quality-report.json").open(
        encoding="utf-8",
    ) as file:
        quality_report = json.load(file)

    dimensions = [
        {"name": name, **result}
        for name, result in quality_report["dimensions"].items()
    ]
    catalog_pass = (
        len(catalog_rows) == 7
        and all(
            row["translation_status"] == "MAPPED"
            for row in catalog_rows
        )
    )
    quality_pass = (
        quality_report.get("row_count") == 4
        and quality_report.get("overall_status") == "PASS"
        and quality_report.get("summary", {}).get("pass_count") == 5
        and quality_report.get("summary", {}).get("fail_count") == 0
    )

    return {
        "catalog_rows": catalog_rows,
        "catalog_row_count": len(catalog_rows),
        "feature_row_count": quality_report.get("row_count", 0),
        "dimensions": dimensions,
        "quality_report": quality_report,
        "dashboard_pass": catalog_pass and quality_pass,
    }

DAY7_FEATURE_COLUMNS = [
    "member_id",
    "as_of_date",
    "order_count_30d",
    "quantity_sum_30d",
    "spend_sum_30d",
    "preferred_category_code_30d",
    "last_order_days_ago",
]
DAY7_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
DAY7_PREVIEW_LIMIT = 10
DAY7_ISSUE_LIMIT = 100
DAY7_SUPPORTED_EXTENSIONS = {
    ".csv": "CSV",
    ".json": "JSON",
    ".ndjson": "NDJSON",
}



def get_day7_inquality_dashboard_context(uploaded_file=None):
    """업로드된 Day 7 feature 데이터를 저장하지 않고 품질 검사한다."""
    context = {
        "upload_ready": uploaded_file is None,
        "upload_error": "",
        "report": None,
        "max_upload_mb": DAY7_UPLOAD_MAX_BYTES // (1024 * 1024),
        "expected_columns": DAY7_FEATURE_COLUMNS,
        "supported_formats": list(DAY7_SUPPORTED_EXTENSIONS.values()),
    }
    if uploaded_file is None:
        return context

    file_name = Path(uploaded_file.name).name
    extension = Path(file_name).suffix.lower()
    if extension not in DAY7_SUPPORTED_EXTENSIONS:
        context["upload_error"] = (
            "CSV(.csv), JSON(.json), NDJSON(.ndjson) 파일만 검사할 수 있습니다."
        )
        return context
    if uploaded_file.size > DAY7_UPLOAD_MAX_BYTES:
        context["upload_error"] = (
            f"파일 크기는 {context['max_upload_mb']}MB 이하여야 합니다."
        )
        return context

    raw_data = uploaded_file.read(DAY7_UPLOAD_MAX_BYTES + 1)
    if len(raw_data) > DAY7_UPLOAD_MAX_BYTES:
        context["upload_error"] = (
            f"파일 크기는 {context['max_upload_mb']}MB 이하여야 합니다."
        )
        return context
    try:
        text = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError:
        context["upload_error"] = (
            "데이터 파일은 UTF-8 또는 UTF-8 BOM 인코딩이어야 합니다."
        )
        return context

    try:
        actual_columns, rows, row_numbers = _parse_uploaded_rows(
            extension,
            text,
        )
    except (csv.Error, ValueError) as error:
        context["upload_error"] = f"파일 형식을 읽을 수 없습니다: {error}"
        return context

    issue_rows = []
    total_issue_count = 0

    def add_issue(check, row_number, column, value, message):
        nonlocal total_issue_count
        total_issue_count += 1
        if len(issue_rows) < DAY7_ISSUE_LIMIT:
            issue_rows.append(
                {
                    "check": check,
                    "row_number": row_number,
                    "column": column,
                    "value": value,
                    "message": message,
                }
            )

    checks = []

    def add_check(key, label, issue_count, message):
        checks.append(
            {
                "key": key,
                "label": label,
                "status": "PASS" if issue_count == 0 else "FAIL",
                "issue_count": issue_count,
                "message": message,
            }
        )

    schema_before = total_issue_count
    if actual_columns != DAY7_FEATURE_COLUMNS:
        missing = [
            column for column in DAY7_FEATURE_COLUMNS
            if column not in actual_columns
        ]
        unexpected = [
            column for column in actual_columns
            if column not in DAY7_FEATURE_COLUMNS
        ]
        details = []
        if missing:
            details.append(f"누락: {', '.join(missing)}")
        if unexpected:
            details.append(f"예상 외: {', '.join(unexpected)}")
        if not missing and not unexpected:
            details.append("컬럼 순서가 표준 계약과 다름")
        add_issue(
            "스키마", "헤더", "전체", ", ".join(actual_columns),
            "; ".join(details),
        )
    for row_number, row in zip(row_numbers, rows):
        if None in row:
            add_issue(
                "스키마", row_number, "전체", row.get(None),
                "헤더보다 많은 필드가 있습니다.",
            )
    schema_count = total_issue_count - schema_before
    add_check(
        "schema", "스키마", schema_count,
        "Day 7 표준 컬럼 7개의 이름과 순서를 검사합니다.",
    )

    has_contract = all(
        column in actual_columns for column in DAY7_FEATURE_COLUMNS
    )
    completeness_before = total_issue_count
    if len(rows) != 4:
        add_issue(
            "완전성", "전체", "행 수", len(rows),
            "표준 fixture 행 수는 4개입니다.",
        )
    if has_contract:
        for row_number, row in zip(row_numbers, rows):
            for column in DAY7_FEATURE_COLUMNS[:5]:
                if (row.get(column) or "").strip() == "":
                    add_issue(
                        "완전성", row_number, column, "",
                        "필수값이 비어 있습니다.",
                    )
            order_count = _safe_decimal(row.get("order_count_30d"))
            optional_values = [
                (row.get(column) or "").strip()
                for column in (
                    "preferred_category_code_30d",
                    "last_order_days_ago",
                )
            ]
            if order_count == 0 and any(optional_values):
                add_issue(
                    "완전성", row_number, "조건부 NULL",
                    " | ".join(optional_values),
                    "주문 수가 0이면 두 선택 컬럼은 비어 있어야 합니다.",
                )
            elif (
                order_count is not None
                and order_count > 0
                and not all(optional_values)
            ):
                add_issue(
                    "완전성", row_number, "조건부 NULL",
                    " | ".join(optional_values),
                    "주문 수가 1 이상이면 두 선택 컬럼이 모두 필요합니다.",
                )
    completeness_count = total_issue_count - completeness_before
    add_check(
        "completeness", "완전성", completeness_count,
        "행 수, 필수값, 조건부 NULL 규칙을 검사합니다.",
    )

    uniqueness_before = total_issue_count
    if has_contract:
        key_counter = Counter(
            (
                (row.get("member_id") or ""),
                (row.get("as_of_date") or ""),
            )
            for row in rows
        )
        for key, count in key_counter.items():
            if count > 1:
                add_issue(
                    "유일성", "전체", "member_id + as_of_date",
                    " + ".join(key), f"동일 키가 {count}번 나타납니다.",
                )
    uniqueness_count = total_issue_count - uniqueness_before
    add_check(
        "uniqueness", "유일성", uniqueness_count,
        "member_id와 as_of_date 복합키 중복을 검사합니다.",
    )

    validity_before = total_issue_count
    integer_columns = [
        "order_count_30d", "quantity_sum_30d", "last_order_days_ago",
    ]
    numeric_columns = integer_columns + ["spend_sum_30d"]
    if has_contract:
        for row_number, row in zip(row_numbers, rows):
            try:
                date.fromisoformat((row.get("as_of_date") or "").strip())
            except ValueError:
                add_issue(
                    "유효성", row_number, "as_of_date",
                    row.get("as_of_date", ""),
                    "YYYY-MM-DD 날짜 형식이 아닙니다.",
                )
            for column in numeric_columns:
                value = (row.get(column) or "").strip()
                if column == "last_order_days_ago" and value == "":
                    continue
                number = _safe_decimal(value)
                if number is None:
                    add_issue(
                        "유효성", row_number, column, value,
                        "숫자로 변환할 수 없습니다.",
                    )
                elif number < 0:
                    add_issue(
                        "유효성", row_number, column, value,
                        "0보다 작을 수 없습니다.",
                    )
                elif (
                    column in integer_columns
                    and number != number.to_integral_value()
                ):
                    add_issue(
                        "유효성", row_number, column, value,
                        "정수여야 합니다.",
                    )
            order_count = _safe_decimal(row.get("order_count_30d"))
            quantity_sum = _safe_decimal(row.get("quantity_sum_30d"))
            spend_sum = _safe_decimal(row.get("spend_sum_30d"))
            if order_count == 0 and (
                quantity_sum != 0 or spend_sum != 0
            ):
                add_issue(
                    "유효성", row_number, "0건 일관성",
                    f"{quantity_sum} | {spend_sum}",
                    "주문 수가 0이면 수량과 금액 합계도 0이어야 합니다.",
                )
    validity_count = total_issue_count - validity_before
    add_check(
        "validity", "유효성", validity_count,
        "날짜, 숫자, 음수, 정수형과 0건 일관성을 검사합니다.",
    )

    reference_before = total_issue_count
    if has_contract:
        reference_rows = read_csv(
            Path(settings.BASE_DIR)
            / "bookstore-standard" / "day3" / "standardized-orders.csv"
        )
        known_members = {row["member_id"] for row in reference_rows}
        known_categories = {
            row["category_code"] for row in reference_rows
        }
        for row_number, row in zip(row_numbers, rows):
            member_id = (row.get("member_id") or "").strip()
            category_code = (
                row.get("preferred_category_code_30d") or ""
            ).strip()
            if member_id and member_id not in known_members:
                add_issue(
                    "참조 무결성", row_number, "member_id", member_id,
                    "Day 3 회원 기준에 존재하지 않습니다.",
                )
            if category_code and category_code not in known_categories:
                add_issue(
                    "참조 무결성", row_number,
                    "preferred_category_code_30d", category_code,
                    "Day 3 카테고리 기준에 존재하지 않습니다.",
                )
    reference_count = total_issue_count - reference_before
    add_check(
        "referential_integrity", "참조 무결성", reference_count,
        "Day 3 회원·카테고리 기준값과 대조합니다.",
    )

    point_before = total_issue_count
    expected_as_of_date = "2026-08-12"
    if has_contract:
        expected_counts = _expected_day7_order_counts(
            expected_as_of_date
        )
        for row_number, row in zip(row_numbers, rows):
            member_id = (row.get("member_id") or "").strip()
            as_of_date = (row.get("as_of_date") or "").strip()
            if as_of_date != expected_as_of_date:
                add_issue(
                    "시점 무결성", row_number, "as_of_date", as_of_date,
                    f"기준일은 {expected_as_of_date}여야 합니다.",
                )
            actual_count = _safe_decimal(row.get("order_count_30d"))
            expected_count = expected_counts.get(
                member_id, Decimal("0")
            )
            if (
                actual_count is not None
                and actual_count != expected_count
            ):
                add_issue(
                    "시점 무결성", row_number, "order_count_30d",
                    actual_count,
                    f"기준 원천으로 계산한 값은 {expected_count}입니다.",
                )
    point_count = total_issue_count - point_before
    add_check(
        "point_in_time", "시점 무결성", point_count,
        "기준일과 최근 30일 주문 수를 원천 데이터와 대조합니다.",
    )

    is_standardized = all(
        check["status"] == "PASS" for check in checks
    )
    context["upload_ready"] = False
    context["report"] = {
        "file_name": file_name,
        "status": "PASS" if is_standardized else "FAIL",
        "file_format": DAY7_SUPPORTED_EXTENSIONS[extension],
        "is_standardized": is_standardized,
        "row_count": len(rows),
        "column_count": len(actual_columns),
        "actual_columns": actual_columns,
        "checks": checks,
        "pass_count": sum(
            check["status"] == "PASS" for check in checks
        ),
        "fail_count": sum(
            check["status"] == "FAIL" for check in checks
        ),
        "issue_count": total_issue_count,
        "issues": issue_rows,
        "issues_truncated": total_issue_count > len(issue_rows),
        "preview_columns": actual_columns,
        "preview_rows": [
            {
                column: row.get(column, "")
                for column in actual_columns
            }
            for row in rows[:DAY7_PREVIEW_LIMIT]
        ],
    }
    return context


def _safe_decimal(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _parse_uploaded_rows(extension, text):
    if extension == ".csv":
        reader = csv.DictReader(io.StringIO(text, newline=""))
        rows = list(reader)
        row_numbers = list(range(2, len(rows) + 2))
        return reader.fieldnames or [], rows, row_numbers

    if extension == ".json":
        records = json.loads(
            text,
            parse_float=Decimal,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(records, list):
            raise ValueError("JSON 최상위 값은 객체 배열이어야 합니다.")
        row_numbers = list(range(1, len(records) + 1))
        return _normalize_json_records(records, row_numbers)

    records = []
    row_numbers = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(
                line,
                parse_float=Decimal,
                parse_constant=_reject_json_constant,
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                f"NDJSON {line_number}번째 줄 오류: {error.msg}"
            ) from error
        records.append(record)
        row_numbers.append(line_number)
    return _normalize_json_records(records, row_numbers)


def _reject_json_constant(value):
    raise ValueError(f"JSON에서 {value} 값은 사용할 수 없습니다.")


def _normalize_json_records(records, row_numbers):
    columns = []
    normalized_rows = []
    for row_number, record in zip(row_numbers, records):
        if not isinstance(record, dict):
            raise ValueError(
                f"{row_number}번째 데이터는 JSON 객체여야 합니다."
            )

        normalized = {}
        for column, value in record.items():
            if column not in columns:
                columns.append(column)
            if isinstance(value, (dict, list)):
                raise ValueError(
                    f"{row_number}번째 데이터의 {column}은 중첩 값입니다."
                )
            if value is None:
                normalized[column] = ""
            elif isinstance(value, Decimal):
                normalized[column] = format(value, "f")
            elif isinstance(value, bool):
                normalized[column] = str(value).lower()
            else:
                normalized[column] = str(value)
        normalized_rows.append(normalized)

    return columns, normalized_rows, row_numbers


def _expected_day7_order_counts(as_of_date):
    selected_date = datetime.strptime(as_of_date, "%Y-%m-%d")
    window_start = selected_date - timedelta(days=30)
    source_rows = read_csv(
        Path(settings.BASE_DIR)
        / "bookstore-standard" / "day3" / "standardized-orders.csv"
    )
    order_ids = defaultdict(set)
    for row in source_rows:
        order_datetime = datetime.fromisoformat(row["order_datetime"])
        if (
            row["order_status_code"] in {"PAID", "SHIPPING", "DONE"}
            and window_start <= order_datetime < selected_date
        ):
            order_ids[row["member_id"]].add(row["order_id"])
    return {
        member_id: Decimal(len(ids))
        for member_id, ids in order_ids.items()
    }


def get_day8_release_dashboard_context():
    """Day 8 release의 수치와 checksum을 화면 context로 만든다."""
    release_dir = (
        Path(settings.BASE_DIR)
        / "day8-lab"
        / "release"
    )

    with (release_dir / "dataset-manifest.json").open(
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    with (release_dir / "quality-report.json").open(
        encoding="utf-8",
    ) as file:
        quality_report = json.load(file)

    with (release_dir / "day8-validation.json").open(
        encoding="utf-8",
    ) as file:
        validation = json.load(file)

    training_info = manifest["files"]["training"]
    training_path = release_dir / training_info["path"]
    actual_checksum = hashlib.sha256(
        training_path.read_bytes()
    ).hexdigest()
    checksum_match = actual_checksum == training_info["sha256"]

    counts = manifest["counts"]
    dashboard_pass = (
        manifest.get("dataset_version") == "2026-08-14-v1"
        and counts.get("ai_ready_row_count") == 2
        and counts.get("eligibility_exclusion_count") == 2
        and counts.get("source_quality_failure_count") == 0
        and manifest.get("release_status") == "PASS_WITH_QUARANTINE"
        and quality_report.get("overall_status")
        == "PASS_WITH_QUARANTINE"
        and validation.get("status") == "READY_FOR_DJANGO"
        and checksum_match
    )

    return {
        "manifest": manifest,
        "counts": counts,
        "quality_report": quality_report,
        "validation": validation,
        "expected_checksum": training_info["sha256"],
        "actual_checksum": actual_checksum,
        "checksum_match": checksum_match,
        "dashboard_pass": dashboard_pass,
    }