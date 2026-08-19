# 출판사명 표준화 변경 요청서

## 변경 요청

| 상태 | 원본 컬럼 | 제안 단어 | 논리 용어 | 표준 단어 조합 | 제안 물리명 | 재사용 도메인 |
|---|---|---|---|---|---|---|
| `PROPOSED` | `pub_nm` | `PUBLISHER` | 출판사명 | `PUBLISHER\|NAME` | `publisher_name` | `NAME_100` |

## 제안 사유

레거시 컬럼 `pub_nm`은 `pub`과 `nm` 약어를 사용하여 의미가 명확하지 않으므로, 출판사를 의미하는 신규 표준 단어 `PUBLISHER`와 기존 표준 단어 `NAME`을 조합한 `publisher_name`으로 표준화할 것을 제안한다. `publisher_name`은 영문 소문자와 밑줄로 구성된 `lower_snake_case` 명명 규칙을 충족한다.

## 도메인 재사용

출판사명은 이름 유형의 문자열이므로 기존 데이터 도메인 `NAME_100`을 재사용한다. 따라서 신규 데이터 도메인은 추가하지 않는다.

## 영향 분석

현재 상태는 승인 전인 `PROPOSED`이므로 정본 `standard-words.csv`, `standard-terms.csv`, `data-domains.yaml`은 수정하지 않는다. 요청이 승인되면 표준 단어는 `PUBLISHER`가 추가되어 12개에서 13개로 증가하고, 표준 용어는 `출판사명`과 물리명 `publisher_name`이 추가되어 11개에서 12개로 증가한다. 데이터 도메인은 기존 `NAME_100`을 재사용하므로 8개로 유지된다.