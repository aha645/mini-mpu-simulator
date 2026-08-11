# Mini NPU Simulator

## 실행 방법

```
python main.py
```

- `1`: 사용자 입력 모드. 필터 A/B를 3×3 직접 입력하거나, N(홀수)을 정해 Cross/X 패턴을 자동 생성할 수 있습니다. 필터를 자동 생성한 경우 패턴도 직접 입력 또는 자동 생성(Cross/X 선택) 중 고를 수 있습니다.
- `2`: `data.json`을 읽어 일괄 판정합니다. 성능 분석 뒤에 2D vs 1D 최적화 비교도 함께 출력됩니다.

`data.json`은 `main.py`와 같은 디렉터리에 있어야 합니다.

## 구현 요약

- **데이터 구조**: `create_grid`/`set_cell`/`get_cell`로 n×n 리스트를 만들고 값을 저장·조회합니다.
- **라벨 정규화**: `normalize_label()`이 `cross`/`+` → `Cross`, `x` → `X`로 표준화합니다. 알 수 없는 라벨은 `expected=None`으로 처리하고 원본 값을 `expected_raw`에 남겨 원인 추적에 씁니다.
- **MAC 연산**: `mac_score()`가 이중 for문으로 패턴·필터를 위치별로 곱해 누적합니다(외부 라이브러리 없음). N×N이면 연산 횟수는 N².
- **동점(epsilon) 처리**: `judge()`는 `abs(score_cross - score_x) < 1e-9`이면 `UNDECIDED`를 반환합니다. 부동소수점 오차로 인해 수학적으로 같은 두 값이 `==`에서 다르게 나오는 문제를 막기 위함입니다.
- **필터·패턴 크기 검증**: `mode2_run()`은 MAC 연산 전에 (1)해당 크기 필터가 존재하는지, (2)패턴과 필터의 행·열 수가 일치하는지 검사합니다. 어긋나면 그 케이스만 FAIL 처리하고 다음으로 넘어가며 프로그램은 중단되지 않습니다. `compare_2d_1d_optimization()`도 동일한 검증을 거쳐, 필터가 없는 크기는 비교 대상에서 조용히 제외합니다.
- **Python 3.8 호환**: 파일 최상단에 `from __future__ import annotations`를 추가해, `list[list[float]]` 같은 타입 힌트(3.9+ 문법)가 3.8에서도 평가 없이(문자열로만 남아) 안전하게 동작하도록 했습니다.

### 보너스: 2D → 1D 메모리 접근 최적화

`grid2flat()`이 그리드를 길이 N² 1차원 리스트로 펼치고, `mac_score_flat()`이 `pattern_flat[i] * filter_flat[i]` 형태의 단일 인덱싱으로 계산합니다(기존은 `pattern[row][col]` 이중 인덱싱). `compare_2d_1d_optimization()`이 동일 입력·동일 반복 횟수(10회)로 2D/1D 평균 시간을 비교합니다.

### 보너스: 패턴 생성기

`generate_cross_pattern(n)`/`generate_x_pattern(n)`이 `create_grid`/`set_cell`로 N×N Cross·X 패턴을 만듭니다. 짝수 N은 정확한 중심이 없어(Cross는 중심 행/열이 애매하게 치우치고, X는 2×2 블록으로 뭉개짐) 홀수만 허용하고, 잘못된 입력은 재입력을 유도합니다. 모드1에서 필터(Cross/X 고정)와 패턴(직접 입력 또는 Cross/X 중 선택)을 이 생성기로 재활용할 수 있어, 3×3 고정이던 성능 측정을 원하는 크기로 재현할 수 있습니다.

## 결과 리포트

### 실행 결과 요약 (data.json 기준)

총 테스트: 10개 / 통과: 4개 / 실패: 6개

| 케이스 | Cross | X | 판정 | expected | 결과 |
|---|---|---|---|---|---|
| size_3_1 | 0.50 | 0.50 | UNDECIDED | X | FAIL |
| size_3_2 | 4.50 | 0.10 | Cross | Cross | PASS |
| size_3_3 | 4.50 | 0.10 | Cross | X | FAIL |
| size_5_1 | 0.90 | 0.90 | UNDECIDED | X | FAIL |
| size_5_2 | 8.90 | 0.10 | Cross | Cross | PASS |
| size_7_1 | - | - | SKIP | X | FAIL |
| size_13_1 | 0.30 | 14.70 | X | X | PASS |
| size_13_2 | 7.50 | 7.50 | UNDECIDED | Cross | FAIL |
| size_25_1 | 4.90 | 4.90 | UNDECIDED | X | FAIL |
| size_25_2 | 52.90 | 0.10 | Cross | Cross | PASS |

### 실패 원인 분석

실패 6건을 데이터/스키마, 수치 비교, 로직 세 원인으로 분류했습니다.

- **데이터/스키마 (1건)**: `size_7_1`은 data.json에 `size_7` 필터가 없어서 발생했습니다. 프로그램은 크래시 없이 이 케이스만 SKIP/FAIL 처리하고 나머지를 계속 진행합니다.
- **수치 비교 (4건)**: `size_3_1`, `size_5_1`, `size_13_2`, `size_25_1`은 Cross 점수와 X 점수가 정확히 같도록 설계된 케이스라 `judge()`가 `UNDECIDED`를 반환합니다. MAC 연산이 잘못된 게 아니라 "동점이면 판정 불가"라는 정책이 낳은 의도된 FAIL입니다.
- **로직 (1건)**: `size_3_3`은 필터·크기·라벨 모두 정상인데, 실제로 Cross 모양 패턴을 넣어두고 `expected`를 X로 지정해서 판정(Cross)과 기대값(X)이 어긋난 경우입니다.

### 성능 표와 시간 복잡도 (O(N²))

| 크기 | 평균 시간(ms) | 연산 횟수 |
|---|---|---|
| 3×3 | 0.0021 | 9 |
| 5×5 | 0.0043 | 25 |
| 13×13 | 0.0226 | 169 |
| 25×25 | 0.0809 | 625 |

(시간 값은 `time.perf_counter_ns()` 실측치라 실행할 때마다 조금씩 달라질 수 있습니다. "연산 횟수"는 N²로 항상 고정입니다.)

`mac_score()`는 모든 칸을 한 번씩 순회하므로 연산 횟수는 정확히 N²입니다(9→25→169→625). 다만 측정 시간의 증가율은 이보다 완만합니다(3×3→25×25: 연산 횟수 약 69배, 시간은 약 39배). 측정 시간에는 곱셈·덧셈(N²에 비례) 외에 함수 호출 같은 고정 오버헤드가 섞여 있어서, 계산량이 작은 3×3에서는 오버헤드 비중이 상대적으로 커 증가율을 눌러줍니다. 반대로 13×13→25×25처럼 이미 계산량이 큰 구간에서는 오버헤드 비중이 작아져 연산 횟수 비율(약 3.7배)과 시간 비율(약 3.6배)이 훨씬 가까워집니다. 즉 크기가 커질수록 실측치가 O(N²) 이론값에 가까워집니다.

### 2D vs 1D 최적화 비교 (보너스)

| 크기 | 2D 평균(ms) | 1D 평균(ms) | 개선비율 |
|---|---|---|---|
| 3×3 | 0.0020 | 0.0012 | 39.7% |
| 5×5 | 0.0043 | 0.0023 | 47.5% |
| 13×13 | 0.0225 | 0.0131 | 41.8% |
| 25×25 | 0.0795 | 0.0496 | 37.6% |

1D 버전은 칸 하나당 인덱싱이 4회(2D: `pattern[row][col]`+`filter[row][col]`)에서 2회(1D: `pattern_flat[i]`+`filter_flat[i]`)로 줄어 모든 크기에서 37~48% 더 빠릅니다. 곱셈·덧셈 비용은 2D/1D 동일하고 인덱싱만 줄어들기 때문에 개선비율은 크기와 무관하게 비슷한 범위를 유지하며, 절약되는 절대 시간은 연산 횟수(N²)만큼 누적되어 크기가 클수록 커집니다.

### 대형 N(1000×1000)에서의 한계 (참고 분석)

data.json 최대 크기(25×25)를 훨씬 넘어서는 N=1001(홀수 제약 유지)에서 실측한 결과입니다.

**시간 측정**

| 항목 | 값 |
|---|---|
| 2D `mac_score` 1회 | 58.50 ms |
| 1D `mac_score_flat` 1회 | 54.27 ms |
| 2D 평균(10회) | 57.15 ms |
| 1D 평균(10회) | 50.18 ms |
| 개선율 | 12.2% |
| 인덱싱 루프 | 52.25 ms |
| zip/sum | 59.75 ms |

연산 횟수 1,002,001회 기준, 1D가 2D보다 약 12% 빠르고, 명시적 인덱싱 루프가 zip/sum보다 약 7.5ms(약 14%) 더 빠릅니다.

**메모리 측정**

| 항목 | 값 |
|---|---|
| 2D 그리드 3개(list) | 25.39 MB |
| list[float] 1개(컨테이너만) | 8.06 MB |
| array('d') 1개(원소 포함) | 7.64 MB |

그리드 3개(pattern+cross_filter+x_filter)를 동시에 들면 약 25MB. `array`가 `list`보다 컨테이너 자체는 살짝 작지만, `list`의 진짜 비용은 원소 하나하나가 별도 float 객체(24바이트)라는 점에 있어서 실질 절감 효과는 원소 개수(N²)가 커질수록 커집니다.
```code
import sys, time, array, tracemalloc
from main import (
    generate_cross_pattern, generate_x_pattern,
    mac_score, mac_score_flat, grid2flat, avg_mac_time,
)

n = 1001  # 홀수 제약 유지

# --- 시간 측정 ---
pattern = generate_cross_pattern(n)
cross_filter = generate_cross_pattern(n)

t0 = time.perf_counter_ns()
mac_score(pattern, cross_filter)
t1 = time.perf_counter_ns()
print(f"2D mac_score 1회: {(t1 - t0) / 1_000_000:.2f} ms")

flat_p = grid2flat(pattern)
flat_c = grid2flat(cross_filter)

t0 = time.perf_counter_ns()
mac_score_flat(flat_p, flat_c)
t1 = time.perf_counter_ns()
print(f"1D mac_score_flat 1회: {(t1 - t0) / 1_000_000:.2f} ms")

avg2d = avg_mac_time(pattern, cross_filter, 10, mac_score)
avg1d = avg_mac_time(flat_p, flat_c, 10, mac_score_flat)
print(f"2D 평균(10회): {avg2d:.2f} ms, 1D 평균(10회): {avg1d:.2f} ms, "
      f"개선율: {(avg2d - avg1d) / avg2d * 100:.1f}%")
print(f"연산 횟수(N²): {n * n:,}")

# --- 메모리 측정 (list vs array) ---
tracemalloc.start()
p2 = generate_cross_pattern(n)
c2 = generate_cross_pattern(n)
x2 = generate_x_pattern(n)
current, peak = tracemalloc.get_traced_memory()
print(f"2D 그리드 3개(list): 현재 {current / 1024 / 1024:.2f} MB")
tracemalloc.stop()

arr_p = array.array('d', flat_p)
arr_c = array.array('d', flat_c)
print("list[float] 1개:", sys.getsizeof(flat_p) / 1024 / 1024, "MB (컨테이너만, 원소 객체 별도)")
print("array('d') 1개:", sys.getsizeof(arr_p) / 1024 / 1024, "MB (원소 포함 실제 크기)")

# --- 인덱싱 루프 vs zip/sum ---
def mac_flat_loop(p, f):
    total = 0.0
    for i in range(len(p)):
        total += p[i] * f[i]
    return total

def mac_flat_zip(p, f):
    return sum(a * b for a, b in zip(p, f))

t0 = time.perf_counter_ns(); mac_flat_loop(flat_p, flat_c); t1 = time.perf_counter_ns()
print("list + 인덱싱 루프:", (t1 - t0) / 1_000_000, "ms")

t0 = time.perf_counter_ns(); mac_flat_zip(flat_p, flat_c); t1 = time.perf_counter_ns()
print("list + zip/sum:", (t1 - t0) / 1_000_000, "ms")
```

### MODE2 실행 로그
```bash
=== Mini NPU Simulator ===
[모드 선택]
1. 사용자 입력 (3x3)
2. data.json 분석
선택: 2
#----------------------------------------
#[1] 필터 로드
#----------------------------------------
✔︎size_3 필터 로드 완료(Cross ,X)
✔︎size_5 필터 로드 완료(Cross ,X)
✔︎size_13 필터 로드 완료(Cross ,X)
✔︎size_25 필터 로드 완료(Cross ,X)
#----------------------------------------
#[2] 패턴 분석(라벨 정규화 적용)
#----------------------------------------
-- size_3_1 --
Cross 점수: 0.50
X 점수      : 0.50
판정: UNDECIDED|expected: X|FAIL(동점규칙)
-- size_3_2 --
Cross 점수: 4.50
X 점수      : 0.10
판정: Cross|expected: Cross|PASS
-- size_3_3 --
Cross 점수: 4.50
X 점수      : 0.10
판정: Cross|expected: X|FAIL(로직)
-- size_5_1 --
Cross 점수: 0.90
X 점수      : 0.90
판정: UNDECIDED|expected: X|FAIL(동점규칙)
-- size_5_2 --
Cross 점수: 8.90
X 점수      : 0.10
판정: Cross|expected: Cross|PASS
-- size_7_1 --
판정: SKIP|expected: X|FAIL(데이터/스키마)
-- size_13_1 --
Cross 점수: 0.30
X 점수      : 14.70
판정: X|expected: X|PASS
-- size_13_2 --
Cross 점수: 7.50
X 점수      : 7.50
판정: UNDECIDED|expected: Cross|FAIL(동점규칙)
-- size_25_1 --
Cross 점수: 4.90
X 점수      : 4.90
판정: UNDECIDED|expected: X|FAIL(동점규칙)
-- size_25_2 --
Cross 점수: 52.90
X 점수      : 0.10
판정: Cross|expected: Cross|PASS
#----------------------------------------
# [3] 성능 분석 (평균/10회)
#----------------------------------------
크기        평균 시간(ms)   연산 횟수
#----------------------------------------
3x3                0.0015           9
5x5                0.0027          25
13x13              0.0114         169
25x25              0.0335         625

크기          2D 평균(ms)    1D 평균(ms)  개선비율
3x3                0.0012         0.0008     31.8%
5x5                0.0022         0.0013     42.9%
13x13              0.0101         0.0065     35.7%
25x25              0.0332         0.0293     11.6%

#---------------------------------------
# [4] 결과 요약
#---------------------------------------
총 테스트: 10개
통과: 4개
실패: 6개

실패 케이스:
- size_3_1: [수치비교] 동점(UNDECIDED) 처리 규칙에 따라 FAIL
- size_3_3: [로직] expected=X, predicted=Cross
- size_5_1: [수치비교] 동점(UNDECIDED) 처리 규칙에 따라 FAIL
- size_7_1: [데이터/스키마] size_7 필터를 찾을 수 없음
- size_13_2: [수치비교] 동점(UNDECIDED) 처리 규칙에 따라 FAIL
- size_25_1: [수치비교] 동점(UNDECIDED) 처리 규칙에 따라 FAIL
```