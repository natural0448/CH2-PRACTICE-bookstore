import csv
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import DecimalField, ExpressionWrapper, F
from bookstore.repository.models import OrderItem
from django.db import connection


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
