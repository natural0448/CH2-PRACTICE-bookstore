import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


# 현재 Python 파일이 위치한 디렉터리를 기준 경로로 사용한다.
# 실행 위치가 달라져도 CSV/JSON 파일을 안정적으로 찾기 위함이다.
BASE_DIR = Path(__file__).resolve().parent

# 분석할 레거시 주문 데이터
INPUT_FILE = BASE_DIR / "legacy-orders.csv"

# 데이터 프로파일링 결과를 저장할 JSON 파일
OUTPUT_FILE = BASE_DIR / "profile-report.json"


# 주문일시(ord_dtm)에서 허용할 날짜/시간 형식을 정의한다.
# 현재 데이터에 여러 날짜 표현이 섞여 있다는 것을 전제로 한다.
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M",      # 예: 2026-08-19 10:30
    "%Y/%m/%d %H:%M",      # 예: 2026/08/19 10:30
    "%Y-%m-%dT%H:%M:%S",   # 예: 2026-08-19T10:30:00
)


# 주문상태(ord_st)에서 정상적인 값으로 인정할 목록이다.
# 한글/영문 값이 혼재된 레거시 데이터를 검사하기 위해 사용한다.
KNOWN_STATUS_VALUES = {
    "PAID",
    "결제완료",
    "SHIPPING",
    "배송중",
    "DONE",
    "완료",
    "CANCEL",
    "CANCELLED",
    "취소",
}


def clean_text(value):
    """
    문자열 앞뒤의 공백을 제거한다.

    CSV에서 값이 없으면 None이 들어올 가능성도 있으므로
    (value or "")를 사용하여 빈 문자열로 변환한 뒤 strip() 한다.
    """
    return (value or "").strip()


def is_valid_datetime(value):
    """
    전달받은 문자열이 DATETIME_FORMATS 중
    하나라도 만족하는 정상적인 날짜/시간인지 검사한다.
    """

    # 허용된 날짜 형식을 하나씩 시도한다.
    for date_format in DATETIME_FORMATS:
        try:
            # 문자열을 실제 datetime 객체로 변환할 수 있으면 정상 값이다.
            datetime.strptime(value, date_format)
            return True

        except ValueError:
            # 현재 형식과 맞지 않으면 다음 형식을 시도한다.
            continue

    # 모든 형식에 실패했다면 잘못된 날짜/시간 값이다.
    return False



# ---------------------------------------------------------
# 1. CSV 파일 읽기
# ---------------------------------------------------------

with INPUT_FILE.open(encoding="utf-8", newline="") as file:

    # 첫 번째 행을 컬럼명으로 사용하는 DictReader를 생성한다.
    #
    # 예:
    # mbr_no, bk_cd, qty
    # M001, B001, 2
    #
    # ↓
    #
    # {
    #   "mbr_no": "M001",
    #   "bk_cd": "B001",
    #   "qty": "2"
    # }
    reader = csv.DictReader(file)

    # CSV의 컬럼명 목록을 가져온다.
    # fieldnames가 None인 경우를 대비하여 빈 리스트를 사용한다.
    columns = reader.fieldnames or []

    # CSV의 모든 행을 메모리에 읽어 리스트로 만든다.
    rows = list(reader)


# ---------------------------------------------------------
# 2. 컬럼별 결측값 개수 확인
# ---------------------------------------------------------

missing_counts = {
    column: sum(
        not clean_text(row[column])
        for row in rows
    )
    for column in columns
}

# 예:
#
# {
#     "mbr_no": 1,
#     "bk_cd": 0,
#     "qty": 2
# }
#
# 공백("   ")도 clean_text() 이후 빈 문자열이 되므로
# 결측값으로 처리된다.


# ---------------------------------------------------------
# 3. 컬럼별 고유값(distinct value) 개수 확인
# ---------------------------------------------------------

distinct_counts = {
    column: len(
        {
            clean_text(row[column])
            for row in rows
            if clean_text(row[column])
        }
    )
    for column in columns
}

# 예:
#
# 회원번호 데이터:
#
# M001
# M001
# M002
# M003
#
# distinct_count = 3
#
# 데이터의 중복 정도나 컬럼의 식별자 후보 여부를 판단할 때
# 참고할 수 있다.


# ---------------------------------------------------------
# 4. 완전히 동일한 행의 중복 검사
# ---------------------------------------------------------

exact_row_counter = Counter(
    tuple(
        clean_text(row[column])
        for column in columns
    )
    for row in rows
)

# 각 행을 tuple로 만들어 등장 횟수를 센다.
#
# 예:
#
# ("M001", "B001", "2") → 2회
# ("M002", "B003", "1") → 1회


duplicate_exact_rows = sum(
    count - 1
    for count in exact_row_counter.values()
    if count > 1
)

# 동일한 행이 2번 존재하면 중복 행은 1건,
# 동일한 행이 3번 존재하면 중복 행은 2건으로 계산한다.
#
# 즉 최초 1건은 정상 행으로 보고
# 추가로 발생한 행의 개수를 중복으로 계산한다.


# ---------------------------------------------------------
# 5. 업무 식별자(Business Key) 중복 검사
# ---------------------------------------------------------

business_key_counter = Counter(
    (
        # 주문번호
        clean_text(row["ord_no"]).upper(),

        # 도서코드
        clean_text(row["bk_cd"]).upper(),
    )
    for row in rows

    # 주문번호와 도서코드가 모두 존재하는 경우만 검사한다.
    if clean_text(row["ord_no"])
    and clean_text(row["bk_cd"])
)

# 여기서는 다음 업무 규칙을 가정하고 있다.
#
# "하나의 주문에서 같은 도서는 한 번만 나타난다."
#
# 따라서
#
# ord_no + bk_cd
#
# 조합을 후보 업무 식별자(candidate business key)로 보고
# 중복되는지 검사한다.


duplicate_business_keys = [
    {
        # 결과 JSON에서는 레거시 컬럼명 대신
        # 의미가 명확한 이름을 사용한다.
        "order_id": order_id,
        "book_id": book_id,
        "count": count,
    }

    for (order_id, book_id), count
    in sorted(business_key_counter.items())

    # 같은 업무 키가 두 번 이상 존재하는 경우만 결과에 포함한다.
    if count > 1
]


# ---------------------------------------------------------
# 6. 잘못된 값의 개수를 저장할 변수 초기화
# ---------------------------------------------------------

invalid_order_datetime = 0
unknown_order_status = 0
non_positive_quantity = 0
negative_unit_price = 0


# ---------------------------------------------------------
# 7. 각 행의 값 품질 검사
# ---------------------------------------------------------

for row in rows:

    # -----------------------------
    # 주문일시 검사
    # -----------------------------

    order_datetime = clean_text(row["ord_dtm"])

    # 정의해둔 DATETIME_FORMATS에 맞지 않는 날짜라면
    # 오류 데이터로 계산한다.
    if not is_valid_datetime(order_datetime):
        invalid_order_datetime += 1


    # -----------------------------
    # 주문상태 검사
    # -----------------------------

    # 앞뒤 공백을 제거하고 대문자로 통일한다.
    #
    # paid → PAID
    # Paid → PAID
    order_status = clean_text(row["ord_st"]).upper()

    # 정상 상태 목록에 없는 값이면
    # 알 수 없는 주문상태로 판단한다.
    if order_status not in KNOWN_STATUS_VALUES:
        unknown_order_status += 1


    # -----------------------------
    # 주문수량 검사
    # -----------------------------

    try:
        # CSV에서 읽은 값은 문자열이므로 정수로 변환한다.
        quantity = int(clean_text(row["qty"]))

        # 수량은 1 이상이어야 한다는 업무 규칙을 적용한다.
        if quantity <= 0:
            non_positive_quantity += 1

    except ValueError:
        # 예:
        # qty = "abc"
        # qty = ""
        #
        # 정수로 변환할 수 없는 경우도 잘못된 수량으로 본다.
        non_positive_quantity += 1


    # -----------------------------
    # 단가 검사
    # -----------------------------

    try:
        # 금액은 float 대신 Decimal을 사용한다.
        #
        # 금액 데이터는 부동소수점 오차를 피하는 것이 좋기 때문이다.
        unit_price = Decimal(clean_text(row["amt"]))

        # 단가가 음수이면 잘못된 값으로 판단한다.
        if unit_price < 0:
            negative_unit_price += 1

    except InvalidOperation:
        # 예:
        # amt = "만원"
        # amt = ""
        #
        # Decimal로 변환하지 못하는 값도 잘못된 단가로 판단한다.
        negative_unit_price += 1


# ---------------------------------------------------------
# 8. 카테고리 코드 ↔ 카테고리 이름의 일관성 검사
# ---------------------------------------------------------

# 하나의 category_code에 어떤 category_name들이 연결되어 있는지
# 집합(set)으로 저장한다.
category_names_by_code = defaultdict(set)


for row in rows:

    category_code = clean_text(row["ctg_cd"]).upper()
    category_name = clean_text(row["ctg_nm"])

    # 코드와 이름이 모두 있는 데이터만 검사한다.
    if category_code and category_name:
        category_names_by_code[category_code].add(category_name)


# 하나의 카테고리 코드에 서로 다른 이름이 연결된 경우를 찾는다.
inconsistent_categories = [
    {
        "category_code": category_code,
        "category_names": sorted(category_names),
    }

    for category_code, category_names
    in sorted(category_names_by_code.items())

    # 이름이 2개 이상이면 기준정보가 일관되지 않은 것이다.
    if len(category_names) > 1
]

# 예:
#
# C03 → AI
# C03 → 인공지능
#
# 하나의 코드 C03이 서로 다른 의미/표현을 가지고 있으므로
# 기준정보(reference/master data) 정비가 필요하다.


# ---------------------------------------------------------
# 9. 실제 주문상태 표현값 확인
# ---------------------------------------------------------

status_variants = list(
    dict.fromkeys(
        clean_text(row["ord_st"])
        for row in rows
        if clean_text(row["ord_st"])
    )
)

# dict.fromkeys()를 사용하면
# 입력 순서를 유지하면서 중복을 제거할 수 있다.
#
# 예:
#
# PAID
# 결제완료
# PAID
# 배송중
#
# ↓
#
# ["PAID", "결제완료", "배송중"]
#
# 주문상태 값이 어떤 표현으로 섞여 있는지
# 실제 데이터를 확인하기 위한 프로파일링 정보다.


# ---------------------------------------------------------
# 10. 최종 데이터 프로파일링 보고서 생성
# ---------------------------------------------------------

report = {

    # 데이터 품질 문제가 발견되었으므로
    # 추가 검토가 필요하다는 상태를 지정한다.
    "status": "review-required",

    # 데이터의 Grain(한 행이 의미하는 업무 단위)을 정의한다.
    "grain": {

        # 현재 한 행은
        # "한 주문에서 주문한 하나의 도서 종류"를 의미한다고 판단한다.
        "row_meaning": "한 주문에 포함된 도서 한 종류",

        # 후보 업무 식별자
        "candidate_business_key": [
            "ord_no",
            "bk_cd",
        ],

        # 후보키를 결정할 때 사용한 업무 가정
        "business_assumption":
            "같은 주문에서 같은 도서는 한 번만 나타난다",
    },


    # 전체 행 개수
    "row_count": len(rows),

    # 전체 컬럼 개수
    "column_count": len(columns),


    # 컬럼별 결측값 개수
    "missing_counts": missing_counts,


    # 컬럼별 고유값 개수
    "distinct_counts": distinct_counts,


    # 모든 컬럼의 값이 완전히 동일한 중복 행 개수
    "duplicate_exact_rows": duplicate_exact_rows,


    # 후보 업무 식별자가 중복된 데이터
    "duplicate_business_keys": duplicate_business_keys,


    # 주요 데이터 품질 오류 개수
    "invalid_value_counts": {

        # 회원번호는 필수라고 가정한다.
        "missing_required_member_id":
            missing_counts["mbr_no"],

        # 잘못된 주문일시
        "invalid_order_datetime":
            invalid_order_datetime,

        # 정의되지 않은 주문상태
        "unknown_order_status":
            unknown_order_status,

        # 0 또는 음수이거나 숫자가 아닌 주문수량
        "non_positive_quantity":
            non_positive_quantity,

        # 음수이거나 숫자가 아닌 단가
        "negative_unit_price":
            negative_unit_price,
    },


    # 실제 데이터에서 발견된 주문상태 표현
    "status_variants": status_variants,


    # 기준정보의 불일치 내용
    "inconsistent_reference_values": {

        # 같은 카테고리 코드에
        # 서로 다른 카테고리 이름이 연결된 경우
        "category_code_to_name":
            inconsistent_categories,
    },


    # 프로파일링 결과를 사람이 쉽게 이해할 수 있도록
    # 주요 문제를 문장으로 정리한다.
    "observations": [
        "공백과 영문 대소문자가 섞여 있다",
        "주문일시 형식이 세 가지이며 잘못된 날짜가 한 건 있다",
        "주문상태가 한글과 영문으로 섞여 있고 미등록 값이 한 건 있다",
        "후보 업무 식별자 ord_no + bk_cd가 한 건 중복된다",
        "카테고리 C03의 이름이 AI와 인공지능으로 불일치한다",
    ],
}


# ---------------------------------------------------------
# 11. 프로파일링 결과를 JSON 파일로 저장
# ---------------------------------------------------------

with OUTPUT_FILE.open("w", encoding="utf-8") as file:

    json.dump(
        report,
        file,

        # 한글을 \uXXXX 형태로 변환하지 않고 그대로 저장한다.
        ensure_ascii=False,

        # JSON을 사람이 읽기 좋게 들여쓰기한다.
        indent=2,
    )

    # 파일 마지막에 개행 문자를 추가한다.
    file.write("\n")


# ---------------------------------------------------------
# 12. 동일한 결과를 터미널에도 출력
# ---------------------------------------------------------

print(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
)