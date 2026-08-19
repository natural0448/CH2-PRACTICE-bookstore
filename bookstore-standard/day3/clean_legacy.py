import csv
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DAY2_DIR = BASE_DIR.parent / "day2"

INPUT_FILE = BASE_DIR / "legacy-orders.csv"
MAPPING_FILE = BASE_DIR / "column-mapping.csv"
STANDARDIZED_FILE = BASE_DIR / "standardized-orders.csv"
REJECTED_FILE = BASE_DIR / "rejected-orders.csv"
VALIDATION_FILE = BASE_DIR / "day3-validation.json"

LEGACY_COLUMNS = [
    "mbr_no",
    "mbr_nm",
    "bk_cd",
    "bk_nm",
    "ctg_cd",
    "ctg_nm",
    "ord_no",
    "ord_dtm",
    "ord_st",
    "qty",
    "amt",
]

STANDARD_COLUMNS = [
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
]

EXPECTED_MAPPING = dict(zip(LEGACY_COLUMNS, STANDARD_COLUMNS))

STATUS_MAP = {
    "PAID": "PAID",
    "결제완료": "PAID",
    "SHIPPING": "SHIPPING",
    "배송중": "SHIPPING",
    "DONE": "DONE",
    "완료": "DONE",
    "CANCEL": "CANCELLED",
    "CANCELLED": "CANCELLED",
    "취소": "CANCELLED",
}

ALLOWED_STATUS_CODES = {"PAID", "SHIPPING", "DONE", "CANCELLED"}

CATEGORY_NAMES = {
    "C01": "데이터",
    "C02": "프로그래밍",
    "C03": "AI",
    "C04": "클라우드",
    "C05": "통계",
}

DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
)

ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{0,19}$")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames or [], list(reader)


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def strip_text(value):
    return (value or "").strip()


def parse_datetime(value):
    for date_format in DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None


def parse_integer(value):
    try:
        return int(value)
    except ValueError:
        return None


def parse_money(value):
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


required_day2_files = [
    "legacy-columns.csv",
    "standard-words.csv",
    "standard-terms.csv",
    "naming-rules.yaml",
    "data-domains.yaml",
    "day2-validation.json",
]

missing_day2_files = [
    filename for filename in required_day2_files if not (DAY2_DIR / filename).exists()
]
if missing_day2_files:
    raise FileNotFoundError(f"Day 2 입력 파일이 없습니다: {missing_day2_files}")

with (DAY2_DIR / "day2-validation.json").open(encoding="utf-8") as file:
    day2_validation = json.load(file)
if day2_validation.get("status") != "ready":
    raise ValueError("Day 2 표준 사전 상태가 ready가 아닙니다.")

_, day2_legacy_rows = read_csv(DAY2_DIR / "legacy-columns.csv")
day2_legacy_columns = {row["legacy_column"] for row in day2_legacy_rows}
if day2_legacy_columns != set(LEGACY_COLUMNS):
    raise ValueError("Day 2 레거시 컬럼 목록과 Day 3 입력 계약이 다릅니다.")

_, day2_word_rows = read_csv(DAY2_DIR / "standard-words.csv")
if not day2_word_rows:
    raise ValueError("Day 2 표준 단어 사전이 비어 있습니다.")

_, day2_term_rows = read_csv(DAY2_DIR / "standard-terms.csv")
day2_term_domains = {
    row["physical_name"]: row["domain_id"]
    for row in day2_term_rows
}
if set(day2_term_domains) != set(STANDARD_COLUMNS):
    raise ValueError("Day 2 표준 용어와 Day 3 표준 컬럼 집합이 다릅니다.")

naming_text = (DAY2_DIR / "naming-rules.yaml").read_text(encoding="utf-8")
pattern_match = re.search(
    r"^\s*physical_name_pattern:\s*['\"](.+)['\"]\s*$",
    naming_text,
    re.MULTILINE,
)
if pattern_match is None:
    raise ValueError("Day 2 명명 규칙에서 물리명 패턴을 찾지 못했습니다.")
physical_name_pattern = pattern_match.group(1)
if not all(re.fullmatch(physical_name_pattern, name) for name in STANDARD_COLUMNS):
    raise ValueError("표준 컬럼명이 Day 2 명명 규칙을 위반합니다.")

domain_text = (DAY2_DIR / "data-domains.yaml").read_text(encoding="utf-8")
day2_domain_ids = set(
    re.findall(r"^\s*- domain_id:\s*([A-Z0-9_]+)\s*$", domain_text, re.MULTILINE)
)

_, mapping_rows = read_csv(MAPPING_FILE)
actual_mapping = {
    row["legacy_column"]: row["standard_column"]
    for row in mapping_rows
}
if actual_mapping != EXPECTED_MAPPING:
    raise ValueError("column-mapping.csv가 Day 2의 11개 표준 컬럼과 다릅니다.")

for row in mapping_rows:
    standard_column = row["standard_column"]
    if row["domain_id"] not in day2_domain_ids:
        raise ValueError(f"등록되지 않은 도메인입니다: {row['domain_id']}")
    if day2_term_domains[standard_column] != row["domain_id"]:
        raise ValueError(f"Day 2와 도메인이 다릅니다: {standard_column}")

input_columns, source_rows = read_csv(INPUT_FILE)
if input_columns != LEGACY_COLUMNS:
    raise ValueError("legacy-orders.csv의 헤더 순서가 입력 계약과 다릅니다.")

standardized_rows = []
rejected_rows = []
seen_business_keys = set()

for raw_row in source_rows:
    source = {column: strip_text(raw_row[column]) for column in LEGACY_COLUMNS}

    member_id = source["mbr_no"].upper()
    member_name = source["mbr_nm"]
    book_id = source["bk_cd"].upper()
    book_name = source["bk_nm"]
    category_code = source["ctg_cd"].upper()
    category_name = CATEGORY_NAMES.get(category_code, source["ctg_nm"])
    order_id = source["ord_no"].upper()
    order_datetime = parse_datetime(source["ord_dtm"])
    order_status_code = STATUS_MAP.get(source["ord_st"].upper())
    quantity = parse_integer(source["qty"])
    unit_price = parse_money(source["amt"])

    reasons = []

    required_values = {
        "member_id": member_id,
        "member_name": member_name,
        "book_id": book_id,
        "book_name": book_name,
        "category_code": category_code,
        "category_name": category_name,
        "order_id": order_id,
    }
    for field_name, value in required_values.items():
        if not value:
            reasons.append(f"missing_required:{field_name}")

    for field_name, value in {
        "member_id": member_id,
        "book_id": book_id,
        "order_id": order_id,
    }.items():
        if value and not ID_PATTERN.fullmatch(value):
            reasons.append(f"invalid_format:{field_name}")

    if category_code and category_code not in CATEGORY_NAMES:
        reasons.append("unmapped_value:category_code")
    if order_datetime is None:
        reasons.append("invalid_format:order_datetime")
    if order_status_code is None:
        reasons.append("unmapped_value:order_status_code")
    if quantity is None or quantity < 1 or quantity > 999:
        reasons.append("out_of_domain:quantity")
    if unit_price is None or unit_price < 0:
        reasons.append("out_of_domain:unit_price")

    business_key = (order_id, book_id)
    if not reasons:
        if business_key in seen_business_keys:
            reasons.append("duplicate_business_key:order_id+book_id")
        else:
            seen_business_keys.add(business_key)

    if reasons:
        rejected_rows.append({**raw_row, "rejection_reason": "|".join(reasons)})
        continue

    standardized_rows.append(
        {
            "member_id": member_id,
            "member_name": member_name,
            "book_id": book_id,
            "book_name": book_name,
            "category_code": category_code,
            "category_name": category_name,
            "order_id": order_id,
            "order_datetime": order_datetime,
            "order_status_code": order_status_code,
            "quantity": quantity,
            "unit_price": format(unit_price, ".2f"),
        }
    )

write_csv(STANDARDIZED_FILE, STANDARD_COLUMNS, standardized_rows)
write_csv(REJECTED_FILE, LEGACY_COLUMNS + ["rejection_reason"], rejected_rows)

output_columns, output_rows = read_csv(STANDARDIZED_FILE)
output_key_counts = Counter(
    (row["order_id"], row["book_id"])
    for row in output_rows
)

checks = {
    "day2_input_status_ready": day2_validation.get("status") == "ready",
    "mapping_matches_day2_terms": set(day2_term_domains) == set(STANDARD_COLUMNS),
    "input_rows": len(source_rows),
    "standardized_rows": len(standardized_rows),
    "rejected_rows": len(rejected_rows),
    "row_balance": len(source_rows) == len(standardized_rows) + len(rejected_rows),
    "expected_partition_counts": len(standardized_rows) == 6 and len(rejected_rows) == 7,
    "standard_column_order": output_columns == STANDARD_COLUMNS,
    "no_duplicate_business_key": all(count == 1 for count in output_key_counts.values()),
    "all_status_codes_allowed": all(
        row["order_status_code"] in ALLOWED_STATUS_CODES for row in output_rows
    ),
    "all_quantities_positive": all(int(row["quantity"]) > 0 for row in output_rows),
    "all_unit_prices_non_negative": all(
        Decimal(row["unit_price"]) >= 0 for row in output_rows
    ),
}

errors = [
    name
    for name, result in checks.items()
    if isinstance(result, bool) and not result
]

validation = {
    "status": "ready" if not errors else "blocked",
    "checks": checks,
    "errors": errors,
    "artifacts": [
        "legacy-orders.csv",
        "profile-report.json",
        "column-mapping.csv",
        "standardized-orders.csv",
        "rejected-orders.csv",
        "day3-validation.json",
    ],
}

with VALIDATION_FILE.open("w", encoding="utf-8") as file:
    json.dump(validation, file, ensure_ascii=False, indent=2)
    file.write("\n")

print(f"입력 행: {len(source_rows)}")
print(f"표준화 성공: {len(standardized_rows)}")
print(f"격리: {len(rejected_rows)}")
print(f"검증 상태: {validation['status']}")