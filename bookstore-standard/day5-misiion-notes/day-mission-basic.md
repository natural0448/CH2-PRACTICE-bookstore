# Day 5 초급 미션 — 열한 컬럼의 정규화 이동표

## 1. 미션 목적

온라인 서점의 표준 주문 데이터 11개 컬럼을 1NF, 2NF, 3NF 순서로 정규화하여
`Member`, `Category`, `Book`, `Order`, `OrderItem` 엔터티로 분리한다.

1NF에서는 모든 값을 원자값으로 관리하고,
2NF에서는 복합키의 일부에만 종속된 속성을 분리하며,
3NF에서는 회원명과 카테고리명처럼 다른 일반 속성을 거쳐 결정되는 이행적 종속을 제거한다.

## 2. 열한 컬럼의 정규화 이동표

| 표준 컬럼 | 1NF 위치 | 2NF 이동 위치 | 3NF 최종 위치 및 건수 | 최종 키 역할 |
|---|---|---|---|---|
| `member_id` | 통합 주문행 | `Order` | `Member` 4건 / `Order` 5건 | `Member.PK`, `Order.FK` |
| `member_name` | 통합 주문행 | `Order` | `Member` 4건 | 일반 속성 |
| `book_id` | 통합 주문행 | `Book`, `OrderItem` | `Book` 5건 / `OrderItem` 6건 | `Book.PK`, `OrderItem.PK·FK` |
| `book_name` | 통합 주문행 | `Book` | `Book` 5건 | 일반 속성 |
| `category_code` | 통합 주문행 | `Book` | `Category` 3건 / `Book` 5건 | `Category.PK`, `Book.FK` |
| `category_name` | 통합 주문행 | `Book` | `Category` 3건 | 일반 속성 |
| `order_id` | 통합 주문행 | `Order`, `OrderItem` | `Order` 5건 / `OrderItem` 6건 | `Order.PK`, `OrderItem.PK·FK` |
| `order_datetime` | 통합 주문행 | `Order` | `Order` 5건 | 일반 속성 |
| `order_status_code` | 통합 주문행 | `Order` | `Order` 5건 | 일반 속성 |
| `quantity` | 통합 주문행 | `OrderItem` | `OrderItem` 6건 | 일반 속성 |
| `unit_price` | 통합 주문행 | `OrderItem` | `OrderItem` 6건 | 일반 속성 |

`OrderItem`의 기본키는 `(order_id, book_id)` 복합키이며,
두 컬럼은 각각 `Order`와 `Book`을 참조하는 외래키이기도 하다.

## 3. 최종 엔터티 구조

| 엔터티 | 고정 fixture 건수 | 기본키(PK) | 외래키(FK) |
|---|---:|---|---|
| `Member` | 4 | `member_id` | 없음 |
| `Category` | 3 | `category_code` | 없음 |
| `Book` | 5 | `book_id` | `category_code → Category.category_code` |
| `Order` | 5 | `order_id` | `member_id → Member.member_id` |
| `OrderItem` | 6 | `(order_id, book_id)` | `order_id → Order.order_id`, `book_id → Book.book_id` |

최종 고정 fixture에서 회원 4건, 카테고리 3건, 도서 5건,
주문 5건, 주문항목 6건으로 분리되며, 이를 `4·3·5·5·6`으로 확인하였다.

## 4. 컬럼 배치 결정 이유

`quantity`와 `unit_price`는 주문 전체나 도서 자체가 아니라 특정 주문에서 선택된 특정 도서의 수량과 주문 당시 단가를 나타내므로 `(order_id, book_id)`로 식별되는 `OrderItem`에 남긴다.

`member_name`은 주문마다 반복해서 저장할 값이 아니라 `member_id`에 의해 결정되는 회원의 기준 정보이므로 `Member` 엔터티로 이동한다.

`category_name`은 도서마다 반복해서 저장할 값이 아니라 `category_code`에 의해 결정되는 카테고리의 기준 정보이므로 `Category` 엔터티로 이동한다.

## 5. 정규화 결과

- 1NF: 11개 컬럼의 값을 하나의 통합 주문행에서 원자값으로 관리하였다.
- 2NF: `order_id`에만 종속되는 주문 속성과 `book_id`에만 종속되는 도서 속성을 분리하였다.
- 3NF: `member_id → member_name`, `category_code → category_name`의 이행적 종속을 제거하였다.
- 주문항목의 업무 단위는 “주문 한 건에 포함된 도서 한 종”이다.
- 최종 엔터티 건수는 `Member 4`, `Category 3`, `Book 5`, `Order 5`, `OrderItem 6`이다.

## 6. 완료 확인

- [x] 표준 컬럼 11개를 모두 기록했다.
- [x] 1NF, 2NF, 3NF 단계별 이동 위치를 기록했다.
- [x] 다섯 엔터티의 PK와 FK를 기록했다.
- [x] 고정 fixture 건수 `4·3·5·5·6`을 기록했다.
- [x] `quantity`와 `unit_price`가 `OrderItem`에 남는 이유를 작성했다.
- [x] `member_name`이 `Member`로 이동하는 이유를 작성했다.
- [x] `category_name`이 `Category`로 이동하는 이유를 작성했다.