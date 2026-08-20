# Day 3 중급 미션: 주문 상태 코드별 강조 표시

## 1. 미션 목표

Day 3 대시보드의 정상 데이터 표에서 주문 상태 코드인 `PAID`, `SHIPPING`, `DONE`을 서로 다른 색상으로 표시한다.

다음 세 값이 화면에서 시각적으로 구분되면 완료이다.

- `PAID`: 파란색
- `SHIPPING`: 주황색
- `DONE`: 초록색

## 2. 상태별 CSS 추가

`day3_dashboard.html`의 `<style>` 영역에서 다음 선택자를 찾는다.

```css
.state-chip {
```

기존 공통 스타일은 모든 주문 상태 배지의 크기와 기본 모양을 담당한다.

```css
.state-chip {
  display: inline-flex;
  padding: 4px 9px;
  color: var(--purple);
  background: var(--purple-soft);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}
```

이 블록 바로 아래에 다음 상태별 스타일을 추가한다.

```css
.state-paid {
  color: #1d4ed8;
  background: #dbeafe;
  border: 1px solid #93c5fd;
}

.state-shipping {
  color: #c2410c;
  background: #ffedd5;
  border: 1px solid #fdba74;
}

.state-done {
  color: #047857;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
}
```

## 3. 템플릿 클래스 변경

같은 파일의 정상 데이터 표에서 다음 코드를 찾는다.

```django
<td><span class="state-chip">{{ row.order_status_code }}</span></td>
```

다음과 같이 변경한다.

```django
<td>
  <span class="state-chip state-{{ row.order_status_code|lower }}">
    {{ row.order_status_code }}
  </span>
</td>
```

`lower`는 Django 템플릿 필터이다. 상태 코드를 소문자로 바꿔 CSS 클래스 이름에 연결한다.

| 원본 상태 코드 | `lower` 적용 결과 | 최종 CSS 클래스 |
|---|---|---|
| `PAID` | `paid` | `state-paid` |
| `SHIPPING` | `shipping` | `state-shipping` |
| `DONE` | `done` | `state-done` |

예를 들어 `PAID` 행은 브라우저에서 다음과 같이 렌더링된다.

```html
<span class="state-chip state-paid">PAID</span>
```

`state-chip`은 공통 모양을 적용하고 `state-paid`는 PAID 전용 색상을 추가한다.


## 4. 완료 확인

정상 데이터 표에서 다음 상태가 서로 다른 색상으로 표시되는지 확인한다.

| 상태 코드 | 기대 표시 |
|---|---|
| `PAID` | 파란색 배지 |
| `SHIPPING` | 주황색 배지 |
| `DONE` | 초록색 배지 |

세 상태 코드가 각각 다른 색상으로 구분되면 중급 미션 완료이다.