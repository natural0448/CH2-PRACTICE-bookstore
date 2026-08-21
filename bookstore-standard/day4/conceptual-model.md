# 온라인 서점 모델

## 모델 목적

정제된 주문항목 데이터에서 회원별 도서·카테고리 선호를 준비할 핵심 업무 대상을 정의한다.

## 개념 모델

```mermaid
flowchart LR
    member["회원\nmember"] -->|주문한다| order["주문\norder"]
    order -->|포함한다| orderItem["주문항목\norder-item"]
    orderItem -->|도서를 가리킨다| book["도서\nbook"]
    book -->|분류된다| category["카테고리\ncategory"]
```

## 관계를 문장으로 읽기

- 회원은 주문한다.
- 주문은 주문항목을 포함한다.
- 주문항목은 도서를 가리킨다.
- 도서는 카테고리에 속한다.

## 범위 밖

- 배송지, 결제, 재고, 출판사 엔터티는 현재 입력 컬럼과 추천 목적에 필요한 근거가 없어 추가하지 않는다.
- 필요성이 생기면 요구사항과 원천 컬럼을 먼저 확보한 뒤 모델 범위를 변경한다.

## 논리 모델 후보

| 안정 ID | 논리명 | 식별자 | 속성 후보 | 근거 |
| --- | --- | --- | --- | --- |
| `member` | 회원 | `member_id` | `member_name` | 주문 회원을 반복 참조한다. |
| `category` | 카테고리 | `category_code` | `category_name` | 여러 도서가 같은 분류를 공유한다. |
| `book` | 도서 | `book_id` | `book_name`, `category_code` | 주문항목이 도서를 참조한다. |
| `order` | 주문 | `order_id` | `member_id`, `order_datetime`, `order_status_code` | 회원에게 발생한 주문 사건이다. |
| `order-item` | 주문항목 | `order_id` + `book_id` | `quantity`, `unit_price` | 주문 당시 수량과 가격 사실이다. |

`category_code`, `member_id`, `order_id`, `book_id`가 실제 FK가 되는지는 5일차에 관계의 방향과 필수 여부를 검증하며 확정한다.

## 물리 이름 후보

| 안정 ID | 물리 테이블 이름 후보 | 주 식별 컬럼 후보 |
| --- | --- | --- |
| `member` | `member` | `member_id` |
| `category` | `category` | `category_code` |
| `book` | `book` | `book_id` |
| `order` | `book_order` | `order_id` |
| `order-item` | `order_item` | `order_id`, `book_id` |

`order`는 SQL 예약어와 충돌할 수 있으므로 물리 이름 후보를 `book_order`로 정했다. 실제 SQL 타입·제약조건·FK는 5일차에 작성한다.

## 단계별 추적표

| 업무 문장 | 개념 요소 | 논리 요소 | 물리 후보 |
| --- | --- | --- | --- |
| 회원은 주문한다. | `member` → `order` | `order.member_id` 후보 | `book_order.member_id` 후보 |
| 도서는 카테고리에 속한다. | `book` → `category` | `book.category_code` 후보 | `book.category_code` 후보 |
| 주문은 도서를 포함한다. | `order` → `order-item` → `book` | 복합 식별자 후보 | `order_item(order_id, book_id)` 후보 |