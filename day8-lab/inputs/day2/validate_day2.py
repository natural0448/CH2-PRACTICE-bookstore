import csv
import json
import re
import sys
import traceback
from collections import defaultdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPORT_FILENAME = "day2-validation.json"

LINEAGE_RELATIVE_PATH = (
    "../day2-mission-notes/unit-price-lineage.md"
)

LINEAGE_PATH = (
    BASE_DIR.parent
    / "day2-mission-notes"
    / "unit-price-lineage.md"
)

EXPECTED_COLUMNS = {
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

ARTIFACTS = [
    "legacy-columns.csv",
    "standard-words.csv",
    "standard-terms.csv",
    "naming-rules.yaml",
    "data-domains.yaml",
    REPORT_FILENAME,
    LINEAGE_RELATIVE_PATH,
]


def clean(value):
    """None을 빈 문자열로 바꾸고 앞뒤 공백을 제거합니다."""
    return str(value or "").strip()


def split_pipe(value):
    """A|B|C 형태의 값을 집합으로 변환합니다."""
    return {
        item.strip()
        for item in clean(value).split("|")
        if item.strip()
    }


def read_csv(filename, required_columns):
    path = BASE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"{filename}: 파일을 찾을 수 없습니다."
        )

    rows = []

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"{filename}: CSV 헤더가 없습니다."
            )

        actual_columns = {
            clean(column)
            for column in reader.fieldnames
            if column is not None
        }

        missing_columns = (
            set(required_columns) - actual_columns
        )

        if missing_columns:
            raise ValueError(
                f"{filename}: 필수 컬럼이 없습니다: "
                f"{sorted(missing_columns)}"
            )

        for row in reader:
            # 헤더보다 데이터 열이 더 많은 경우
            if None in row:
                raise ValueError(
                    f"{filename}:{reader.line_num}: "
                    "헤더보다 데이터 열이 많습니다."
                )

            row["__file__"] = filename
            row["__line__"] = reader.line_num
            rows.append(row)

    return rows


def read_domain_ids(filename):
    path = BASE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"{filename}: 파일을 찾을 수 없습니다."
        )

    text = path.read_text(encoding="utf-8")

    domain_ids = set(
        re.findall(
            r"^\s*-\s*domain_id:\s*([A-Z0-9_]+)\s*$",
            text,
            re.MULTILINE,
        )
    )

    if not domain_ids:
        raise ValueError(
            f"{filename}: domain_id를 찾지 못했습니다."
        )

    return domain_ids


def read_physical_name_pattern(filename):
    path = BASE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"{filename}: 파일을 찾을 수 없습니다."
        )

    text = path.read_text(encoding="utf-8")

    # 작은따옴표와 큰따옴표 모두 처리
    match = re.search(
        r"""^\s*physical_name_pattern:\s*(['"])(.+)\1\s*$""",
        text,
        re.MULTILINE,
    )

    if match is None:
        raise ValueError(
            f"{filename}: physical_name_pattern을 "
            "찾지 못했습니다."
        )

    pattern = match.group(2)

    # 정규식 자체가 올바른지도 검사
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(
            f"{filename}: physical_name_pattern이 "
            f"올바른 정규식이 아닙니다: {error}"
        ) from error

    return pattern


def add_error(
    errors,
    checks,
    check_name,
    message,
    row=None,
    field=None,
    value=None,
    related_lines=None,
):
    checks[check_name] = False

    error = {
        "check": check_name,
        "message": message,
    }

    if row is not None:
        error["file"] = row.get("__file__")
        error["line"] = row.get("__line__")

    if field is not None:
        error["field"] = field

    if value is not None:
        error["value"] = value

    if related_lines:
        error["related_lines"] = related_lines

    errors.append(error)


def validate_unique(
    rows,
    field,
    check_name,
    checks,
    errors,
):
    checks[check_name] = True

    value_locations = defaultdict(list)

    for row in rows:
        value = clean(row.get(field))
        value_locations[value].append(row)

    for value, duplicate_rows in value_locations.items():
        if len(duplicate_rows) <= 1:
            continue

        lines = [
            row["__line__"]
            for row in duplicate_rows
        ]

        add_error(
            errors=errors,
            checks=checks,
            check_name=check_name,
            message=(
                f"중복 값입니다. 발견된 행: {lines}"
            ),
            row=duplicate_rows[0],
            field=field,
            value=value,
            related_lines=lines,
        )

def validate_unit_price_lineage(
    checks,
    errors,
):
    check_name = "unit_price_lineage_complete"
    checks[check_name] = True

    if not LINEAGE_PATH.exists():
        add_error(
            errors=errors,
            checks=checks,
            check_name=check_name,
            message="unit-price-lineage.md 파일이 없습니다.",
            row={
                "__file__": LINEAGE_RELATIVE_PATH,
                "__line__": 1,
            },
        )
        return

    content = LINEAGE_PATH.read_text(
        encoding="utf-8"
    )

    lines = content.splitlines()

    # Markdown 표 안의 \|를 실제 | 값으로 취급
    semantic_content = content.replace(
        r"\|",
        "|",
    )

    required_values = [
        "amt",
        "단가",
        "UNIT|PRICE",
        "unit_price",
        "MONEY_12_2",
    ]

    missing_values = [
        value
        for value in required_values
        if value not in semantic_content
    ]

    if missing_values:
        add_error(
            errors=errors,
            checks=checks,
            check_name=check_name,
            message=(
                "필수 연결값이 누락됐습니다: "
                f"{missing_values}"
            ),
            row={
                "__file__": LINEAGE_RELATIVE_PATH,
                "__line__": 1,
            },
            field="lineage_values",
            value="|".join(missing_values),
        )

    # 헤더와 구분선을 제외한 데이터 행
    data_rows = []

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        stripped = line.strip()

        if not stripped.startswith("|"):
            continue

        if "레거시 컬럼" in stripped:
            continue

        if re.match(
            r"^\|\s*:?-{3,}",
            stripped,
        ):
            continue

        data_rows.append(
            (line_number, stripped)
        )

    if len(data_rows) != 1:
        add_error(
            errors=errors,
            checks=checks,
            check_name=check_name,
            message=(
                "표의 데이터 행은 정확히 "
                f"1개여야 합니다. 현재: {len(data_rows)}개"
            ),
            row={
                "__file__": LINEAGE_RELATIVE_PATH,
                "__line__": 1,
            },
            field="table_data_rows",
            value=len(data_rows),
        )

    expected_last_line = (
        "레거시 설명의 “한 권 가격”이 "
        "`unit_price` 결정 근거입니다."
    )

    non_empty_lines = [
        line.strip()
        for line in lines
        if line.strip()
    ]

    actual_last_line = (
        non_empty_lines[-1]
        if non_empty_lines
        else ""
    )

    if actual_last_line != expected_last_line:
        add_error(
            errors=errors,
            checks=checks,
            check_name=check_name,
            message=(
                "마지막 업무 근거 문장이 "
                "지정된 문장과 다릅니다."
            ),
            row={
                "__file__": LINEAGE_RELATIVE_PATH,
                "__line__": len(lines),
            },
            field="last_line",
            value=actual_last_line,
        )

def run_validation():
    legacy_rows = read_csv(
        "legacy-columns.csv",
        required_columns={
            "legacy_column",
        },
    )

    word_rows = read_csv(
        "standard-words.csv",
        required_columns={
            "word_id",
        },
    )

    term_rows = read_csv(
        "standard-terms.csv",
        required_columns={
            "physical_name",
            "logical_term",
            "source_columns",
            "word_ids",
            "domain_id",
            "definition",
        },
    )

    domain_ids = read_domain_ids(
        "data-domains.yaml"
    )

    physical_name_pattern = (
        read_physical_name_pattern(
            "naming-rules.yaml"
        )
    )

    legacy_columns = {
        clean(row["legacy_column"])
        for row in legacy_rows
        if clean(row["legacy_column"])
    }

    word_ids = {
        clean(row["word_id"])
        for row in word_rows
        if clean(row["word_id"])
    }

    physical_names = [
        clean(row["physical_name"])
        for row in term_rows
    ]

    logical_terms = [
        clean(row["logical_term"])
        for row in term_rows
    ]

    mapped_sources = {
        source
        for row in term_rows
        for source in split_pipe(
            row["source_columns"]
        )
    }

    checks = {
        "legacy_column_count": len(legacy_rows),
        "standard_word_count": len(word_rows),
        "standard_term_count": len(term_rows),
        "all_legacy_columns_mapped": True,
        "all_term_words_exist": True,
        "all_term_domains_exist": True,
        "all_physical_names_follow_rule": True,
        "physical_names_are_unique": True,
        "logical_terms_are_unique": True,
        "expected_standard_columns_match": True,
        "amt_is_resolved_as_unit_price": True,
    }

    errors = []

    # 1. 레거시 컬럼 매핑 검사
    missing_mappings = (
        legacy_columns - mapped_sources
    )

    for legacy_column in sorted(missing_mappings):
        source_row = next(
            row
            for row in legacy_rows
            if clean(row["legacy_column"])
            == legacy_column
        )

        add_error(
            errors=errors,
            checks=checks,
            check_name="all_legacy_columns_mapped",
            message=(
                "표준 용어에 매핑되지 않은 "
                "레거시 컬럼입니다."
            ),
            row=source_row,
            field="legacy_column",
            value=legacy_column,
        )

    # 표준 용어에는 있지만 레거시에는 없는 컬럼
    unknown_sources = (
        mapped_sources - legacy_columns
    )

    for source in sorted(unknown_sources):
        matching_rows = [
            row
            for row in term_rows
            if source
            in split_pipe(row["source_columns"])
        ]

        for row in matching_rows:
            add_error(
                errors=errors,
                checks=checks,
                check_name="all_legacy_columns_mapped",
                message=(
                    "legacy-columns.csv에 없는 "
                    "source_column입니다."
                ),
                row=row,
                field="source_columns",
                value=source,
            )

    # 2. word_id 존재 여부 검사
    for row in term_rows:
        term_word_ids = split_pipe(
            row["word_ids"]
        )

        missing_word_ids = (
            term_word_ids - word_ids
        )

        for word_id in sorted(missing_word_ids):
            add_error(
                errors=errors,
                checks=checks,
                check_name="all_term_words_exist",
                message=(
                    f"정의되지 않은 word_id입니다: "
                    f"{word_id}"
                ),
                row=row,
                field="word_ids",
                value=word_id,
            )

    # 3. domain_id 존재 여부 검사
    for row in term_rows:
        domain_id = clean(row["domain_id"])

        if domain_id not in domain_ids:
            add_error(
                errors=errors,
                checks=checks,
                check_name="all_term_domains_exist",
                message=(
                    f"존재하지 않는 domain_id입니다: "
                    f"{domain_id}"
                ),
                row=row,
                field="domain_id",
                value=domain_id,
            )

    # 4. 물리명 규칙 검사
    for row in term_rows:
        physical_name = clean(
            row["physical_name"]
        )

        if re.fullmatch(
            physical_name_pattern,
            physical_name,
        ) is None:
            add_error(
                errors=errors,
                checks=checks,
                check_name=(
                    "all_physical_names_follow_rule"
                ),
                message=(
                    "물리명이 명명 규칙과 "
                    "일치하지 않습니다. "
                    f"규칙: {physical_name_pattern}"
                ),
                row=row,
                field="physical_name",
                value=physical_name,
            )

    # 5. 물리명과 논리명 중복 검사
    validate_unique(
        rows=term_rows,
        field="physical_name",
        check_name="physical_names_are_unique",
        checks=checks,
        errors=errors,
    )

    validate_unique(
        rows=term_rows,
        field="logical_term",
        check_name="logical_terms_are_unique",
        checks=checks,
        errors=errors,
    )

    # 6. 예상 표준 컬럼 검사
    actual_columns = set(physical_names)

    missing_expected_columns = (
        EXPECTED_COLUMNS - actual_columns
    )

    for column in sorted(
        missing_expected_columns
    ):
        add_error(
            errors=errors,
            checks=checks,
            check_name=(
                "expected_standard_columns_match"
            ),
            message="필수 표준 컬럼이 누락되었습니다.",
            field="physical_name",
            value=column,
        )

    unexpected_columns = (
        actual_columns - EXPECTED_COLUMNS
    )

    for column in sorted(unexpected_columns):
        source_row = next(
            row
            for row in term_rows
            if clean(row["physical_name"])
            == column
        )

        add_error(
            errors=errors,
            checks=checks,
            check_name=(
                "expected_standard_columns_match"
            ),
            message=(
                "EXPECTED_COLUMNS에 없는 "
                "표준 컬럼입니다."
            ),
            row=source_row,
            field="physical_name",
            value=column,
        )

    # 7. amt → unit_price 해소 여부 검사
    amt_rows = [
        row
        for row in term_rows
        if "amt"
        in split_pipe(row["source_columns"])
    ]

    amt_resolved = any(
        clean(row["physical_name"])
        == "unit_price"
        and "한 권 가격"
        in clean(row["definition"])
        for row in amt_rows
    )

    if not amt_resolved:
        if amt_rows:
            for row in amt_rows:
                add_error(
                    errors=errors,
                    checks=checks,
                    check_name=(
                        "amt_is_resolved_as_unit_price"
                    ),
                    message=(
                        "amt가 unit_price로 매핑되고 "
                        "definition에 '한 권 가격'이 "
                        "포함되어야 합니다."
                    ),
                    row=row,
                    field="source_columns",
                    value="amt",
                )
        else:
            add_error(
                errors=errors,
                checks=checks,
                check_name=(
                    "amt_is_resolved_as_unit_price"
                ),
                message=(
                    "source_columns에 amt가 포함된 "
                    "표준 용어가 없습니다."
                ),
                field="source_columns",
                value="amt",
            )

    validate_unit_price_lineage(
        checks=checks,
        errors=errors,
    )

    failed_checks = sorted({
        error["check"]
        for error in errors
    })


    return {
        "status": (
            "ready"
            if not errors
            else "blocked"
        ),
        "checks": checks,
        "failed_checks": failed_checks,
        "error_count": len(errors),
        "errors": errors,
        "artifacts": ARTIFACTS,
    }


def save_report(report):
    output_path = BASE_DIR / REPORT_FILENAME

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    return output_path


def print_report(report, output_path):
    print("=" * 70)
    print(f'검증 상태: {report["status"]}')
    print(f'오류 개수: {report["error_count"]}')
    print(f"보고서: {output_path}")
    print("=" * 70)

    if not report["errors"]:
        print("모든 검증을 통과했습니다.")
        return

    for index, error in enumerate(
        report["errors"],
        start=1,
    ):
        file_name = error.get("file")
        line = error.get("line")

        if file_name and line:
            location = f"{file_name}:{line}"
        elif file_name:
            location = file_name
        else:
            location = "위치 정보 없음"

        print(
            f'\n[{index}] FAIL: {error["check"]}'
        )
        print(f"    위치: {location}")
        print(
            f'    필드: {error.get("field", "-")}'
        )
        print(
            f'    값: {error.get("value", "-")}'
        )
        print(f'    이유: {error["message"]}')

        related_lines = error.get(
            "related_lines"
        )

        if related_lines:
            print(
                f"    관련 행: {related_lines}"
            )


def main():
    try:
        report = run_validation()

    except Exception as error:
        # 파일 누락, CSV 구조 오류, 정규식 오류 등
        # 검증 자체가 실행되지 못한 경우
        report = {
            "status": "blocked",
            "checks": {},
            "failed_checks": [
                "validator_runtime_error"
            ],
            "error_count": 1,
            "errors": [
                {
                    "check": (
                        "validator_runtime_error"
                    ),
                    "message": str(error),
                    "exception_type": (
                        type(error).__name__
                    ),
                    "traceback": (
                        traceback.format_exc()
                    ),
                }
            ],
            "artifacts": ARTIFACTS,
        }

    output_path = save_report(report)
    print_report(report, output_path)

    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())