import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path


OUTPUT_FIELDS = [
    "member_id",
    "as_of_date",
    "order_count_30d",
    "quantity_sum_30d",
    "spend_sum_30d",
    "preferred_category_code_30d",
    "last_order_days_ago",
]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_datetime(value):
    return datetime.fromisoformat(value)


def choose_preferred_category(category_quantity):
    if not category_quantity:
        return ""

    ranked = sorted(
        category_quantity.items(),
        key=lambda item: (-item[1], item[0]),
    )
    return ranked[0][0]


def build_features(input_dir, as_of_date):
    members = read_csv(input_dir / "members.csv")
    books = read_csv(input_dir / "books.csv")
    orders = read_csv(input_dir / "orders.csv")
    order_items = read_csv(input_dir / "order-items.csv")

    book_category = {
        row["book_id"]: row["category_code"]
        for row in books
    }
    items_by_order = defaultdict(list)
    for row in order_items:
        items_by_order[row["order_id"]].append(row)

    window_start = as_of_date - timedelta(days=30)
    eligible_orders = []
    for row in orders:
        order_datetime = parse_datetime(row["order_datetime"])
        is_allowed_status = row["order_status_code"] in {
            "PAID",
            "SHIPPING",
            "DONE",
        }
        is_in_window = window_start <= order_datetime < as_of_date

        if is_allowed_status and is_in_window:
            copied = dict(row)
            copied["_parsed_order_datetime"] = order_datetime
            eligible_orders.append(copied)

    orders_by_member = defaultdict(list)
    for row in eligible_orders:
        orders_by_member[row["member_id"]].append(row)

    results = []
    for member in members:
        member_id = member["member_id"]
        member_orders = orders_by_member.get(member_id, [])
        quantity_sum = 0
        spend_sum = Decimal("0.00")
        category_quantity = Counter()

        for order in member_orders:
            for item in items_by_order.get(order["order_id"], []):
                quantity = int(item["quantity"])
                unit_price = Decimal(item["unit_price"])
                category_code = book_category[item["book_id"]]

                quantity_sum += quantity
                spend_sum += quantity * unit_price
                category_quantity[category_code] += quantity

        if member_orders:
            last_order_datetime = max(
                row["_parsed_order_datetime"]
                for row in member_orders
            )
            last_order_days_ago = (
                as_of_date.date() - last_order_datetime.date()
            ).days
        else:
            last_order_days_ago = ""

        results.append(
            {
                "member_id": member_id,
                "as_of_date": as_of_date.date().isoformat(),
                "order_count_30d": len(member_orders),
                "quantity_sum_30d": quantity_sum,
                "spend_sum_30d": format(spend_sum, ".2f"),
                "preferred_category_code_30d": choose_preferred_category(
                    category_quantity
                ),
                "last_order_days_ago": last_order_days_ago,
            }
        )

    return results


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=".")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--output", default="feature-sample.csv")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    as_of_date = datetime.fromisoformat(args.as_of_date)
    output_path = Path(args.output)

    rows = build_features(input_dir, as_of_date)
    write_csv(output_path, rows)

    print(f"feature_rows={len(rows)}")
    print(f"as_of_date={as_of_date.date().isoformat()}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()