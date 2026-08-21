import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
EXPECTED_ENTITY_IDS = {"member", "book", "category", "order", "order-item"}
EXPECTED_IDENTIFIERS = {
    "member": "member_id",
    "book": "book_id",
    "category": "category_code",
    "order": "order_id",
    "order-item": "order_id|book_id",
}
DAY3_INPUT_FILES = [
    "legacy-orders.csv",
    "standardized-orders.csv",
    "rejected-orders.csv",
    "profile-report.json",
    "column-mapping.csv",
    "day3-validation.json",
]
DAY4_ARTIFACT_FILES = [
    "business-rules.md",
    "conceptual-model.md",
    "entity-candidates.csv",
    "identifier-decisions.csv",
    "ai-entity-scope.yaml",
]


def read_csv(file_name):
    path = BASE_DIR / file_name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def read_json(file_name):
    path = BASE_DIR / file_name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        return json.load(file)


missing_day3_inputs = [
    file_name
    for file_name in DAY3_INPUT_FILES
    if not (BASE_DIR / file_name).exists()
]
missing_day4_artifacts = [
    file_name
    for file_name in DAY4_ARTIFACT_FILES
    if not (BASE_DIR / file_name).exists()
]

day3_validation = read_json("day3-validation.json")
day3_report_checks = day3_validation.get("checks", {})
day3_actual_counts = {
    "legacy": len(read_csv("legacy-orders.csv")),
    "standardized": len(read_csv("standardized-orders.csv")),
    "rejected": len(read_csv("rejected-orders.csv")),
}
day3_reported_counts = {
    "legacy": day3_report_checks.get("input_rows"),
    "standardized": day3_report_checks.get("standardized_rows"),
    "rejected": day3_report_checks.get("rejected_rows"),
}
expected_day3_counts = {
    "legacy": 13,
    "standardized": 6,
    "rejected": 7,
}

entity_rows = read_csv("entity-candidates.csv")
accepted_entity_ids = {
    row.get("entity_id", "")
    for row in entity_rows
    if row.get("status", "").lower() == "accepted"
}

identifier_rows = read_csv("identifier-decisions.csv")
selected_identifiers = {
    row.get("entity_id", ""): row.get("candidate_columns", "")
    for row in identifier_rows
    if row.get("selected", "").upper() == "Y"
}

conceptual_text = (
    (BASE_DIR / "conceptual-model.md").read_text(encoding="utf-8")
    if (BASE_DIR / "conceptual-model.md").exists()
    else ""
)
business_text = (
    (BASE_DIR / "business-rules.md").read_text(encoding="utf-8")
    if (BASE_DIR / "business-rules.md").exists()
    else ""
)
ai_scope_text = (
    (BASE_DIR / "ai-entity-scope.yaml").read_text(encoding="utf-8")
    if (BASE_DIR / "ai-entity-scope.yaml").exists()
    else ""
)

checks = {
    "day3_inputs_exist": len(missing_day3_inputs) == 0,
    "day3_validation_ready": (
        day3_validation.get("status") == "ready"
    ),
    "day3_partition_is_13_equals_6_plus_7": (
        day3_actual_counts == expected_day3_counts
        and day3_actual_counts["legacy"]
        == day3_actual_counts["standardized"]
        + day3_actual_counts["rejected"]
    ),
    "day3_report_counts_match_actual": (
        day3_reported_counts == day3_actual_counts
    ),
    "day4_artifacts_exist": len(missing_day4_artifacts) == 0,
    "accepted_entity_ids_are_stable": accepted_entity_ids == EXPECTED_ENTITY_IDS,
    "one_selected_identifier_per_entity": selected_identifiers == EXPECTED_IDENTIFIERS,
    "conceptual_model_mentions_all_entities": all(
        entity_id in conceptual_text for entity_id in EXPECTED_ENTITY_IDS
    ),
    "business_rules_define_source_grain": "원천 grain" in business_text,
    "ai_scope_keeps_all_stable_ids": all(
        entity_id in ai_scope_text for entity_id in EXPECTED_ENTITY_IDS
    ),
    "ai_scope_excludes_member_name": (
        "field: member_name" in ai_scope_text
        and "excluded_fields" in ai_scope_text
    ),
}

status = "ready" if all(checks.values()) else "blocked"
report = {
    "day": 4,
    "status": status,
    "checks": checks,
    "evidence": {
        "missing_day3_inputs": missing_day3_inputs,
        "missing_day4_artifacts": missing_day4_artifacts,
        "day3_validation_status": day3_validation.get("status"),
        "day3_actual_counts": day3_actual_counts,
        "day3_reported_counts": day3_reported_counts,
        "accepted_entity_ids": sorted(accepted_entity_ids),
        "selected_identifiers": selected_identifiers,
    },
    "next_day": {
        "day": 5,
        "purpose": "관계·PK/FK·도메인·정규화 확정",
    },
}

output_path = BASE_DIR / "day4-validation.json"
output_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(f"{status.upper()}: {output_path.name}")
for check_name, passed in checks.items():
    print(f"- {check_name}: {'PASS' if passed else 'FAIL'}")

raise SystemExit(0 if status == "ready" else 1)