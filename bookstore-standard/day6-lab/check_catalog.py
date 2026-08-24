import csv
import json
from pathlib import Path


STANDARD_COLUMNS = {
    "member_id": {"data_type": "VARCHAR", "max_length": "20", "nullable": "N"},
    "member_name": {"data_type": "VARCHAR", "max_length": "100", "nullable": "N"},
    "book_id": {"data_type": "VARCHAR", "max_length": "20", "nullable": "N"},
    "book_name": {"data_type": "VARCHAR", "max_length": "200", "nullable": "N"},
    "category_code": {"data_type": "VARCHAR", "max_length": "20", "nullable": "N"},
    "category_name": {"data_type": "VARCHAR", "max_length": "100", "nullable": "N"},
    "order_id": {"data_type": "VARCHAR", "max_length": "20", "nullable": "N"},
    "order_datetime": {"data_type": "DATETIME", "max_length": "", "nullable": "N"},
    "order_status_code": {"data_type": "VARCHAR", "max_length": "20", "nullable": "N"},
    "quantity": {"data_type": "INTEGER", "max_length": "", "nullable": "N"},
    "unit_price": {"data_type": "DECIMAL", "max_length": "12", "nullable": "N"},
}


def read_catalog(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def check_row(row):
    column_name = row["column_name"]
    standard = STANDARD_COLUMNS.get(column_name)

    if standard is None:
        return {
            "table_name": row["table_name"],
            "column_name": column_name,
            "status": "FAIL",
            "reason": "standard_term_not_found",
        }

    differences = []
    for field in ["data_type", "max_length", "nullable"]:
        if row[field] != standard[field]:
            differences.append(
                {
                    "field": field,
                    "catalog_value": row[field],
                    "standard_value": standard[field],
                }
            )

    if differences:
        return {
            "table_name": row["table_name"],
            "column_name": column_name,
            "status": "FAIL",
            "reason": "domain_mismatch",
            "differences": differences,
        }

    return {
        "table_name": row["table_name"],
        "column_name": column_name,
        "status": "PASS",
        "reason": "matched",
    }


def main():
    catalog_path = Path("db-catalog.csv")
    output_path = Path("catalog-standard-check.json")
    catalog_rows = read_catalog(catalog_path)
    results = [check_row(row) for row in catalog_rows]
    failed = [row for row in results if row["status"] == "FAIL"]

    report = {
        "catalog_file": catalog_path.name,
        "checked_column_count": len(results),
        "pass_count": len(results) - len(failed),
        "fail_count": len(failed),
        "overall_status": "PASS" if not failed else "FAIL",
        "results": results,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(f"checked={report['checked_column_count']}")
    print(f"failed={report['fail_count']}")
    print(f"status={report['overall_status']}")


if __name__ == "__main__":
    main()