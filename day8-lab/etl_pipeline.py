import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path


UPSTREAM_CONTRACT = {
    "day2": [
        "legacy-columns.csv",
        "standard-words.csv",
        "standard-terms.csv",
        "naming-rules.yaml",
        "data-domains.yaml",
        "day2-validation.json",
    ],
    "day3": [
        "legacy-orders.csv",
        "profile-report.json",
        "column-mapping.csv",
        "standardized-orders.csv",
        "rejected-orders.csv",
        "day3-validation.json",
    ],
    "day4": [
        "business-rules.md",
        "conceptual-model.md",
        "entity-candidates.csv",
        "identifier-decisions.csv",
        "ai-entity-scope.yaml",
        "day4-validation.json",
    ],
    "day5": [
        "relationship-rules.md",
        "normalized-model.md",
        "normalized-schema.sql",
        "normalization-report.json",
        "day5-validation.json",
    ],
    "day6": [
        "denormalization-decision.md",
        "feature-view-spec.yaml",
        "feature-standard-extension.yaml",
        "build_features.py",
        "feature-sample.csv",
        "partition-plan.md",
        "db-catalog.csv",
        "catalog-standard-check.json",
        "day6-validation.json",
    ],
    "day7": [
        "as-is-catalog.csv",
        "quality-rules.yaml",
        "catalog_gap.py",
        "catalog-gap-report.json",
        "translate_catalog.py",
        "standardized-catalog.csv",
        "quality-report.json",
        "day7-validation.json",
    ],
}

VALIDATION_FILES = {
    "day2": "day2-validation.json",
    "day3": "day3-validation.json",
    "day4": "day4-validation.json",
    "day5": "day5-validation.json",
    "day6": "day6-validation.json",
    "day7": "day7-validation.json",
}

DAY2_STANDARD_COLUMNS = {
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

DAY7_CATALOG_FIELDS = [
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

EXPECTED_FEATURE_CATALOG = {
    "member_id": {
        "source_column_name": "mbr_no",
        "logical_name": "회원ID",
        "word_ids": "MEMBER|ID",
        "domain_id": "ID_20",
        "data_type": "VARCHAR",
        "max_length": "20",
        "nullable": "N",
    },
    "as_of_date": {
        "source_column_name": "base_dt",
        "logical_name": "기준일자",
        "word_ids": "AS_OF|DATE",
        "domain_id": "DATE_ISO",
        "data_type": "DATE",
        "max_length": "",
        "nullable": "N",
    },
    "order_count_30d": {
        "source_column_name": "ord_cnt_30d",
        "logical_name": "30일주문건수",
        "word_ids": "WINDOW_30D|ORDER|COUNT",
        "domain_id": "NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "N",
    },
    "quantity_sum_30d": {
        "source_column_name": "qty_sum_30d",
        "logical_name": "30일수량합계",
        "word_ids": "WINDOW_30D|QUANTITY|SUM",
        "domain_id": "NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "N",
    },
    "spend_sum_30d": {
        "source_column_name": "spend_amt_30d",
        "logical_name": "30일구매금액합계",
        "word_ids": "WINDOW_30D|SPEND|SUM",
        "domain_id": "MONEY_12_2",
        "data_type": "DECIMAL",
        "max_length": "12",
        "nullable": "N",
    },
    "preferred_category_code_30d": {
        "source_column_name": "pref_ctg_cd_30d",
        "logical_name": "30일선호카테고리코드",
        "word_ids": "WINDOW_30D|PREFERRED|CATEGORY|CODE",
        "domain_id": "OPTIONAL_CODE_20",
        "data_type": "VARCHAR",
        "max_length": "20",
        "nullable": "Y",
    },
    "last_order_days_ago": {
        "source_column_name": "last_ord_days",
        "logical_name": "마지막주문경과일수",
        "word_ids": "LAST|ORDER|DAYS_AGO",
        "domain_id": "OPTIONAL_NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "Y",
    },
}

DATASET_FIELDS = [
    "dataset_record_id",
    "member_id",
    "as_of_date",
    "order_count_30d",
    "quantity_sum_30d",
    "spend_sum_30d",
    "preferred_category_code_30d",
    "last_order_days_ago",
    "label_next_7d_category_code",
]

FAILED_FIELDS = DATASET_FIELDS + [
    "reason_type",
    "reason_code",
    "source_quality_failure",
]

EXPECTED_SCHEMA_COLUMNS = {
    "dataset_record_id": {
        "domain": "DATASET_RECORD_ID_40",
        "type": "string",
        "nullable": False,
        "catalog_data_type": "VARCHAR(40)",
    },
    "member_id": {
        "domain": "ID_20",
        "type": "string",
        "nullable": False,
        "catalog_data_type": "VARCHAR(20)",
    },
    "as_of_date": {
        "domain": "DATE_ISO",
        "type": "date",
        "nullable": False,
        "catalog_data_type": "DATE",
    },
    "order_count_30d": {
        "domain": "NON_NEGATIVE_INTEGER",
        "type": "integer",
        "nullable": False,
        "catalog_data_type": "INTEGER",
    },
    "quantity_sum_30d": {
        "domain": "NON_NEGATIVE_INTEGER",
        "type": "integer",
        "nullable": False,
        "catalog_data_type": "INTEGER",
    },
    "spend_sum_30d": {
        "domain": "MONEY_12_2",
        "type": "decimal",
        "nullable": False,
        "catalog_data_type": "DECIMAL(12,2)",
    },
    "preferred_category_code_30d": {
        "domain": "OPTIONAL_CODE_20",
        "type": "string",
        "nullable": True,
        "catalog_data_type": "VARCHAR(20)",
    },
    "last_order_days_ago": {
        "domain": "OPTIONAL_NON_NEGATIVE_INTEGER",
        "type": "integer",
        "nullable": True,
        "catalog_data_type": "INTEGER",
    },
    "label_next_7d_category_code": {
        "domain": "CODE_20",
        "type": "string",
        "nullable": False,
        "catalog_data_type": "VARCHAR(20)",
    },
}

CATALOG_FIELDS = [
    "dataset_name",
    "column_order",
    "physical_column_name",
    "korean_term_name",
    "domain_id",
    "data_type",
    "nullable",
    "role",
    "source",
]

ALLOWED_STATUSES = {"PAID", "SHIPPING", "DONE"}
ALLOWED_CATEGORY_CODES = {"C01", "C02", "C03"}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_yaml_scalar(value):
    cleaned = value.strip().strip("'\"")
    if cleaned.lower() == "true":
        return True
    if cleaned.lower() == "false":
        return False
    return cleaned


def read_schema_columns(path):
    """이 수업의 단순한 columns 블록만 표준 라이브러리로 읽는다."""
    columns = []
    current = None
    in_columns = False

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip() == "columns:" and line.startswith("  "):
                in_columns = True
                continue
            if not in_columns:
                continue
            if line and not line[0].isspace():
                break

            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- name:"):
                current = {
                    "name": parse_yaml_scalar(
                        stripped.split(":", 1)[1]
                    )
                }
                columns.append(current)
                continue
            if current is None or ":" not in stripped:
                raise ValueError(
                    f"to-be-schema.yaml {line_number}행의 "
                    "columns 형식을 읽을 수 없습니다."
                )
            key, value = stripped.split(":", 1)
            current[key] = parse_yaml_scalar(value)

    if not columns:
        raise ValueError("to-be-schema.yaml에 columns가 없습니다.")
    return columns


def validate_schema_columns(columns):
    names = [column.get("name") for column in columns]
    if names != DATASET_FIELDS:
        raise ValueError(
            "to-be-schema.yaml 컬럼 순서가 DATASET_FIELDS와 다릅니다."
        )

    for column in columns:
        name = column["name"]
        expected = EXPECTED_SCHEMA_COLUMNS[name]
        for key in ["domain", "type", "nullable"]:
            actual = column.get(key)
            if actual != expected[key]:
                raise ValueError(
                    f"to-be-schema.yaml {name}.{key}가 "
                    f"{expected[key]}여야 하지만 {actual}입니다."
                )


def validate_catalog_rows(schema_columns, catalog_rows):
    schema_by_name = {
        column["name"]: column for column in schema_columns
    }
    catalog_names = [
        row["physical_column_name"] for row in catalog_rows
    ]
    if catalog_names != DATASET_FIELDS:
        raise ValueError("catalog-final.csv 컬럼 순서가 schema와 다릅니다.")

    for row in catalog_rows:
        name = row["physical_column_name"]
        schema = schema_by_name[name]
        expected = EXPECTED_SCHEMA_COLUMNS[name]
        expected_nullable = "Y" if schema["nullable"] else "N"
        if row["domain_id"] != schema["domain"]:
            raise ValueError(f"catalog-final.csv {name} 도메인이 다릅니다.")
        if row["nullable"] != expected_nullable:
            raise ValueError(f"catalog-final.csv {name} NULL 규칙이 다릅니다.")
        if row["data_type"] != expected["catalog_data_type"]:
            raise ValueError(f"catalog-final.csv {name} 타입이 다릅니다.")


def read_top_level_yaml_value(path, key):
    prefix = f"{key}:"
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.startswith(prefix):
                value = line.split(":", 1)[1].strip()
                return value.strip("'\"")
    raise ValueError(f"{path.name}에 {key}가 없습니다.")


def read_yaml_list_section(path, section_name):
    """확장 표준의 최상위 목록 한 개를 제한적으로 읽는다."""
    items = []
    current = None
    nested_key = None
    in_section = False

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip() == f"{section_name}:" and not line.startswith(" "):
                in_section = True
                continue
            if not in_section:
                continue
            if line.strip() and not line[0].isspace():
                break

            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent == 2 and stripped.startswith("- "):
                key, value = stripped[2:].split(":", 1)
                current = {key: parse_yaml_scalar(value)}
                items.append(current)
                nested_key = None
            elif indent == 4 and current is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                if value.strip():
                    current[key] = parse_yaml_scalar(value)
                    nested_key = None
                else:
                    current[key] = []
                    nested_key = key
            elif (
                indent == 6
                and current is not None
                and nested_key is not None
                and stripped.startswith("- ")
            ):
                current[nested_key].append(
                    parse_yaml_scalar(stripped[2:])
                )
            else:
                raise ValueError(
                    f"{path.name}의 {section_name} 형식을 읽을 수 없습니다."
                )
    return items


def validate_feature_standard_extension(path):
    expected_word_ids = [
        "AS_OF",
        "DATE",
        "WINDOW_30D",
        "COUNT",
        "SUM",
        "SPEND",
        "PREFERRED",
        "LAST",
        "DAYS_AGO",
    ]
    expected_domain_ids = [
        "DATE_ISO",
        "NON_NEGATIVE_INTEGER",
        "OPTIONAL_NON_NEGATIVE_INTEGER",
        "OPTIONAL_CODE_20",
    ]
    words = read_yaml_list_section(path, "words")
    domains = read_yaml_list_section(path, "domains")
    bindings = read_yaml_list_section(path, "term_bindings")

    if [item.get("word_id") for item in words] != expected_word_ids:
        raise ValueError("feature 표준 확장의 9개 word_id가 다릅니다.")
    if [item.get("domain_id") for item in domains] != expected_domain_ids:
        raise ValueError("feature 표준 확장의 4개 domain_id가 다릅니다.")
    if [item.get("physical_name") for item in bindings] != FEATURE_FIELDS[1:]:
        raise ValueError("feature 표준 확장의 6개 term binding이 다릅니다.")

    for binding in bindings:
        name = binding["physical_name"]
        expected = EXPECTED_FEATURE_CATALOG[name]
        if (
            binding.get("logical_name") != expected["logical_name"]
            or binding.get("word_ids")
            != expected["word_ids"].split("|")
            or binding.get("domain_id") != expected["domain_id"]
            or binding.get("nullable")
            != (expected["nullable"] == "Y")
        ):
            raise ValueError(
                "feature 표준 확장 term binding이 다릅니다: " + name
            )

    domain_by_id = {item["domain_id"]: item for item in domains}
    expected_domain_metadata = {
        "DATE_ISO": {
            "database_type": "DATE",
            "nullable": False,
            "format": "%Y-%m-%d",
        },
        "NON_NEGATIVE_INTEGER": {
            "database_type": "INTEGER",
            "nullable": False,
            "minimum": "0",
        },
        "OPTIONAL_NON_NEGATIVE_INTEGER": {
            "database_type": "INTEGER",
            "nullable": True,
            "minimum": "0",
        },
        "OPTIONAL_CODE_20": {
            "database_type": "VARCHAR",
            "length": "20",
            "nullable": True,
            "format": "^[A-Z][A-Z0-9_\\-]{0,19}$",
        },
    }
    for domain_id, expected in expected_domain_metadata.items():
        for key, expected_value in expected.items():
            if domain_by_id[domain_id].get(key) != expected_value:
                raise ValueError(
                    "feature 표준 확장 도메인 정의가 다릅니다: "
                    f"{domain_id}.{key}"
                )

    return {
        "word_count": len(words),
        "domain_count": len(domains),
        "binding_count": len(bindings),
    }


def check_status(value, file_name):
    normalized = str(value).strip().lower()
    if normalized not in {"ready", "pass"}:
        raise ValueError(
            f"{file_name} 상태가 시작 조건을 통과하지 못했습니다: {value}"
        )


def check_upstream_contract(artifact_root):
    missing = []
    for day, file_names in UPSTREAM_CONTRACT.items():
        for file_name in file_names:
            path = artifact_root / day / file_name
            if not path.is_file():
                missing.append(str(path))

    if missing:
        raise FileNotFoundError(
            "필수 upstream 파일이 없습니다: " + ", ".join(missing)
        )

    extension_path = (
        artifact_root
        / "day6"
        / "feature-standard-extension.yaml"
    )
    extension_status = read_top_level_yaml_value(
        extension_path,
        "status",
    )
    if extension_status != "approved":
        raise ValueError(
            "feature-standard-extension.yaml 상태가 "
            "approved가 아닙니다."
        )
    extension_counts = validate_feature_standard_extension(
        extension_path
    )

    statuses = {}
    for day, file_name in VALIDATION_FILES.items():
        path = artifact_root / day / file_name
        report = read_json(path)
        status = report.get("status", "")
        check_status(status, file_name)
        statuses[day] = status

    day5_report = read_json(
        artifact_root / "day5" / "normalization-report.json"
    )
    expected_day5_counts = {
        "source_rows": 6,
        "member": 4,
        "category": 3,
        "book": 5,
        "book_order": 5,
        "order_item": 6,
        "order_amount": "153000.00",
    }
    if (
        day5_report.get("status") != "ready"
        or day5_report.get("source") != "standardized-orders.csv"
        or day5_report.get("table_counts") != expected_day5_counts
        or day5_report.get("issues") != []
        or day5_report.get("foreign_key_violations") != []
        or day5_report.get("round_trip")
        != {"matched": True, "mismatch_samples": []}
    ):
        raise ValueError(
            "Day 5 normalization-report.json의 행 수, 금액, "
            "FK 또는 round-trip 근거가 계약과 다릅니다."
        )

    day7_quality_path = artifact_root / "day7" / "quality-report.json"
    day7_quality = read_json(day7_quality_path)
    day7_status = str(
        day7_quality.get("overall_status", "")
    ).upper()
    if day7_status != "PASS":
        raise ValueError(
            "Day 7 quality-report.json 상태는 PASS여야 합니다."
        )
    expected_dimensions = {
        "completeness",
        "uniqueness",
        "validity",
        "referential_integrity",
        "point_in_time",
    }
    day7_summary = day7_quality.get("summary", {})
    day7_dimensions = day7_quality.get("dimensions", {})
    if (
        day7_quality.get("dataset")
        != "member_book_preference_features"
        or day7_quality.get("source_file") != "feature-sample.csv"
        or day7_quality.get("row_count") != 4
        or day7_quality.get("column_count") != 7
        or day7_summary
        != {
            "dimension_count": 5,
            "pass_count": 5,
            "fail_count": 0,
        }
        or set(day7_dimensions) != expected_dimensions
        or any(
            result.get("status") != "PASS"
            for result in day7_dimensions.values()
        )
    ):
        raise ValueError(
            "Day 7 quality-report.json의 5개 품질 차원이 "
            "모두 PASS인 4행/7컬럼 계약과 다릅니다."
        )

    point_in_time = day7_dimensions["point_in_time"]
    expected_as_of_date = point_in_time.get("expected_as_of_date")
    if (
        expected_as_of_date != "2026-08-12"
        or point_in_time.get("unexpected_as_of_dates") != []
        or point_in_time.get("future_leak_member_ids") != []
        or point_in_time.get("negative_last_order_days_count") != 0
    ):
        raise ValueError("Day 7 시점 품질 근거가 계약과 다릅니다.")

    term_rows = read_csv(
        artifact_root / "day2" / "standard-terms.csv"
    )
    physical_names = {row["physical_name"] for row in term_rows}
    missing_standard_terms = DAY2_STANDARD_COLUMNS - physical_names
    if missing_standard_terms:
        missing_text = ", ".join(sorted(missing_standard_terms))
        raise ValueError(
            "Day 2 표준 용어가 부족합니다: " + missing_text
        )

    catalog_rows = read_csv(
        artifact_root / "day7" / "standardized-catalog.csv"
    )
    if len(catalog_rows) != 7:
        raise ValueError("Day 7 표준 카탈로그는 정확히 7행이어야 합니다.")
    if list(catalog_rows[0].keys()) != DAY7_CATALOG_FIELDS:
        raise ValueError("Day 7 표준 카탈로그 헤더가 계약과 다릅니다.")

    catalog_names = [
        row["standard_column_name"] for row in catalog_rows
    ]
    if catalog_names != FEATURE_FIELDS:
        raise ValueError(
            "Day 7 표준 카탈로그의 7개 feature 순서가 계약과 다릅니다."
        )

    for row in catalog_rows:
        feature_name = row["standard_column_name"]
        expected = EXPECTED_FEATURE_CATALOG[feature_name]
        common_expected = {
            "source_table_name": "ml_mbr_ftr",
            "standard_table_name": (
                "member_book_preference_features"
            ),
            "translation_status": "MAPPED",
        }
        for key, expected_value in {
            **common_expected,
            **expected,
        }.items():
            if row.get(key) != expected_value:
                raise ValueError(
                    "Day 7 표준 카탈로그 값이 다릅니다: "
                    f"{feature_name}.{key}"
                )

    return {
        "required_file_count": sum(
            len(file_names)
            for file_names in UPSTREAM_CONTRACT.values()
        ),
        "validation_statuses": statuses,
        "day5_normalization_counts": expected_day5_counts,
        "day7_quality_status": day7_status,
        "expected_as_of_date": expected_as_of_date,
        "feature_standard_extension_status": extension_status,
        "feature_standard_extension_counts": extension_counts,
    }


def parse_non_negative_integer(value, field_name, allow_blank=False):
    if allow_blank and value == "":
        return None

    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(
            f"{field_name} 값은 정수여야 합니다: {value}"
        ) from error

    if parsed < 0:
        raise ValueError(
            f"{field_name} 값은 0 이상이어야 합니다: {value}"
        )
    return parsed


def normalize_feature(row):
    errors = []
    member_id = row.get("member_id", "").strip()
    as_of_value = row.get("as_of_date", "").strip()

    if not member_id:
        errors.append("MEMBER_ID_REQUIRED")
    elif re.fullmatch(r"[A-Z][A-Z0-9-]{0,19}", member_id) is None:
        errors.append("MEMBER_ID_FORMAT_INVALID")

    try:
        as_of_date = date.fromisoformat(as_of_value)
    except ValueError:
        as_of_date = None
        errors.append("AS_OF_DATE_INVALID")

    try:
        order_count = parse_non_negative_integer(
            row.get("order_count_30d", ""),
            "order_count_30d",
        )
    except ValueError:
        order_count = None
        errors.append("ORDER_COUNT_30D_INVALID")

    try:
        quantity_sum = parse_non_negative_integer(
            row.get("quantity_sum_30d", ""),
            "quantity_sum_30d",
        )
    except ValueError:
        quantity_sum = None
        errors.append("QUANTITY_SUM_30D_INVALID")

    try:
        spend_sum = Decimal(row.get("spend_sum_30d", ""))
        if (
            not spend_sum.is_finite()
            or spend_sum < 0
            or spend_sum > Decimal("9999999999.99")
            or spend_sum.as_tuple().exponent < -2
        ):
            raise InvalidOperation
    except InvalidOperation:
        spend_sum = None
        errors.append("SPEND_SUM_30D_INVALID")

    preferred_category = row.get(
        "preferred_category_code_30d",
        "",
    ).strip()
    if (
        preferred_category
        and preferred_category not in ALLOWED_CATEGORY_CODES
    ):
        errors.append("PREFERRED_CATEGORY_INVALID")

    try:
        last_order_days_ago = parse_non_negative_integer(
            row.get("last_order_days_ago", ""),
            "last_order_days_ago",
            allow_blank=True,
        )
    except ValueError:
        last_order_days_ago = None
        errors.append("LAST_ORDER_DAYS_AGO_INVALID")

    if order_count == 0 and last_order_days_ago is not None:
        errors.append("LAST_ORDER_MUST_BE_EMPTY_WHEN_NO_ORDER")
    if (
        order_count is not None
        and order_count > 0
        and last_order_days_ago is None
    ):
        errors.append("LAST_ORDER_REQUIRED_WHEN_ORDER_EXISTS")

    record_id = (
        f"{member_id}_{as_of_value.replace('-', '')}"
        if member_id and as_of_value
        else ""
    )

    normalized = {
        "dataset_record_id": record_id,
        "member_id": member_id,
        "as_of_date": as_of_value,
        "order_count_30d": (
            "" if order_count is None else str(order_count)
        ),
        "quantity_sum_30d": (
            "" if quantity_sum is None else str(quantity_sum)
        ),
        "spend_sum_30d": (
            "" if spend_sum is None else format(spend_sum, ".2f")
        ),
        "preferred_category_code_30d": preferred_category,
        "last_order_days_ago": (
            ""
            if last_order_days_ago is None
            else str(last_order_days_ago)
        ),
        "label_next_7d_category_code": "",
        "_parsed_as_of_date": as_of_date,
    }
    return normalized, errors


def choose_label(member_id, as_of_date, order_rows):
    window_start = datetime.combine(as_of_date, time.min)
    window_end = window_start + timedelta(days=7)
    category_quantity = Counter()

    for row in order_rows:
        if row["member_id"] != member_id:
            continue
        if row["order_status_code"] not in ALLOWED_STATUSES:
            continue

        order_datetime = datetime.fromisoformat(row["order_datetime"])
        if not window_start <= order_datetime < window_end:
            continue

        category_code = row["category_code"]
        quantity = int(row["quantity"])
        category_quantity[category_code] += quantity

    if not category_quantity:
        return ""

    ranked = sorted(
        category_quantity.items(),
        key=lambda item: (-item[1], item[0]),
    )
    return ranked[0][0]


def public_row(normalized):
    return {
        field: normalized.get(field, "")
        for field in DATASET_FIELDS
    }


def failed_row(
    normalized,
    reason_type,
    reason_code,
    source_quality_failure,
):
    row = public_row(normalized)
    row.update(
        {
            "reason_type": reason_type,
            "reason_code": reason_code,
            "source_quality_failure": (
                "true" if source_quality_failure else "false"
            ),
        }
    )
    return row


def make_catalog_rows():
    definitions = [
        (
            "dataset_record_id",
            "데이터셋레코드ID",
            "DATASET_RECORD_ID_40",
            "VARCHAR(40)",
            "N",
            "identifier",
            "member_id + as_of_date",
        ),
        (
            "member_id",
            "회원ID",
            "ID_20",
            "VARCHAR(20)",
            "N",
            "entity_key",
            "day6.feature-sample.csv",
        ),
        (
            "as_of_date",
            "기준일자",
            "DATE_ISO",
            "DATE",
            "N",
            "point_in_time",
            "day6.feature-sample.csv",
        ),
        (
            "order_count_30d",
            "30일주문건수",
            "NON_NEGATIVE_INTEGER",
            "INTEGER",
            "N",
            "feature",
            "day6.feature-sample.csv",
        ),
        (
            "quantity_sum_30d",
            "30일수량합계",
            "NON_NEGATIVE_INTEGER",
            "INTEGER",
            "N",
            "feature",
            "day6.feature-sample.csv",
        ),
        (
            "spend_sum_30d",
            "30일구매금액합계",
            "MONEY_12_2",
            "DECIMAL(12,2)",
            "N",
            "feature",
            "day6.feature-sample.csv",
        ),
        (
            "preferred_category_code_30d",
            "30일선호카테고리코드",
            "OPTIONAL_CODE_20",
            "VARCHAR(20)",
            "Y",
            "feature",
            "day6.feature-sample.csv",
        ),
        (
            "last_order_days_ago",
            "마지막주문경과일수",
            "OPTIONAL_NON_NEGATIVE_INTEGER",
            "INTEGER",
            "Y",
            "feature",
            "day6.feature-sample.csv",
        ),
        (
            "label_next_7d_category_code",
            "다음7일구매카테고리코드",
            "CODE_20",
            "VARCHAR(20)",
            "N",
            "label",
            "day3.standardized-orders.csv",
        ),
    ]

    rows = []
    for index, definition in enumerate(definitions, start=1):
        (
            physical_name,
            korean_name,
            domain_id,
            data_type,
            nullable,
            role,
            source,
        ) = definition
        rows.append(
            {
                "dataset_name": "member_book_preference_training",
                "column_order": index,
                "physical_column_name": physical_name,
                "korean_term_name": korean_name,
                "domain_id": domain_id,
                "data_type": data_type,
                "nullable": nullable,
                "role": role,
                "source": source,
            }
        )
    return rows


def build_dataset_card(
    dataset_version,
    generated_at,
    as_of_date,
    release_status,
    ready_count,
    excluded_count,
    source_failure_count,
    dataset_checksum,
):
    return f"""# Dataset Card

## 이름

회원별 도서 선호 추천 학습 데이터

## 버전

{dataset_version}

## 생성 시각

{generated_at}

## 목적

회원의 과거 30일 구매 특징으로 다음 7일 구매 카테고리를 예측한다.

## 한 행의 의미

한 회원과 한 as_of_date의 feature 및 label이다.

## 시점

- feature: as_of_date 직전 30일
- label: as_of_date 이상 7일 미만
- as_of_date: {as_of_date}

## 포함 기준

다음 7일 안에 PAID, SHIPPING, DONE 상태 주문이 있어 label을 만들 수 있는 회원

## 제외 기준

다음 7일 구매가 없는 회원은 ELIGIBILITY_EXCLUSION으로 failed-rows.csv에 기록한다. 이는 원천 품질 실패가 아니다.

## 행 수

- AI 학습 입력: {ready_count}
- 학습 대상 제외: {excluded_count}
- 원천 품질 실패: {source_failure_count}

## 품질 상태

{release_status}

## SHA-256

{dataset_checksum}

## 주의사항

- member_name과 book_name은 학습 입력에 포함하지 않았다.
- 4명의 작은 교육용 fixture이므로 실제 모델 성능을 대표하지 않는다.
- 다음 7일 구매가 없는 회원을 제외했으므로 이 release만으로 구매 여부 자체를 학습할 수 없다.
- failed-rows.csv는 학습 입력이 아니라 감사와 재검토 입력이다.
"""


def run_pipeline(
    artifact_root,
    schema_path,
    output_dir,
    dataset_version,
    generated_at,
):
    upstream = check_upstream_contract(artifact_root)

    schema_columns = read_schema_columns(schema_path)
    validate_schema_columns(schema_columns)

    feature_path = artifact_root / "day6" / "feature-sample.csv"
    extension_path = (
        artifact_root
        / "day6"
        / "feature-standard-extension.yaml"
    )
    order_path = artifact_root / "day3" / "standardized-orders.csv"
    feature_rows = read_csv(feature_path)
    order_rows = read_csv(order_path)

    if len(feature_rows) != 4:
        raise ValueError("Day 6 feature 행 수는 4여야 합니다.")
    if list(feature_rows[0].keys()) != FEATURE_FIELDS:
        raise ValueError("feature-sample.csv 헤더가 계약과 다릅니다.")
    if len(order_rows) != 6:
        raise ValueError("Day 3 표준 주문 행 수는 6이어야 합니다.")

    ready_rows = []
    failed_rows = []
    seen_record_ids = set()
    domain_violation_count = 0
    duplicate_record_id_count = 0
    temporal_violation_count = 0
    expected_as_of_date = date.fromisoformat(
        upstream["expected_as_of_date"]
    )

    for source_row in feature_rows:
        normalized, errors = normalize_feature(source_row)
        if errors:
            domain_violation_count += 1
        record_id = normalized["dataset_record_id"]

        if record_id in seen_record_ids:
            errors.append("DUPLICATE_DATASET_RECORD_ID")
            duplicate_record_id_count += 1
        seen_record_ids.add(record_id)

        if normalized["_parsed_as_of_date"] != expected_as_of_date:
            errors.append("UNEXPECTED_AS_OF_DATE")
            temporal_violation_count += 1

        if errors:
            failed_rows.append(
                failed_row(
                    normalized,
                    "SOURCE_QUALITY_FAILURE",
                    "|".join(sorted(errors)),
                    True,
                )
            )
            continue

        label = choose_label(
            normalized["member_id"],
            normalized["_parsed_as_of_date"],
            order_rows,
        )
        normalized["label_next_7d_category_code"] = label

        if not label:
            failed_rows.append(
                failed_row(
                    normalized,
                    "ELIGIBILITY_EXCLUSION",
                    "NO_NEXT_PURCHASE_WITHIN_7D",
                    False,
                )
            )
            continue

        if label not in ALLOWED_CATEGORY_CODES:
            failed_rows.append(
                failed_row(
                    normalized,
                    "SOURCE_QUALITY_FAILURE",
                    "LABEL_CATEGORY_INVALID",
                    True,
                )
            )
            continue

        ready_rows.append(public_row(normalized))

    source_failure_count = sum(
        row["source_quality_failure"] == "true"
        for row in failed_rows
    )
    eligibility_exclusion_count = sum(
        row["reason_type"] == "ELIGIBILITY_EXCLUSION"
        for row in failed_rows
    )

    if source_failure_count > 0:
        release_status = "FAIL"
    elif not ready_rows:
        release_status = "FAIL"
    elif eligibility_exclusion_count > 0:
        release_status = "PASS_WITH_QUARANTINE"
    else:
        release_status = "PASS"

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / "ai-ready-dataset.csv"
    failed_path = output_dir / "failed-rows.csv"
    quality_path = output_dir / "quality-report.json"
    manifest_path = output_dir / "dataset-manifest.json"
    lineage_path = output_dir / "lineage.json"
    card_path = output_dir / "dataset-card.md"
    catalog_path = output_dir / "catalog-final.csv"
    validation_path = output_dir / "day8-validation.json"

    write_csv(dataset_path, DATASET_FIELDS, ready_rows)
    write_csv(failed_path, FAILED_FIELDS, failed_rows)
    dataset_checksum = sha256_file(dataset_path)
    failed_checksum = sha256_file(failed_path)

    quality_report = {
        "overall_status": release_status,
        "input_candidate_count": len(feature_rows),
        "ai_ready_row_count": len(ready_rows),
        "failed_row_count": len(failed_rows),
        "eligibility_exclusion_count": eligibility_exclusion_count,
        "source_quality_failure_count": source_failure_count,
        "label_coverage_rate": (
            len(ready_rows) / len(feature_rows)
            if feature_rows
            else 0
        ),
        "rules": [
            {
                "rule": "UPSTREAM_VALIDATIONS_READY_OR_PASS",
                "status": "PASS",
                "failed_count": 0,
            },
            {
                "rule": "FEATURE_REQUIRED_FIELDS_AND_DOMAINS",
                "status": (
                    "PASS"
                    if domain_violation_count == 0
                    else "FAIL"
                ),
                "failed_count": domain_violation_count,
            },
            {
                "rule": "POINT_IN_TIME_TEMPORAL_RULE",
                "status": (
                    "PASS"
                    if temporal_violation_count == 0
                    else "FAIL"
                ),
                "failed_count": temporal_violation_count,
            },
            {
                "rule": "DATASET_RECORD_ID_UNIQUE",
                "status": (
                    "PASS"
                    if duplicate_record_id_count == 0
                    else "FAIL"
                ),
                "failed_count": duplicate_record_id_count,
            },
            {
                "rule": "NEXT_7D_LABEL_ELIGIBILITY",
                "status": "PASS_WITH_EXCLUSIONS",
                "excluded_count": eligibility_exclusion_count,
            },
            {
                "rule": "TRAINING_OUTPUT_LABEL_COMPLETE",
                "status": "PASS",
                "failed_count": 0,
            },
        ],
    }
    write_json(quality_path, quality_report)

    manifest = {
        "dataset_name": "member_book_preference_training",
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "release_status": release_status,
        "schema_file": schema_path.name,
        "files": {
            "training": {
                "path": dataset_path.name,
                "row_count": len(ready_rows),
                "sha256": dataset_checksum,
            },
            "audit": {
                "path": failed_path.name,
                "row_count": len(failed_rows),
                "sha256": failed_checksum,
            },
            "quality_report": quality_path.name,
            "lineage": lineage_path.name,
            "dataset_card": card_path.name,
            "catalog": catalog_path.name,
        },
        "counts": {
            "input_candidate_count": len(feature_rows),
            "ai_ready_row_count": len(ready_rows),
            "failed_row_count": len(failed_rows),
            "eligibility_exclusion_count": (
                eligibility_exclusion_count
            ),
            "source_quality_failure_count": source_failure_count,
        },
        "input_checksums": {
            "day3_standardized_orders_sha256": sha256_file(
                order_path
            ),
            "day6_feature_standard_extension_sha256": sha256_file(
                extension_path
            ),
            "day6_feature_sample_sha256": sha256_file(
                feature_path
            ),
        },
    }

    lineage = {
        "dataset_version": dataset_version,
        "sources": [
            {
                "file": "day2/standard-terms.csv",
                "use": "base_standard_names",
            },
            {
                "file": "day3/standardized-orders.csv",
                "use": "next_7d_label_events",
            },
            {
                "file": "day6/feature-sample.csv",
                "use": "point_in_time_features",
            },
            {
                "file": "day6/feature-standard-extension.yaml",
                "use": "approved_feature_words_and_domains",
            },
            {
                "file": "day7/standardized-catalog.csv",
                "use": "feature_catalog_mapping",
            },
            {
                "file": "day7/quality-report.json",
                "use": "upstream_quality_gate",
            },
        ],
        "transformations": [
            {
                "step": 1,
                "name": "check_upstream_contract",
            },
            {
                "step": 2,
                "name": "validate_feature_domains",
            },
            {
                "step": 3,
                "name": "build_next_7d_category_label",
                "time_rule": (
                    "as_of_date_lte_order_datetime_"
                    "lt_as_of_date_plus_7_days"
                ),
            },
            {
                "step": 4,
                "name": "split_training_and_audit_rows",
            },
            {
                "step": 5,
                "name": "package_release",
            },
        ],
        "outputs": [
            {
                "file": dataset_path.name,
                "role": "AI_TRAINING_INPUT",
            },
            {
                "file": failed_path.name,
                "role": "AUDIT_AND_REVIEW_INPUT",
            },
        ],
    }
    write_json(lineage_path, lineage)

    catalog_rows = make_catalog_rows()
    validate_catalog_rows(schema_columns, catalog_rows)
    write_csv(catalog_path, CATALOG_FIELDS, catalog_rows)

    card_text = build_dataset_card(
        dataset_version,
        generated_at,
        upstream["expected_as_of_date"],
        release_status,
        len(ready_rows),
        eligibility_exclusion_count,
        source_failure_count,
        dataset_checksum,
    )
    with card_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(card_text)

    write_json(manifest_path, manifest)

    validation = {
        "day": 8,
        "status": (
            "READY_FOR_DJANGO"
            if release_status != "FAIL"
            else "FAIL"
        ),
        "release_status": release_status,
        "checks": [
            {
                "name": "upstream_exact_artifacts_present",
                "status": "PASS",
                "evidence": upstream["required_file_count"],
            },
            {
                "name": "day5_normalization_report_exact",
                "status": "PASS",
                "evidence": upstream["day5_normalization_counts"],
            },
            {
                "name": "feature_standard_extension_approved",
                "status": "PASS",
                "evidence": upstream[
                    "feature_standard_extension_status"
                ],
            },
            {
                "name": "feature_standard_extension_exact_structure",
                "status": "PASS",
                "evidence": upstream[
                    "feature_standard_extension_counts"
                ],
            },
            {
                "name": "to_be_schema_metadata_matches_output",
                "status": "PASS",
                "evidence": {
                    "column_count": len(DATASET_FIELDS),
                    "preferred_category_domain": (
                        "OPTIONAL_CODE_20"
                    ),
                    "last_order_domain": (
                        "OPTIONAL_NON_NEGATIVE_INTEGER"
                    ),
                    "catalog_metadata_match": True,
                },
            },
            {
                "name": "ai_ready_row_count",
                "status": (
                    "PASS" if len(ready_rows) == 2 else "FAIL"
                ),
                "evidence": len(ready_rows),
            },
            {
                "name": "eligibility_exclusion_count",
                "status": (
                    "PASS"
                    if eligibility_exclusion_count == 2
                    else "FAIL"
                ),
                "evidence": eligibility_exclusion_count,
            },
            {
                "name": "source_quality_failure_count",
                "status": (
                    "PASS"
                    if source_failure_count == 0
                    else "FAIL"
                ),
                "evidence": source_failure_count,
            },
            {
                "name": "dataset_checksum_recorded",
                "status": "PASS",
                "evidence": dataset_checksum,
            },
            {
                "name": "lineage_and_catalog_written",
                "status": "PASS",
                "evidence": [
                    lineage_path.name,
                    catalog_path.name,
                ],
            },
        ],
    }
    if any(
        check["status"] == "FAIL"
        for check in validation["checks"]
    ):
        validation["status"] = "FAIL"
    write_json(validation_path, validation)

    print(f"input_candidates={len(feature_rows)}")
    print(f"ai_ready_rows={len(ready_rows)}")
    print(f"failed_rows={len(failed_rows)}")
    print(
        "eligibility_exclusions="
        f"{eligibility_exclusion_count}"
    )
    print(f"source_quality_failures={source_failure_count}")
    print(f"dataset_sha256={dataset_checksum}")
    print(f"release_status={release_status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-root",
        default="day8-lab/inputs",
    )
    parser.add_argument(
        "--schema",
        default="day8-lab/to-be-schema.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="day8-lab/release",
    )
    parser.add_argument(
        "--dataset-version",
        default="2026-08-14-v1",
    )
    parser.add_argument(
        "--generated-at",
        default="2026-08-14T18:00:00+09:00",
    )
    args = parser.parse_args()

    run_pipeline(
        artifact_root=Path(args.artifact_root),
        schema_path=Path(args.schema),
        output_dir=Path(args.output_dir),
        dataset_version=args.dataset_version,
        generated_at=args.generated_at,
    )


if __name__ == "__main__":
    main()