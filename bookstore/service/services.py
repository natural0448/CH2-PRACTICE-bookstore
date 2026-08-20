import csv
import json
from pathlib import Path
from collections import Counter
from decimal import Decimal


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
