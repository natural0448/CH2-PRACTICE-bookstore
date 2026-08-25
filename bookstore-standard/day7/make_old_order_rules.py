from pathlib import Path

import yaml


source_path = Path("quality-rules.yaml")
target_path = Path("quality-rules-old-order.yaml")
with source_path.open(encoding="utf-8") as file:
    rules = yaml.safe_load(file)

old_order_source = "standardized-orders-with-old.csv"
reference_rules = rules["dimensions"]["referential_integrity"]
reference_rules["member_reference"]["source_file"] = old_order_source
reference_rules["category_reference"]["source_file"] = old_order_source
rules["dimensions"]["point_in_time"]["source_file"] = old_order_source

with target_path.open("w", encoding="utf-8") as file:
    yaml.safe_dump(rules, file, allow_unicode=True, sort_keys=False)

print(target_path)