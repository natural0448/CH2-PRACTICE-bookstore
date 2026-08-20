from csv import DictReader
import json
from pathlib import Path


required_files = [
    "legacy-orders.csv",
    "standardized-orders.csv",
    "rejected-orders.csv",
    "profile-report.json",
    "column-mapping.csv",
    "day3-validation.json",
]

missing_files = []
for file_name in required_files:
    path = Path(file_name)
    exists = path.is_file()
    print(f"{file_name}: {'있음' if exists else '없음'}")
    if not exists:
        missing_files.append(file_name)


def read_csv_rows(file_name):
    path = Path(file_name)
    if not path.is_file():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def read_json(file_name):
    path = Path(file_name)
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as file:
        return json.load(file)


legacy_columns, legacy_rows = read_csv_rows("legacy-orders.csv")
standardized_columns, standardized_rows = read_csv_rows(
    "standardized-orders.csv"
)
_, rejected_rows = read_csv_rows("rejected-orders.csv")
day3_validation = read_json("day3-validation.json")
day3_checks = day3_validation.get("checks", {})

actual_counts = {
    "legacy": len(legacy_rows),
    "standardized": len(standardized_rows),
    "rejected": len(rejected_rows),
}
reported_counts = {
    "legacy": day3_checks.get("input_rows"),
    "standardized": day3_checks.get("standardized_rows"),
    "rejected": day3_checks.get("rejected_rows"),
}

gate_checks = {
    "day3_inputs_exist": not missing_files,
    "day3_validation_ready": (
        day3_validation.get("status") == "ready"
    ),
    "actual_partition_is_13_equals_6_plus_7": (
        actual_counts
        == {"legacy": 13, "standardized": 6, "rejected": 7}
        and actual_counts["legacy"]
        == actual_counts["standardized"] + actual_counts["rejected"]
    ),
    "day3_report_counts_match_actual": reported_counts == actual_counts,
}

print("컬럼:", standardized_columns)
print("표준화 행 수:", actual_counts["standardized"])
print("격리 행 수:", actual_counts["rejected"])
print("입력 행 수:", actual_counts["legacy"])
print("Day 3 상태:", day3_validation.get("status", "없음"))
print(
    "첫 행:",
    standardized_rows[0] if standardized_rows else "데이터 없음",
)
for check_name, passed in gate_checks.items():
    print(f"- {check_name}: {'PASS' if passed else 'FAIL'}")

raise SystemExit(0 if all(gate_checks.values()) else 1)