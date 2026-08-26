# Day 8 Django 미션 — Release 근거 추적

## 확인 결과

Day 8 화면의 `dataset version`, `2·2·0`, `release 상태`, `checksum`은 모두 `release` 폴더의 정본 산출물까지 추적된다. 화면은 manifest를 주 표시 원천으로 사용하고, quality report와 validation으로 집계·상태를 교차검증하며, training CSV 원본 바이트로 실제 checksum을 다시 계산한다.

## 화면 값과 원천 산출물 추적표

| 화면 항목 | 화면 값 | 화면의 1차 출처 | 정확한 필드·계산 | 교차검증 근거 | Django context |
| --- | ---: | --- | --- | --- | --- |
| Dataset version | `2026-08-14-v1` | `release/dataset-manifest.json` | `dataset_version` | manifest가 배포 데이터셋의 이름·버전·생성 시각을 함께 고정한다. | `manifest.dataset_version` |
| 학습 행 | `2` | `release/dataset-manifest.json` | `counts.ai_ready_row_count` | `quality-report.json`의 `ai_ready_row_count=2`, `day8-validation.json`의 `ai_ready_row_count` 검사 `evidence=2`, `ai-ready-dataset.csv`의 헤더 제외 실제 행 수 `2`가 일치한다. | `counts.ai_ready_row_count` |
| 적격성 제외 행 | `2` | `release/dataset-manifest.json` | `counts.eligibility_exclusion_count` | `quality-report.json`의 같은 집계와 `NEXT_7D_LABEL_ELIGIBILITY.excluded_count=2`, `day8-validation.json`의 같은 검사 `evidence=2`가 일치한다. | `counts.eligibility_exclusion_count` |
| 원천 품질 실패 행 | `0` | `release/dataset-manifest.json` | `counts.source_quality_failure_count` | `quality-report.json`의 같은 집계와 `day8-validation.json`의 같은 검사 `evidence=0`이 일치한다. | `counts.source_quality_failure_count` |
| Release 상태 | `PASS_WITH_QUARANTINE` | `release/dataset-manifest.json` | `release_status` | `quality-report.json`의 `overall_status`와 `day8-validation.json`의 `release_status`도 `PASS_WITH_QUARANTINE`이다. 2건은 원천 품질 실패가 아니라 적격성 조건에 따라 격리된 것이므로 이 상태가 정상 결과다. | `manifest.release_status` |
| Validation 상태 | `READY_FOR_DJANGO` | `release/day8-validation.json` | `status` | validation의 개별 `checks`가 모두 `PASS`이며 release 상태도 일치한다. | `validation.status` |
| Manifest checksum | `9098fe74965a673ef912b4866416707b3d00b45956264c9c67c203a23bbd7b89` | `release/dataset-manifest.json` | `files.training.sha256` | `day8-validation.json`의 `dataset_checksum_recorded.evidence`와 같다. | `expected_checksum` |
| 실제 checksum | `9098fe74965a673ef912b4866416707b3d00b45956264c9c67c203a23bbd7b89` | `release/ai-ready-dataset.csv` | CSV 파일 바이트에 `SHA-256` 적용 | manifest checksum과 같으므로 `checksum_match=True`이다. | `actual_checksum`, `checksum_match` |

> `2·2·0`은 순서대로 학습 가능 행 2건, 적격성 제외 행 2건, 원천 품질 실패 행 0건을 뜻한다.

## 네 산출물의 역할

| 산출물 | 역할 |
| --- | --- |
| `dataset-manifest.json` | 화면에 표시할 데이터셋 버전, `2·2·0`, release 상태, 기대 checksum을 제공하는 배포 계약이다. |
| `quality-report.json` | `2·2·0` 집계와 `PASS_WITH_QUARANTINE` 판단의 품질 규칙 근거를 제공한다. |
| `day8-validation.json` | 집계와 기록 checksum을 다시 검사하고 Django 인계 준비 상태 `READY_FOR_DJANGO`를 제공한다. |
| `ai-ready-dataset.csv` | 실제 학습 행 2건을 담으며, 파일 자체가 실제 checksum 계산 대상이다. |

## Django 전달 흐름

```text
GET /bookstore/day8/
  → bookstore/presentation/urls.py
  → day8_dashboard(request)
  → get_day8_release_dashboard_context()
  → manifest · quality report · validation 로드
  → training CSV 행 수 확인 및 SHA-256 계산
  → context 생성
  → day8_dashboard.html 출력
```

서비스는 `dataset-manifest.json`의 `files.training.path`로 학습 CSV를 찾은 다음, CSV 바이트의 SHA-256을 계산하여 `files.training.sha256`과 비교한다. 따라서 checksum은 JSON에 적힌 문자열만 출력하는 값이 아니라 실제 파일 무결성을 재검증한 결과다.

## 순차 적용 및 확인 방법

1. `day8-lab/release/dataset-manifest.json`에서 `dataset_version`, `counts`, `release_status`, `files.training.sha256`을 확인한다.
2. `quality-report.json`에서 `ai_ready_row_count=2`, `eligibility_exclusion_count=2`, `source_quality_failure_count=0`, `overall_status=PASS_WITH_QUARANTINE`을 확인한다.
3. `day8-validation.json`에서 대응 검사들의 `evidence`와 `status`, 최상위 `status=READY_FOR_DJANGO`를 확인한다.
4. PowerShell에서 `(Import-Csv .\release\ai-ready-dataset.csv).Count`를 실행해 학습 행이 `2`인지 확인한다.
5. `(Get-FileHash .\release\ai-ready-dataset.csv -Algorithm SHA256).Hash.ToLower()`를 실행해 실제 checksum을 계산한다.
6. 계산 결과가 manifest의 `files.training.sha256`과 같은지 확인한다.
7. `/bookstore/day8/` 화면에서 version, `2·2·0`, release·validation 상태, checksum 일치 여부를 확인하고 화면을 캡처한다.

## 현재 구현에서 주의할 점

정본 validation 상태는 `PASS`가 아니라 `READY_FOR_DJANGO`이다. 서비스의 최종 판정 조건이 `validation.get("status") == "PASS"`로 되어 있으면 다른 근거가 모두 정상이어도 화면의 최종 상태는 `FAIL`이 된다. 정본 계약에 맞는 조건은 다음과 같다.

```python
validation.get("status") == "READY_FOR_DJANGO"
```

여러 상태를 허용해야 하는 설계라면 다음처럼 명시할 수 있다.

```python
validation.get("status") in {"PASS", "READY_FOR_DJANGO"}
```

## 완료 기준

- dataset version의 manifest 필드가 기록되어 있다.
- `2·2·0`의 의미와 manifest·quality report·validation·training CSV 사이의 교차 근거가 기록되어 있다.
- release 상태가 `PASS_WITH_QUARANTINE`인 이유가 기록되어 있다.
- manifest checksum과 training CSV에서 계산한 실제 checksum이 일치함을 기록했다.
- 화면까지의 `urls.py → views.py → services.py → template` 흐름을 기록했다.
