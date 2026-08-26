# Dataset Card

## 이름

회원별 도서 선호 추천 학습 데이터

## 버전

2026-08-14-v1

## 생성 시각

2026-08-14T18:00:00+09:00

## 목적

회원의 과거 30일 구매 특징으로 다음 7일 구매 카테고리를 예측한다.

## 한 행의 의미

한 회원과 한 as_of_date의 feature 및 label이다.

## 시점

- feature: as_of_date 직전 30일
- label: as_of_date 이상 7일 미만
- as_of_date: 2026-08-12

## 포함 기준

다음 7일 안에 PAID, SHIPPING, DONE 상태 주문이 있어 label을 만들 수 있는 회원

## 제외 기준

다음 7일 구매가 없는 회원은 ELIGIBILITY_EXCLUSION으로 failed-rows.csv에 기록한다. 이는 원천 품질 실패가 아니다.

## 행 수

- AI 학습 입력: 2
- 학습 대상 제외: 2
- 원천 품질 실패: 0

## 품질 상태

PASS_WITH_QUARANTINE

## SHA-256

9098fe74965a673ef912b4866416707b3d00b45956264c9c67c203a23bbd7b89

## 주의사항

- member_name과 book_name은 학습 입력에 포함하지 않았다.
- 4명의 작은 교육용 fixture이므로 실제 모델 성능을 대표하지 않는다.
- 다음 7일 구매가 없는 회원을 제외했으므로 이 release만으로 구매 여부 자체를 학습할 수 없다.
- failed-rows.csv는 학습 입력이 아니라 감사와 재검토 입력이다.
