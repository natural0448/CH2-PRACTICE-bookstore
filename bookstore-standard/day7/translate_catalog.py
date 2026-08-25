import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from catalog_gap import (
    COLUMN_CONTRACTS,
    EXPECTED_FEATURE_COLUMNS,
    STANDARD_TABLE_NAME,
    validate_feature_contract,
)


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DAY2_DIR = ROOT_DIR / "day2"
DAY3_DIR = ROOT_DIR / "day3"
DAY5_DIR = ROOT_DIR / "day5"
DAY6_DIR = BASE_DIR.parents[1] / "day6-lab"

AS_IS_CATALOG = BASE_DIR / "as-is-catalog.csv"
QUALITY_RULES = BASE_DIR / "quality-rules.yaml"
GAP_REPORT = BASE_DIR / "catalog-gap-report.json"
STANDARDIZED_CATALOG = BASE_DIR / "standardized-catalog.csv"
QUALITY_REPORT = BASE_DIR / "quality-report.json"
VALIDATION_REPORT = BASE_DIR / "day7-validation.json"

STANDARDIZED_CATALOG_FIELDS = [
    "source_table_name",
    "source_column_name",
    "standard_table_name",
    "standard_column_name",
    "logical_name",
    "word_ids",
    "domain_id",
    "data_type",
    "max_length",
    "nullable",
    "translation_status",
]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames or [], list(reader)


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path, document):
    with path.open("w", encoding="utf-8") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_yaml(path):
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def resolve_rule_path(path_value):
    path = Path(path_value)
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def require_cumulative_inputs(rules, rules_path):
    dimension_rules = rules["dimensions"]
    configured_sources = [
        resolve_rule_path(rules["dataset"]["source_file"]),
        resolve_rule_path(
            dimension_rules["referential_integrity"]["member_reference"][
                "source_file"
            ]
        ),
        resolve_rule_path(
            dimension_rules["referential_integrity"]["category_reference"][
                "source_file"
            ]
        ),
        resolve_rule_path(dimension_rules["point_in_time"]["source_file"]),
    ]
    required = [
        DAY2_DIR / "legacy-columns.csv",
        DAY2_DIR / "standard-words.csv",
        DAY2_DIR / "standard-terms.csv",
        DAY2_DIR / "naming-rules.yaml",
        DAY2_DIR / "data-domains.yaml",
        DAY2_DIR / "day2-validation.json",
        DAY3_DIR / "profile-report.json",
        DAY3_DIR / "column-mapping.csv",
        DAY3_DIR / "standardized-orders.csv",
        DAY3_DIR / "rejected-orders.csv",
        DAY3_DIR / "day3-validation.json",
        DAY5_DIR / "normalized-model.md",
        DAY5_DIR / "normalized-schema.sql",
        DAY5_DIR / "normalization-report.json",
        DAY5_DIR / "day5-validation.json",
        DAY6_DIR / "denormalization-decision.md",
        DAY6_DIR / "feature-view-spec.yaml",
        DAY6_DIR / "feature-standard-extension.yaml",
        DAY6_DIR / "feature-sample.csv",
        DAY6_DIR / "partition-plan.md",
        DAY6_DIR / "db-catalog.csv",
        DAY6_DIR / "catalog-standard-check.json",
        DAY6_DIR / "day6-validation.json",
        AS_IS_CATALOG,
        rules_path,
        GAP_REPORT,
        *configured_sources,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"누적 입력 파일이 없습니다: {missing}")

    statuses = {
        "day2": read_json(DAY2_DIR / "day2-validation.json")["status"]
        == "ready",
        "day3": read_json(DAY3_DIR / "day3-validation.json")["status"]
        == "ready",
        "day5": read_json(DAY5_DIR / "day5-validation.json")["status"]
        == "ready",
        "day6": read_json(DAY6_DIR / "day6-validation.json")["status"]
        == "ready",
        "day6_catalog": read_json(
            DAY6_DIR / "catalog-standard-check.json"
        )["overall_status"]
        == "PASS",
    }
    if not all(statuses.values()):
        raise ValueError(f"이전 Day 입력 상태를 확인하세요: {statuses}")

    schema_text = (DAY5_DIR / "normalized-schema.sql").read_text(
        encoding="utf-8"
    ).upper()
    if schema_text.count("CREATE TABLE") < 5:
        raise ValueError("Day 5 정규화 스키마의 다섯 테이블을 확인할 수 없습니다.")

    return statuses


def build_standardized_catalog():
    _, as_is_rows = read_csv(AS_IS_CATALOG)
    standardized_rows = []

    for row in as_is_rows:
        source_column = row["column_name"]
        contract = COLUMN_CONTRACTS.get(source_column)
        if contract is None:
            raise ValueError(f"번역되지 않은 AS-IS 컬럼입니다: {source_column}")

        standardized_rows.append(
            {
                "source_table_name": row["table_name"],
                "source_column_name": source_column,
                "standard_table_name": STANDARD_TABLE_NAME,
                "standard_column_name": contract["standard_column_name"],
                "logical_name": contract["logical_name"],
                "word_ids": "|".join(contract["word_ids"]),
                "domain_id": contract["domain_id"],
                "data_type": contract["data_type"],
                "max_length": contract["max_length"],
                "nullable": contract["nullable"],
                "translation_status": "MAPPED",
            }
        )

    write_csv(
        STANDARDIZED_CATALOG,
        STANDARDIZED_CATALOG_FIELDS,
        standardized_rows,
    )
    return standardized_rows


def parse_decimal(value):
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def dimension(status_condition, metrics):
    return {
        "status": "PASS" if status_condition else "FAIL",
        **metrics,
    }


def measure_quality(feature_path, rules):
    dataset_rules = rules["dataset"]
    dimension_rules = rules["dimensions"]

    feature_columns, feature_rows = read_csv(feature_path)
    if feature_columns != dataset_rules["expected_columns"]:
        raise ValueError("feature-sample.csv의 7개 컬럼 순서가 계약과 다릅니다.")
    if feature_columns != EXPECTED_FEATURE_COLUMNS:
        raise ValueError("Day 6 feature 명세와 실제 CSV 컬럼이 다릅니다.")

    completeness_rules = dimension_rules["completeness"]
    required_columns = completeness_rules["required_columns"]
    missing_required_count = sum(
        1
        for row in feature_rows
        for column in required_columns
        if row[column].strip() == ""
    )

    conditional_columns = completeness_rules["conditional_nullable_columns"]
    allowed_null_condition = completeness_rules["allowed_null_condition"]
    if allowed_null_condition != "order_count_30d_equals_zero":
        raise ValueError(
            "지원하지 않는 allowed_null_condition입니다: "
            f"{allowed_null_condition}"
        )

    conditional_nullable_violation_count = 0
    for row in feature_rows:
        order_count_text = row["order_count_30d"].strip()
        order_count = int(order_count_text) if order_count_text else None
        optional_values = [row[column].strip() for column in conditional_columns]
        if order_count == 0 and any(optional_values):
            conditional_nullable_violation_count += 1
        if order_count is not None and order_count > 0 and not all(optional_values):
            conditional_nullable_violation_count += 1

    expected_row_count = dataset_rules["expected_row_count"]
    completeness_violation_count = (
        missing_required_count + conditional_nullable_violation_count
    )
    maximum_completeness_violations = int(
        completeness_rules["maximum_violation_count"]
    )
    completeness_ok = (
        len(feature_rows) == expected_row_count
        and completeness_violation_count <= maximum_completeness_violations
    )
    completeness = dimension(
        completeness_ok,
        {
            "expected_row_count": expected_row_count,
            "actual_row_count": len(feature_rows),
            "required_cell_count": len(feature_rows) * len(required_columns),
            "missing_required_count": missing_required_count,
            "conditional_nullable_violation_count": (
                conditional_nullable_violation_count
            ),
        },
    )

    uniqueness_rules = dimension_rules["uniqueness"]
    key_columns = uniqueness_rules["key_columns"]
    key_counter = Counter(
        tuple(row[column] for column in key_columns)
        for row in feature_rows
    )
    duplicate_key_count = sum(
        count - 1 for count in key_counter.values() if count > 1
    )
    uniqueness = dimension(
        duplicate_key_count
        <= int(uniqueness_rules["maximum_duplicate_count"]),
        {
            "key_columns": key_columns,
            "checked_key_count": len(feature_rows),
            "duplicate_key_count": duplicate_key_count,
        },
    )

    validity_rules = dimension_rules["validity"]
    numeric_columns = validity_rules["non_negative_columns"]
    non_negative_violation_count = 0
    checked_numeric_cell_count = 0
    for row in feature_rows:
        for column in numeric_columns:
            value = row[column].strip()
            if value == "" and column == "last_order_days_ago":
                continue
            checked_numeric_cell_count += 1
            parsed = parse_decimal(value)
            if parsed is None or parsed < 0:
                non_negative_violation_count += 1

    zero_order_consistency_violation_count = 0
    if validity_rules["zero_order_requires_zero_sums"]:
        for row in feature_rows:
            order_count = parse_decimal(row["order_count_30d"])
            quantity_sum = parse_decimal(row["quantity_sum_30d"])
            spend_sum = parse_decimal(row["spend_sum_30d"])
            if order_count == 0 and (quantity_sum != 0 or spend_sum != 0):
                zero_order_consistency_violation_count += 1

    validity_violation_count = (
        non_negative_violation_count
        + zero_order_consistency_violation_count
    )
    validity = dimension(
        validity_violation_count
        <= int(validity_rules["maximum_violation_count"]),
        {
            "checked_numeric_cell_count": checked_numeric_cell_count,
            "non_negative_violation_count": non_negative_violation_count,
            "zero_order_consistency_violation_count": (
                zero_order_consistency_violation_count
            ),
        },
    )

    reference_rules = dimension_rules["referential_integrity"]
    member_reference = reference_rules["member_reference"]
    category_reference = reference_rules["category_reference"]
    _, member_reference_rows = read_csv(
        resolve_rule_path(member_reference["source_file"])
    )
    _, category_reference_rows = read_csv(
        resolve_rule_path(category_reference["source_file"])
    )
    known_member_ids = {
        row[member_reference["reference_column"]]
        for row in member_reference_rows
    }
    known_category_codes = {
        row[category_reference["reference_column"]]
        for row in category_reference_rows
    }

    unknown_member_ids = sorted(
        {
            row[member_reference["feature_column"]]
            for row in feature_rows
            if row[member_reference["feature_column"]] not in known_member_ids
        }
    )
    unknown_category_codes = sorted(
        {
            row[category_reference["feature_column"]]
            for row in feature_rows
            if row[category_reference["feature_column"]]
            and row[category_reference["feature_column"]]
            not in known_category_codes
        }
    )
    unknown_reference_count = (
        len(unknown_member_ids) + len(unknown_category_codes)
    )
    referential_integrity = dimension(
        unknown_reference_count
        <= int(reference_rules["maximum_unknown_count"]),
        {
            "reference_member_count": len(known_member_ids),
            "reference_category_count": len(known_category_codes),
            "unknown_member_ids": unknown_member_ids,
            "unknown_category_codes": unknown_category_codes,
        },
    )

    point_rules = dimension_rules["point_in_time"]
    expected_as_of_date = date.fromisoformat(point_rules["expected_as_of_date"])
    feature_spec = load_yaml(DAY6_DIR / "feature-view-spec.yaml")["feature_view"]
    time_rule = feature_spec["time_rule"]
    window_start = expected_as_of_date - timedelta(
        days=int(time_rule["window_days"])
    )
    include_start = bool(time_rule["include_start"])
    include_as_of = bool(time_rule["include_as_of"])
    if bool(point_rules["include_as_of_date"]) != include_as_of:
        raise ValueError(
            "quality-rules.yaml과 feature-view-spec.yaml의 "
            "include_as_of 설정이 다릅니다."
        )
    allowed_status_codes = set(
        feature_spec["filters"]["order_status_code"]["allowed"]
    )

    _, source_orders = read_csv(resolve_rule_path(point_rules["source_file"]))
    source_datetime_column = point_rules["source_datetime_column"]

    def is_in_feature_window(order_date):
        starts_in_window = (
            order_date >= window_start
            if include_start
            else order_date > window_start
        )
        ends_in_window = (
            order_date <= expected_as_of_date
            if include_as_of
            else order_date < expected_as_of_date
        )
        return starts_in_window and ends_in_window

    def is_future_for_feature(order_date):
        return (
            order_date > expected_as_of_date
            or (order_date == expected_as_of_date and not include_as_of)
        )

    historical_order_ids = defaultdict(set)
    future_order_ids = defaultdict(set)
    for row in source_orders:
        if row["order_status_code"] not in allowed_status_codes:
            continue
        order_date = datetime.fromisoformat(row[source_datetime_column]).date()
        if is_in_feature_window(order_date):
            historical_order_ids[row["member_id"]].add(row["order_id"])
        elif is_future_for_feature(order_date):
            future_order_ids[row["member_id"]].add(row["order_id"])

    unexpected_as_of_dates = sorted(
        {
            row["as_of_date"]
            for row in feature_rows
            if row["as_of_date"] != expected_as_of_date.isoformat()
        }
    )
    order_count_mismatch_member_ids = set()
    future_leak_member_ids = set()
    negative_last_order_days_count = 0

    for row in feature_rows:
        member_id = row["member_id"]
        actual_order_count = int(row["order_count_30d"])
        expected_order_count = len(historical_order_ids[member_id])
        if actual_order_count != expected_order_count:
            order_count_mismatch_member_ids.add(member_id)
        if actual_order_count > expected_order_count:
            future_leak_member_ids.add(member_id)

        last_days = row["last_order_days_ago"].strip()
        if last_days and int(last_days) < 0:
            negative_last_order_days_count += 1

    historical_source_order_count = sum(
        len(order_ids) for order_ids in historical_order_ids.values()
    )
    future_source_order_count = sum(
        len(order_ids) for order_ids in future_order_ids.values()
    )

    future_leak_count = (
        len(future_leak_member_ids) + negative_last_order_days_count
    )
    point_in_time = dimension(
        not unexpected_as_of_dates
        and not order_count_mismatch_member_ids
        and future_leak_count
        <= int(point_rules["maximum_future_leak_count"]),
        {
            "expected_as_of_date": expected_as_of_date.isoformat(),
            "unexpected_as_of_dates": unexpected_as_of_dates,
            "historical_source_order_count": historical_source_order_count,
            "future_source_order_count": future_source_order_count,
            "order_count_mismatch_member_ids": sorted(
                order_count_mismatch_member_ids
            ),
            "future_leak_member_ids": sorted(future_leak_member_ids),
            "negative_last_order_days_count": negative_last_order_days_count,
        },
    )

    dimensions = {
        "completeness": completeness,
        "uniqueness": uniqueness,
        "validity": validity,
        "referential_integrity": referential_integrity,
        "point_in_time": point_in_time,
    }
    pass_count = sum(
        result["status"] == "PASS" for result in dimensions.values()
    )
    fail_count = len(dimensions) - pass_count
    gate_rules = rules["quality_gate"]
    required_dimensions = gate_rules["required_dimensions"]
    unknown_required_dimensions = sorted(
        set(required_dimensions) - set(dimensions)
    )
    if unknown_required_dimensions:
        raise ValueError(
            "quality_gate에 알 수 없는 차원이 있습니다: "
            f"{unknown_required_dimensions}"
        )
    required_fail_count = sum(
        dimensions[name]["status"] == "FAIL"
        for name in required_dimensions
    )
    gate_passed = required_fail_count <= int(
        gate_rules["maximum_failed_dimension_count"]
    )

    return {
        "dataset": dataset_rules["name"],
        "source_file": feature_path.name,
        "row_count": len(feature_rows),
        "column_count": len(feature_columns),
        "overall_status": "PASS" if gate_passed else "FAIL",
        "summary": {
            "dimension_count": len(dimensions),
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "dimensions": dimensions,
    }


def build_validation(input_statuses, standardized_rows, quality_report):
    gap_report = read_json(GAP_REPORT)
    standard_columns = [
        row["standard_column_name"] for row in standardized_rows
    ]

    checks = {
        "all_input_contracts_ready": all(input_statuses.values()),
        "as_is_gap_detected": gap_report["overall_status"] == "FAIL"
        and gap_report["name_gap_column_count"] == 7
        and gap_report["domain_gap_column_count"] == 3,
        "all_catalog_columns_mapped": len(standardized_rows) == 7
        and all(row["translation_status"] == "MAPPED" for row in standardized_rows),
        "feature_catalog_has_exact_7_columns": (
            standard_columns == EXPECTED_FEATURE_COLUMNS
        ),
        "quality_status_pass": quality_report["overall_status"] == "PASS",
        "all_quality_dimensions_pass": all(
            result["status"] == "PASS"
            for result in quality_report["dimensions"].values()
        ),
        "pre_validation_artifacts_exist": all(
            path.exists()
            for path in [
                AS_IS_CATALOG,
                QUALITY_RULES,
                GAP_REPORT,
                STANDARDIZED_CATALOG,
                QUALITY_REPORT,
            ]
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]

    return {
        "day": 7,
        "status": "PASS" if not failed_checks else "FAIL",
        "checks": checks,
        "failed_checks": failed_checks,
        "evidence": {
            "as_is_checked_column_count": gap_report["checked_column_count"],
            "as_is_name_gap_column_count": gap_report["name_gap_column_count"],
            "as_is_domain_gap_column_count": gap_report[
                "domain_gap_column_count"
            ],
            "standardized_catalog_column_count": len(standardized_rows),
            "feature_row_count": quality_report["row_count"],
            "quality_status": quality_report["overall_status"],
            "quality_dimension_statuses": {
                name: result["status"]
                for name, result in quality_report["dimensions"].items()
            },
        },
        "artifacts": [
            "as-is-catalog.csv",
            "quality-rules.yaml",
            "catalog-gap-report.json",
            "standardized-catalog.csv",
            "quality-report.json",
            "day7-validation.json",
        ],
        "next_day": {
            "required_catalog_columns": EXPECTED_FEATURE_COLUMNS,
            "required_quality_status": "PASS",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--feature",
        default=None,
        help="생략하면 quality-rules.yaml의 dataset.source_file을 사용합니다.",
    )
    parser.add_argument(
        "--rules",
        default=str(QUALITY_RULES),
        help="검증에 사용할 품질 규칙 YAML 경로입니다.",
    )
    args = parser.parse_args()

    rules_path = resolve_rule_path(args.rules)
    rules = load_yaml(rules_path)
    feature_path = resolve_rule_path(
        args.feature or rules["dataset"]["source_file"]
    )

    input_statuses = require_cumulative_inputs(rules, rules_path)
    validate_feature_contract()
    standardized_rows = build_standardized_catalog()
    quality_report = measure_quality(feature_path, rules)
    write_json(QUALITY_REPORT, quality_report)

    validation = build_validation(
        input_statuses,
        standardized_rows,
        quality_report,
    )
    write_json(VALIDATION_REPORT, validation)

    print(f"catalog_rows={len(standardized_rows)}")
    print(f"feature_rows={quality_report['row_count']}")
    print(f"quality_status={quality_report['overall_status']}")
    print(f"day7_status={validation['status']}")


if __name__ == "__main__":
    main()