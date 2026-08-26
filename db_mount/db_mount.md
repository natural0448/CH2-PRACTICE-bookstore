connection.cursor()
→ cursor.execute("SELECT ...")
→ cursor.fetchall()
→ [(1, "Raw item 1"), (2, "Raw item 2")]
→ RawItemDTO 두 개
→ service의 asdict()
→ JsonResponse


#### Raw 주소에서 `no such table: raw_item`이 나올 때

1. **증상 확인:** `/db-mount/raw/` 응답에 `no such table: raw_item`이 있는지 확인합니다.
2. **기대값과 실제값 비교:** 기대값은 Raw 데이터 두 건이며, 실제값은 테이블 없음 오류입니다.
3. **가장 작은 진단:** `python manage.py showmigrations db_mount`를 실행합니다.
4. **원인 확정:** `0002_seed_data` 앞이 `[ ]`이면 자동 생성 migration을 아직 실행하지 않은 것입니다.
5. **최소 수정:** 코드는 바꾸지 말고 `python manage.py migrate`를 실행합니다.
6. **재실행 증거:** Raw 주소를 다시 호출해 `Raw item 1`, `Raw item 2`를 확인합니다.

<!-- lesson:block {"id":"encore.db-mount-layer-practice.layers.practice","type":"practice","role":"learning","conceptId":"encore.db-mount-layer-practice.layers","version":"v1"} -->
## 확인 문제

코드를 바꾸지 말고 다음 표의 빈칸을 채우세요.

| 질문 | 답 |
| --- | --- |
| ORM 조회를 시작하는 코드 | `OrmItem.objects.using("sqlite3")` |
| Raw SQL 커서를 여는 코드 | `connections["sqlite3"].cursor()` |
| SQL 결과 전체를 받는 코드 | `cursor.fetchall()` |
| 튜플 한 행을 받는 DTO 이름 | `RawItemDTO` |
| DTO를 dict로 바꾸는 계층 | `service 계층의 get_raw_items()` |

<!-- lesson:block {"id":"encore.db-mount-layer-practice.artifact","type":"artifact","role":"artifact","version":"v1"} -->
## 최종 파일 구조와 완료 기준

```text
db_mount/
├── __init__.py
├── apps.py
├── models.py                  # Django 모델 탐색용 한 줄 연결
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
│   └── 0002_seed_data.py
├── presentation/
│   ├── __init__.py
│   ├── views.py
│   └── urls.py
├── service/
│   ├── __init__.py
│   └── services.py
└── repository/
    ├── __init__.py
    ├── models.py
    └── sqlite_repository.py