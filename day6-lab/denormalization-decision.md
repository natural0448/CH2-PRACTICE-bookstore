# 반정규화 결정서

## 목적

회원별 도서 선호 및 추천용 학습 데이터 준비 시간을 줄인다.

## 정본

- Member
- Book
- Category
- Order
- OrderItem
- Day 5 normalized-schema.sql

## 생성할 projection

이름: member_book_preference_features

한 행의 의미:
한 회원이 as_of_date 직전 30일 동안 보인 구매 행동의 요약

포함 항목:
- member_id
- as_of_date
- order_count_30d
- quantity_sum_30d
- spend_sum_30d
- preferred_category_code_30d
- last_order_days_ago

## 갱신 방법

- 매일 오전 1시에 새로운 as_of_date 파티션 생성
- 기존 정규화 테이블에서 전체 재계산 가능
- 계산 코드 버전을 dataset manifest에 기록

## 허용하는 중복

member_id와 집계값을 as_of_date별로 반복 저장한다.
Member의 member_name은 추천 학습에 필요하지 않으므로 feature projection에 복사하지 않는다.

## 위험과 대응

- 원본과 값이 어긋날 수 있음: 생성 시각과 원본 버전을 기록한다.
- 미래 주문이 포함될 수 있음: order_datetime이 as_of_date보다 작은 주문만 사용한다.
- 파일이 너무 많아질 수 있음: 일 단위 파티션을 사용하고 파일 크기를 관찰한다.

## 승인 조건

- 정규화 쓰기 모델을 정본으로 유지한다.
- projection을 사람이 직접 수정하지 않는다.
- 같은 입력과 같은 as_of_date로 다시 실행하면 같은 결과가 나온다.
- 표준 사전에 없는 컬럼을 추가하지 않는다.