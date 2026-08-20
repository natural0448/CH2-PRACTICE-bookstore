import csv
from collections import Counter


with open("standardized-orders.csv", encoding="utf-8-sig", newline="") as file:
    rows = list(csv.DictReader(file))

order_id_counts = Counter(row["order_id"] for row in rows)
duplicated_order_ids = sorted(
    order_id for order_id, count in order_id_counts.items() if count > 1
)

if duplicated_order_ids:
    print("FAIL: order_id만으로 주문항목을 구분할 수 없습니다.")
    print("중복 주문 ID:", duplicated_order_ids)
else:
    print("PASS: order_id가 주문항목마다 유일합니다.")