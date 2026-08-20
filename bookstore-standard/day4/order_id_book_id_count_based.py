import csv
from collections import Counter


with open("standardized-orders.csv", encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

item_keys = [(row["order_id"], row["book_id"]) for row in rows]
key_counts = Counter(item_keys)
duplicated_keys = sorted(key for key, count in key_counts.items() if count > 1)

if duplicated_keys:
    print("FAIL: 복합 식별자가 중복됩니다.")
else:
    print(f"PASS: {len(item_keys)}개 주문항목을 모두 구분했습니다.")