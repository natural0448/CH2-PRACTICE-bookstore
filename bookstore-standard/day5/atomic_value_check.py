import csv


multi_value_separator = "|"
issues = []

with open("standardized-orders.csv", encoding="utf-8-sig", newline="") as file:
    for line_number, row in enumerate(csv.DictReader(file), start=2):
        for column_name, value in row.items():
            if multi_value_separator in value:
                issues.append(
                    {
                        "line": line_number,
                        "column": column_name,
                        "value": value,
                    }
                )

print("다중값 의심 건수:", len(issues))
for issue in issues:
    print(issue)