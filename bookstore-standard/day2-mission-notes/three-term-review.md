| 원본 컬럼 | 논리 용어 | 표준 단어 조합 | 물리명 | 도메인 | 명명 규칙 통과 근거 |
|---|---|---|---|---|---|
| `mbr_no` | 회원ID | `MEMBER\|ID` | `member_id` | `ID_20` | 영문 소문자와 밑줄로 구성된 `lower_snake_case`이며, 식별자 접미사 `_id`를 사용하고 승인 약어 `id`를 적용했다. |
| `ord_st` | 주문상태코드 | `ORDER\|STATUS\|CODE` | `order_status_code` | `ORDER_STATUS_CODE` | 영문 소문자와 밑줄로 구성된 `lower_snake_case`이며, 코드 접미사 `_code`를 사용하고 레거시 약어 `ord`, `st`를 표준 단어로 확장했다. |
| `amt` | 단가 | `UNIT\|PRICE` | `unit_price` | `MONEY_12_2` | 영문 소문자와 밑줄로 구성된 `lower_snake_case`이며, 금지된 레거시 약어 `amt`를 표준 단어 `unit`, `price`로 전환했다. |

세 용어는 새로운 단어나 도메인을 추가하지 않고 기존 12개 표준 단어 중 `MEMBER`, `ID`, `ORDER`, `STATUS`, `CODE`, `UNIT`, `PRICE` 7개를 조합하여 재사용하며, 기존 8개 데이터 도메인 중 `ID_20`, `ORDER_STATUS_CODE`, `MONEY_12_2` 3개를 각 용어의 값 형식과 업무 의미에 맞게 재사용한다.