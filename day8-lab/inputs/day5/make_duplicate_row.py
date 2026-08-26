from pathlib import Path


source_path = Path("standardized-orders.csv")
broken_path = Path("standardized-orders-broken.csv")

lines = source_path.read_text(encoding="utf-8-sig").splitlines()
if len(lines) < 2:
    raise SystemExit("데이터 행이 없어 중복 오류를 만들 수 없습니다.")

broken_lines = lines + [lines[1]]
broken_path.write_text("\n".join(broken_lines) + "\n", encoding="utf-8")
print(f"created: {broken_path}")