
''''''
    초급 — 다섯 엔터티 카드 만들기
    온라인 서점의 member, category, book, order, order-item을 한 표로 정리하여 각 안정 ID, 선택 식별자, 한글 이름, grain을 기록하고, 고정 fixture의 서로 다른 건수가 각각 4·3·5·5·6임을 entity-candidates.csv와 identifier-decisions.csv에서 확인해 근거 열에 적는다.

    완료 기준은 order-item의 grain을 “주문 한 건의 도서 한 종”이라고 쓰고 다섯 엔터티 모두에 근거 파일을 연결하는 것이다.
'''''' 

# Day 4 초급 미션: 다섯 엔터티 카드

| 안정 ID | 선택 식별자 | 한글 이름 | grain | 서로 다른 건수 | 근거 |
|---|---|---|---|---:|---|
| member | member_id | 회원 | 회원 한 명 | 4 | entity-candidates.csv의 member 행, identifier-decisions.csv의 member-pk |
| category | category_code | 카테고리 | 카테고리 한 건 | 3 | entity-candidates.csv의 category 행, identifier-decisions.csv의 category-pk |
| book | book_id | 도서 | 도서 한 종 | 5 | entity-candidates.csv의 book 행, identifier-decisions.csv의 book-pk |
| order | order_id | 주문 | 주문 한 건 | 5 | entity-candidates.csv의 order 행, identifier-decisions.csv의 order-pk |
| order-item | (order_id, book_id) | 주문항목 | 주문 한 건의 도서 한 종 | 6 | entity-candidates.csv의 order-item 행, identifier-decisions.csv의 order-item-pk |