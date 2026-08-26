# Feature projection 파티션 계획

## 대상

member_book_preference_features

## 파티션 키

as_of_date

## 선택 이유

추천 학습 데이터는 특정 기준일의 전체 회원 feature를 읽는다.
기준일 조건으로 필요한 파일만 선택할 수 있다.

## 예상 경로

member_book_preference_features/as_of_date=YYYY-MM-DD/part-000.csv

## 쓰기 방식

- 하루 한 파티션을 새로 생성한다.
- 같은 날짜를 재실행할 때는 새 결과를 임시 위치에 완성한 후 교체한다.
- 성공 여부가 확인되지 않은 반쪽 파일을 공개하지 않는다.

## 작은 파일 대응

- 학습 fixture에서는 날짜마다 CSV 한 개를 사용한다.
- 운영에서는 날짜별 전체 크기와 파일 수를 측정한다.
- 파일이 지나치게 작으면 주 단위 분할 또는 파일 합치기를 검토한다.

## 제외 범위

- 실제 Spark 작업 작성
- 실제 S3 업로드
- 운영 DB 파티션 변경

## 검증

- 경로의 as_of_date와 파일 안 as_of_date가 같다.
- 미래 주문을 feature에 포함하지 않는다.
- 같은 기준일 재실행 결과가 같다.