# 온라인 서점 관계 규칙

## 안정 엔터티 ID

- `member`
- `category`
- `book`
- `order`
- `order-item`

## 관계 규칙

### R-01 회원과 주문

- 부모: `member`
- 자식: `order`
- 관계: 1:N
- 회원 기준: 주문 0건 이상, 선택 관계
- 주문 기준: 회원 정확히 1명, 필수 관계
- FK 후보: `book_order.member_id` → `member.member_id`
- 근거: BR-05, BR-06

### R-02 카테고리와 도서

- 부모: `category`
- 자식: `book`
- 관계: 1:N
- 카테고리 기준: 도서 0종 이상, 선택 관계
- 도서 기준: 카테고리 정확히 1건, 필수 관계
- FK 후보: `book.category_code` → `category.category_code`
- 근거: BR-07, BR-08

### R-03 주문과 주문항목

- 부모: `order`
- 자식: `order-item`
- 관계: 1:N
- 주문 기준: 주문항목 1건 이상, 업무상 필수 관계
- 주문항목 기준: 주문 정확히 1건, 필수 관계
- FK 후보: `order_item.order_id` → `book_order.order_id`
- 근거: BR-09, BR-10

### R-04 도서와 주문항목

- 부모: `book`
- 자식: `order-item`
- 관계: 1:N
- 도서 기준: 주문항목 0건 이상, 선택 관계
- 주문항목 기준: 도서 정확히 1종, 필수 관계
- FK 후보: `order_item.book_id` → `book.book_id`
- 근거: BR-10

## N:M 해소

주문과 도서는 업무적으로 N:M이다. `order-item`을 연결 엔터티로 두어 두 개의 1:N 관계로 바꾼다. `quantity`와 `unit_price`는 연결에서 발생한 값이므로 `order-item`에 둔다.

## 1:1 범위 판단

회원과 회원상세는 1:1 예제가 될 수 있지만 현재 원천 컬럼과 추천 목적에 근거가 없다. 따라서 `member-profile` 엔터티를 추가하지 않는다.

## 삭제 규칙

학습 단계에서는 부모 행을 실수로 삭제하여 주문 사실이 사라지지 않도록 모든 FK에 `ON DELETE RESTRICT`를 사용한다.

## 미확정 경계

정규화된 쓰기 구조의 조회 성능, 인덱스, 파티션, 반정규화는 Day 6에서 결정한다.