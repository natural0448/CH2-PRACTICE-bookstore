import csv
import json
from pathlib import Path
from collections import Counter

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