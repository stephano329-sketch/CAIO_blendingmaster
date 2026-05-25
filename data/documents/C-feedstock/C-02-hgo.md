---
section_id: C-02
title: HGO (Heavy Gas Oil) 반제품 특성
doc_type: feedstock
lang: ko
source: 합성 (공개 정유공정 자료 + physical_model.py 정합)
version: 1.0
---

# C-02. HGO (Heavy Gas Oil) — 중질 가스 오일

## 정의와 위치

HGO(Heavy Gas Oil, 중질 가스 오일)는 LGO보다 **무거운 분획**으로, 비점 320~400°C 구간에서 생성된다. 디젤 보조 반제품으로 사용되거나, Hydrocracker 원료로도 활용된다.

## 생산 경로

### 1. CDU 직접 유래 HGO
- 비점 350~400°C 컷
- 황 함량 매우 높음 (5,000~15,000ppm)
- HDS 1~2단 강력 처리 필요

### 2. HCC 유래 HGO
- Hydrocracker 부산물
- 수소화로 인해 품질이 CDU 직접보다 우수
- 디젤 블렌딩에 더 선호됨

### 3. VGO Hydrotreater 유래
- 일부 정유사에서 운영하는 별도 라인

## 주요 성상 범위 (HDS 처리 후)

| 항목 | 일반 범위 | 평균 |
| --- | --- | --- |
| 비점 (T50) | 340~370°C | 355°C |
| 밀도 (15°C) | 845~865 kg/m³ | 855 kg/m³ |
| 황분 | 5~10 ppm | 8 ppm |
| 세탄 지수 | 45~52 | 48 |
| **CFPP** | **+8 ~ +20°C** | **+14°C** |
| n-파라핀 C10~C15 | 4~8 wt% | 6 wt% |
| n-파라핀 C16~C20 | 10~16 wt% | 12 wt% |
| n-파라핀 C21+ | 3~6 wt% | 4 wt% |
| 방향족 | 24~32 vol% | 28 vol% |

→ 본 시스템 `physical_model.py`의 HGO baseline CFPP = +14°C와 정합

## 디젤 블렌딩에서의 역할

### 긍정적 역할
- **수율 보강**: LGO만으로는 부족한 디젤 양을 채움
- **밀도 조정**: LGO만 사용 시 밀도 하한에 가까움 → HGO로 상향
- **세탄 보조**: HCC HGO의 세탄은 우수한 편

### 부정적 영향
- **CFPP 부담**: HGO 자체 CFPP가 +14°C로 매우 따뜻 → 디젤 풀 CFPP 끌어올림
- **n-파라핀 C21+ 高**: 변동성 신호, WAFI 효과 제한적
- **무게**: 디젤 밀도 상한(845 kg/m³) 위협

## 운영 비율

| 시즌 | 일반 HGO 비중 |
| --- | --- |
| 하절기 | 15~25% (CFPP 부담 적음) |
| 동절기 | 5~20% |
| 혹한기 | 0~10% (최소화) |

## CDU 직접 vs HCC 유래 비교

| 항목 | CDU 직접 HGO | HCC HGO |
| --- | --- | --- |
| 세탄 지수 | 45~50 | 48~52 |
| 밀도 | 850~865 | 845~855 |
| 방향족 | 28~32 | 22~28 |
| 색상 | 약간 노란빛 | 거의 무색 |
| 디젤 블렌딩 선호도 | 보통 | 높음 |

베테랑 연구원은 HCC 운전 모드를 함께 확인하여 HGO 품질을 추정한다.

## 베테랑 점검 포인트

1. **HGO 비중 25%+ 케이스**: 디젤 풀 CFPP 부담 심각, WAFI 강화 필수
2. **CDU HGO만 사용 시**: 세탄 미달 위험 → 세탄 향상제 검토
3. **n-파라핀 C21+ 4%+**: 변동성 위험 (`metric_variability` reason code)
4. **HCC 셧다운 시점**: HGO 공급원이 CDU 직접으로 일원화 → 품질 변동

## 출처

- ASTM D2887 (시뮬레이트 증류)
- API Technical Data Book
- 한국정유공업협회 HGO 가이드
- `ml/data_generation/physical_model.py` 정합
