import csv
import json
from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DAY2_DIR = ROOT_DIR / "day2"
DAY6_DIR = BASE_DIR.parents[1] / "day6-lab"

AS_IS_CATALOG = BASE_DIR / "as-is-catalog.csv"
OUTPUT_REPORT = BASE_DIR / "catalog-gap-report.json"

STANDARD_TABLE_NAME = "member_book_preference_features"

COLUMN_CONTRACTS = {
    "mbr_no": {
        "standard_column_name": "member_id",
        "logical_name": "회원ID",
        "word_ids": ["MEMBER", "ID"],
        "domain_id": "ID_20",
        "data_type": "VARCHAR",
        "max_length": "20",
        "nullable": "N",
    },
    "base_dt": {
        "standard_column_name": "as_of_date",
        "logical_name": "기준일자",
        "word_ids": ["AS_OF", "DATE"],
        "domain_id": "DATE_ISO",
        "data_type": "DATE",
        "max_length": "",
        "nullable": "N",
    },
    "ord_cnt_30d": {
        "standard_column_name": "order_count_30d",
        "logical_name": "30일주문건수",
        "word_ids": ["WINDOW_30D", "ORDER", "COUNT"],
        "domain_id": "NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "N",
    },
    "qty_sum_30d": {
        "standard_column_name": "quantity_sum_30d",
        "logical_name": "30일수량합계",
        "word_ids": ["WINDOW_30D", "QUANTITY", "SUM"],
        "domain_id": "NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "N",
    },
    "spend_amt_30d": {
        "standard_column_name": "spend_sum_30d",
        "logical_name": "30일구매금액합계",
        "word_ids": ["WINDOW_30D", "SPEND", "SUM"],
        "domain_id": "MONEY_12_2",
        "data_type": "DECIMAL",
        "max_length": "12",
        "nullable": "N",
    },
    "pref_ctg_cd_30d": {
        "standard_column_name": "preferred_category_code_30d",
        "logical_name": "30일선호카테고리코드",
        "word_ids": ["WINDOW_30D", "PREFERRED", "CATEGORY", "CODE"],
        "domain_id": "OPTIONAL_CODE_20",
        "data_type": "VARCHAR",
        "max_length": "20",
        "nullable": "Y",
    },
    "last_ord_days": {
        "standard_column_name": "last_order_days_ago",
        "logical_name": "마지막주문경과일수",
        "word_ids": ["LAST", "ORDER", "DAYS_AGO"],
        "domain_id": "OPTIONAL_NON_NEGATIVE_INTEGER",
        "data_type": "INTEGER",
        "max_length": "",
        "nullable": "Y",
    },
}

EXPECTED_FEATURE_COLUMNS = [
    "member_id",
    "as_of_date",
    "order_count_30d",
    "quantity_sum_30d",
    "spend_sum_30d",
    "preferred_category_code_30d",
    "last_order_days_ago",
]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def require_inputs():
    required = [
        DAY2_DIR / "standard-words.csv",
        DAY2_DIR / "standard-terms.csv",
        DAY2_DIR / "data-domains.yaml",
        DAY2_DIR / "day2-validation.json",
        DAY6_DIR / "denormalization-decision.md",
        DAY6_DIR / "feature-view-spec.yaml",
        DAY6_DIR / "feature-standard-extension.yaml",
        DAY6_DIR / "feature-sample.csv",
        DAY6_DIR / "partition-plan.md",
        DAY6_DIR / "db-catalog.csv",
        DAY6_DIR / "catalog-standard-check.json",
        DAY6_DIR / "day6-validation.json",
        AS_IS_CATALOG,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"입력 파일이 없습니다: {missing}")

    day2_status = read_json(DAY2_DIR / "day2-validation.json")["status"]
    #day6_status = read_json(DAY6_DIR / "day6-validation.json")["status"]
    #catalog_status = read_json(
    #    DAY6_DIR / "catalog-standard-check.json"
    #)["overall_status"]

    if day2_status != "ready":
        raise ValueError("Day 2 표준 사전 상태가 ready가 아닙니다.")
    #if day6_status != "PASS":
    #    raise ValueError("Day 6 검증 상태가 PASS가 아닙니다.")
    #if catalog_status != "PASS":
    #    raise ValueError("Day 6 카탈로그 검증 상태가 PASS가 아닙니다.")


def validate_feature_contract():
    with (DAY6_DIR / "feature-view-spec.yaml").open(encoding="utf-8") as file:
        spec = yaml.safe_load(file)["feature_view"]

    extension_path = DAY6_DIR / spec["standard_extension"]
    with extension_path.open(encoding="utf-8") as file:
        extension = yaml.safe_load(file)
    if extension.get("status") != "approved":
        raise ValueError("Day 6 feature 표준 확장 상태가 approved가 아닙니다.")

    actual_columns = [spec["entity_key"], spec["as_of_column"]]
    actual_columns.extend(feature["name"] for feature in spec["features"])
    if actual_columns != EXPECTED_FEATURE_COLUMNS:
        raise ValueError(
            "Day 6 feature 컬럼이 Day 7의 고정 7개 컬럼과 다릅니다."
        )

    day2_word_ids = {
        row["word_id"]
        for row in read_csv(DAY2_DIR / "standard-words.csv")
    }
    extension_words = extension.get("words", [])
    extension_word_ids = {row["word_id"] for row in extension_words}
    if (
        len(extension_words) != 9
        or len(extension_word_ids) != 9
        or day2_word_ids & extension_word_ids
    ):
        raise ValueError(
            "feature 표준 확장 단어는 Day 2와 충돌하지 않는 고유 9개여야 합니다."
        )
    approved_word_ids = day2_word_ids | extension_word_ids

    with (DAY2_DIR / "data-domains.yaml").open(encoding="utf-8") as file:
        day2_domains = yaml.safe_load(file)["domains"]
    day2_domain_ids = {row["domain_id"] for row in day2_domains}
    extension_domains = extension.get("domains", [])
    extension_domain_ids = {
        row["domain_id"] for row in extension_domains
    }
    if (
        len(extension_domains) != 4
        or len(extension_domain_ids) != 4
        or day2_domain_ids & extension_domain_ids
    ):
        raise ValueError(
            "feature 표준 확장 도메인은 Day 2와 충돌하지 않는 고유 4개여야 합니다."
        )
    approved_domain_ids = day2_domain_ids | extension_domain_ids

    used_word_ids = {
        word_id
        for contract in COLUMN_CONTRACTS.values()
        for word_id in contract["word_ids"]
    }
    used_domain_ids = {
        contract["domain_id"] for contract in COLUMN_CONTRACTS.values()
    }
    missing_word_ids = sorted(used_word_ids - approved_word_ids)
    missing_domain_ids = sorted(used_domain_ids - approved_domain_ids)
    if missing_word_ids or missing_domain_ids:
        raise ValueError(
            "승인되지 않은 feature 표준입니다: "
            f"words={missing_word_ids}, domains={missing_domain_ids}"
        )

    day2_terms = {
        row["physical_name"]: row
        for row in read_csv(DAY2_DIR / "standard-terms.csv")
    }
    member_contract = COLUMN_CONTRACTS["mbr_no"]
    member_term = day2_terms.get("member_id")
    expected_member_term = {
        "logical_name": member_contract["logical_name"],
        "word_ids": "|".join(member_contract["word_ids"]),
        "domain_id": member_contract["domain_id"],
        "nullable": member_contract["nullable"],
    }
    actual_member_term = (
        {
            "logical_name": member_term["logical_term"],
            "word_ids": member_term["word_ids"],
            "domain_id": member_term["domain_id"],
            "nullable": member_term["nullable"],
        }
        if member_term
        else None
    )
    if actual_member_term != expected_member_term:
        raise ValueError("member_id가 Day 2 표준 용어 계약과 다릅니다.")

    extension_binding_rows = extension.get("term_bindings", [])
    extension_bindings = {
        row["physical_name"]: row
        for row in extension_binding_rows
    }
    expected_extension_names = set(EXPECTED_FEATURE_COLUMNS) - {"member_id"}
    if (
        len(extension_binding_rows) != 6
        or len(extension_bindings) != 6
        or set(extension_bindings) != expected_extension_names
    ):
        raise ValueError("Day 6 feature term binding 6개가 컬럼 계약과 다릅니다.")

    extension_domains_by_id = {
        row["domain_id"]: row for row in extension_domains
    }
    bound_extension_domain_ids = set()
    for binding in extension_binding_rows:
        domain = extension_domains_by_id.get(binding["domain_id"])
        if domain is None:
            continue
        bound_extension_domain_ids.add(binding["domain_id"])
        if bool(domain["nullable"]) != bool(binding["nullable"]):
            raise ValueError(
                f"{binding['physical_name']}의 도메인 NULL 규칙이 binding과 다릅니다."
            )
    if bound_extension_domain_ids != extension_domain_ids:
        raise ValueError("승인 확장 도메인 4개가 term binding에 모두 사용되지 않았습니다.")

    contracts_by_standard_name = {
        contract["standard_column_name"]: contract
        for contract in COLUMN_CONTRACTS.values()
    }
    for physical_name in sorted(expected_extension_names):
        contract = contracts_by_standard_name[physical_name]
        binding = extension_bindings[physical_name]
        expected_binding = {
            "logical_name": contract["logical_name"],
            "word_ids": contract["word_ids"],
            "domain_id": contract["domain_id"],
            "nullable": contract["nullable"] == "Y",
        }
        actual_binding = {
            "logical_name": binding["logical_name"],
            "word_ids": binding["word_ids"],
            "domain_id": binding["domain_id"],
            "nullable": binding["nullable"],
        }
        if actual_binding != expected_binding:
            raise ValueError(
                f"{physical_name}의 승인 term binding이 카탈로그 계약과 다릅니다."
            )

    spec_domains = {spec["as_of_column"]: spec["as_of_domain"]}
    spec_domains.update(
        {feature["name"]: feature["domain"] for feature in spec["features"]}
    )
    for physical_name in expected_extension_names:
        contract_domain = contracts_by_standard_name[physical_name]["domain_id"]
        if spec_domains.get(physical_name) != contract_domain:
            raise ValueError(
                f"{physical_name}의 feature spec 도메인과 승인 계약이 다릅니다."
            )


def main():
    require_inputs()
    validate_feature_contract()

    catalog_rows = read_csv(AS_IS_CATALOG)
    results = []
    name_gap_count = 0
    domain_gap_count = 0
    unmapped_count = 0

    for row in catalog_rows:
        source_column = row["column_name"]
        contract = COLUMN_CONTRACTS.get(source_column)

        if contract is None:
            unmapped_count += 1
            results.append(
                {
                    "source_table_name": row["table_name"],
                    "source_column_name": source_column,
                    "translation_status": "UNMAPPED",
                    "gaps": ["standard_mapping"],
                    "domain_differences": [],
                    "status": "GAP",
                }
            )
            continue

        gaps = []
        domain_differences = []

        if source_column != contract["standard_column_name"]:
            gaps.append("physical_name")
            name_gap_count += 1

        for field in ("data_type", "max_length", "nullable"):
            if row[field] != contract[field]:
                domain_differences.append(
                    {
                        "field": field,
                        "as_is_value": row[field],
                        "standard_value": contract[field],
                    }
                )

        if domain_differences:
            gaps.append("domain")
            domain_gap_count += 1

        results.append(
            {
                "source_table_name": row["table_name"],
                "source_column_name": source_column,
                "standard_table_name": STANDARD_TABLE_NAME,
                "standard_column_name": contract["standard_column_name"],
                "logical_name": contract["logical_name"],
                "word_ids": contract["word_ids"],
                "translation_status": "MAPPED",
                "gaps": gaps,
                "domain_differences": domain_differences,
                "status": "PASS" if not gaps else "GAP",
            }
        )

    report = {
        "catalog_file": AS_IS_CATALOG.name,
        "overall_status": "PASS"
        if name_gap_count == 0 and domain_gap_count == 0 and unmapped_count == 0
        else "FAIL",
        "checked_column_count": len(catalog_rows),
        "name_gap_column_count": name_gap_count,
        "domain_gap_column_count": domain_gap_count,
        "unmapped_column_count": unmapped_count,
        "results": results,
    }

    with OUTPUT_REPORT.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"checked_columns={report['checked_column_count']}")
    print(f"name_gap_columns={report['name_gap_column_count']}")
    print(f"domain_gap_columns={report['domain_gap_column_count']}")
    print(f"unmapped_columns={report['unmapped_column_count']}")
    print(f"status={report['overall_status']}")


if __name__ == "__main__":
    main()