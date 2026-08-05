# Mini NPU Simulator — 개발 가이드 (dev_guide.md)

이 문서는 "Mini NPU 시뮬레이터" 과제를 처음부터 끝까지 풀어나가기 위한
**학습 로드맵 + 단계별 구현 설계 + 실제 코드 스니펫 + 실행/검증 커맨드**를 정리한 것이다.
`main.py`를 바로 완성하기보다, 아래 순서를 그대로 따라가며 하나씩 만들고 실행해보면
요구사항을 빠짐없이 채울 수 있도록 구성했다.

---

## 0. 큰 그림부터 잡기

과제가 요구하는 것은 결국 3가지 축이다.

1. **연산 로직**: 2차원 배열끼리 위치별 곱셈 후 누적합 (MAC) → 이게 전부다.
2. **입출력/검증 로직**: 콘솔 입력 검증, JSON 스키마 검증, 라벨 정규화, epsilon 비교.
3. **계측/리포트 로직**: 반복 측정 후 평균 시간(ms) 계산, PASS/FAIL 집계, README 서술.

이 세 축을 각각 **독립된 함수**로 분리해서 만들면, 모드 1(콘솔 입력)과 모드 2(JSON 분석)가
같은 MAC 함수·같은 판정 함수·같은 계측 함수를 재사용하게 되어 코드 중복이 없어진다.
아래 단계들은 이 분리를 그대로 따른다.

---

## 1. 사전 학습 체크리스트

구현에 들어가기 전에 아래 개념들을 짧게라도 확인하고 시작하는 것을 권장한다.

| 개념 | 왜 필요한가 | 확인 방법 |
|---|---|---|
| 2차원 리스트 (`[[0]*n for _ in range(n)]`) | 패턴/필터 저장 구조 | `list comprehension`으로 `n*[0]`을 n번 복사하면 **참조 공유 버그**가 생김 — 반드시 `for _ in range(n)`으로 각 행을 새로 생성해야 함 |
| `input().split()` + `float()`/형변환 | 콘솔 입력 파싱 | `ValueError` 발생 지점을 알아야 검증 가능 |
| `try/except` | 입력 검증, JSON 스키마 검증 | 모드 1 재입력 루프, 모드 2 케이스별 FAIL 처리 둘 다 이 패턴 사용 |
| `json.load` / `dict.get()` | data.json 파싱 | 키가 없을 때 `KeyError` 대신 `.get()`으로 안전하게 접근 |
| IEEE 754 부동소수점 오차 | `0.9`와 `0.8999999999999999`가 다른 값으로 계산되는 이유 | 파이썬 콘솔에서 `0.1 + 0.2` 쳐보기 → `0.30000000000000004` |
| `time.perf_counter()` | 정밀한 구간 시간 측정 | `time.time()`보다 단조증가·고해상도라 성능 측정에 적합 |
| 시간 복잡도 O(N²) | 성능 분석 리포트 근거 | N×N 필터의 MAC 연산은 반드시 N² 번의 곱셈 필요 → 이중 for문 구조 자체가 증거 |

**빠른 개념 확인 커맨드** (터미널에서 파이썬 인터랙티브로 직접 확인):

```bash
python3 --version        # 3.8 이상인지 확인
python3
```

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> a = [[0]*3]*3          # 잘못된 방법: 행이 서로 같은 리스트를 참조함(버그 재현용)
>>> a[0][0] = 9
>>> a
[[9, 0, 0], [9, 0, 0], [9, 0, 0]]   # 모든 행이 같이 바뀜 -> 이래서 안 됨
>>> b = [[0]*3 for _ in range(3)]  # 올바른 방법
>>> b[0][0] = 9
>>> b
[[9, 0, 0], [0, 0, 0], [0, 0, 0]]
>>> import time
>>> time.perf_counter()
```

이 버그(얕은 복사로 행 공유)를 미리 눈으로 확인해두면, 나중에 `create_grid()` 구현 시
실수하지 않는다.

---

## 2. 프로젝트 초기 세팅

```bash
cd /Users/thinkover20221658/Documents/mini-calc
touch main.py data.json README.md
ls -la
```

외부 라이브러리를 쓰지 않으므로 가상환경(venv)은 필수는 아니지만,
습관적으로 분리하고 싶다면:

```bash
python3 -m venv venv
source venv/bin/activate   # 종료 시 deactivate
```

Git으로 버전 관리를 하고 싶다면 (선택 사항, 과제 제출에는 불필요):

```bash
git init
git add main.py data.json README.md
git commit -m "chore: init mini npu simulator skeleton"
```

---

## 3. 데이터 구조 & MAC 연산 함수 (핵심 로직)

가장 먼저 이 부분부터 만든다. 나머지 기능은 전부 이 함수를 감싸는 껍데기이기 때문이다.

```python
# main.py

EPSILON = 1e-9

def create_grid(n: int, fill=0.0):
    """n x n 크기의 2차원 리스트를 생성한다. 행마다 새 리스트를 만들어야 참조 공유 버그를 피한다."""
    return [[fill for _ in range(n)] for _ in range(n)]


def set_cell(grid, row, col, value):
    grid[row][col] = value


def get_cell(grid, row, col):
    return grid[row][col]


def mac_score(pattern, filt) -> float:
    """
    입력 패턴과 필터를 위치별로 곱하고 모두 더한다 (Multiply-Accumulate).
    외부 라이브러리 없이 이중 for문으로만 구현 -> 이 이중 루프 자체가 O(N^2)의 근거.
    """
    n = len(filt)
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += pattern[i][j] * filt[i][j]
    return total
```

**바로 검증**: 파이썬 인터랙티브 셸에서 과제 예시 값으로 직접 테스트한다.

```bash
python3 -c "
from main import mac_score
cross = [[0,1,0],[1,1,1],[0,1,0]]
x_pat = [[1,0,1],[0,1,0],[1,0,1]]
print(mac_score(cross, cross))  # 5.0 이어야 함
print(mac_score(cross, x_pat))  # 1.0 이어야 함
"
```

이 두 값이 미션 설명의 Case 1(5), Case 2(1)과 일치하는지 확인하고 다음 단계로 넘어간다.

---

## 4. 판정 로직 (epsilon 기반 비교)

```python
def judge(score_cross: float, score_x: float) -> str:
    """
    두 점수를 epsilon 기준으로 비교해 'Cross' / 'X' / 'UNDECIDED' 를 반환한다.
    """
    diff = abs(score_cross - score_x)
    if diff < EPSILON:
        return "UNDECIDED"
    return "Cross" if score_cross > score_x else "X"
```

- 왜 `==` 대신 epsilon 비교인가: 부동소수점 연산은 수학적으로 같은 값이라도
  계산 순서에 따라 마지막 비트가 달라질 수 있다 (`0.9` vs `0.8999999999999999`).
  `==`로 비교하면 "동점이어야 할 케이스"가 동점이 아니라고 잘못 판정될 수 있다.
- `1e-9`라는 임계값 자체는 "이 정도 오차는 계산 방식의 차이로 보고 무시한다"는
  **정책**이다. README에 이 정책을 명시적으로 서술해야 한다 (요구사항 6번).

---

## 5. 라벨 정규화 (Cross / X 표준화)

data.json의 필터 키(`cross`, `x`)와 expected 값(`+`, `x`)이 서로 다른 표기를 쓰기 때문에,
내부적으로는 항상 `"Cross"` / `"X"` 두 가지 표준 라벨만 쓰도록 변환하는 함수가 필요하다.

```python
def normalize_label(raw) -> str:
    """
    다양한 표기를 표준 라벨('Cross' 또는 'X')로 변환한다.
    - filter 키: 'cross' -> Cross, 'x' -> X
    - expected 값: '+' -> Cross, 'x' -> X
    알 수 없는 라벨이면 ValueError를 던진다 (호출부에서 케이스 단위 FAIL로 처리).
    """
    key = str(raw).strip().lower()
    if key in ("cross", "+"):
        return "Cross"
    if key == "x":
        return "X"
    raise ValueError(f"알 수 없는 라벨: {raw!r}")
```

**설계 포인트**: 이 함수를 한 군데에만 두고, 필터 로드/expected 비교 두 곳에서 모두 재사용한다.
"정규화 로직이 여러 군데 흩어지면" 나중에 표기가 하나 더 추가됐을 때(`X`, `x`, `X-pattern` 등)
전부 찾아 고쳐야 하는 유지보수 문제가 생긴다 — 이게 과제 목표 3번("라벨을 표준화하는 이유")의
핵심 논지다.

---

## 6. 모드 1: 콘솔 입력 + 검증 (3×3)

### 6-1. 입력 함수 설계

요구사항: "행 수/열 수 불일치, 숫자 파싱 실패 시 안내 문구 출력 후 재입력 유도".
→ `while True` 루프 + `try/except`로 감싸고, 실패하면 `continue`로 되돌아간다.

```python
def read_grid_from_console(n: int, label: str):
    """
    n줄을 입력받아 n x n 2차원 리스트로 변환한다.
    각 줄은 공백으로 구분된 n개의 숫자여야 한다. 실패 시 안내 후 처음부터 다시 입력받는다.
    """
    while True:
        print(f"{label} ({n}줄 입력, 공백 구분)")
        rows = []
        ok = True
        for _ in range(n):
            line = input().strip()
            tokens = line.split()
            if len(tokens) != n:
                print(f"입력 형식 오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
                ok = False
                break
            try:
                rows.append([float(t) for t in tokens])
            except ValueError:
                print(f"입력 형식 오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
                ok = False
                break
        if ok:
            return rows
        # ok=False면 while True로 돌아가 처음부터 다시 n줄 입력받음
```

### 6-2. 모드 1 흐름 함수

```python
def run_mode_console():
    print("\n#----------------------------------------")
    print("# [1] 필터 입력")
    print("#----------------------------------------")
    filter_a = read_grid_from_console(3, "필터 A")
    filter_b = read_grid_from_console(3, "필터 B")

    print("\n#----------------------------------------")
    print("# [2] 패턴 입력")
    print("#----------------------------------------")
    pattern = read_grid_from_console(3, "패턴")

    print("\n#----------------------------------------")
    print("# [3] MAC 결과")
    print("#----------------------------------------")
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)
    avg_ms = measure_mac_time_repeated(pattern, filter_a, repeat=10)  # 7단계에서 정의

    diff = abs(score_a - score_b)
    if diff < EPSILON:
        verdict = f"판정 불가 (|A-B| < 1e-9)"
    else:
        verdict = "A" if score_a > score_b else "B"

    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/10회): {avg_ms:.3f} ms")
    print(f"판정: {verdict}")
```

### 6-3. 빠른 수동 테스트

파이프로 입력을 흘려보내면 대화형 실행 없이도 검증할 수 있다.

```bash
printf "0 1 0\n1 1 1\n0 1 0\n1 0 1\n0 1 0\n1 0 1\n1 0 1\n0 1 0\n1 0 1\n" | python3 main.py
```

(입력 순서: 필터A 3줄 → 필터B 3줄 → 패턴 3줄. 실제로는 모드 선택 `1`도 먼저 입력해야 하므로
아래처럼 맨 앞에 `1\n`을 붙인다.)

```bash
printf "1\n0 1 0\n1 1 1\n0 1 0\n1 0 1\n0 1 0\n1 0 1\n1 0 1\n0 1 0\n1 0 1\n" | python3 main.py
```

**잘못된 입력으로 검증 로직 테스트** (열 개수 2개짜리 줄 섞기):

```bash
printf "1\n0 1\n1 1 1\n0 1 0\n" | python3 main.py
```
→ "입력 형식 오류" 문구가 뜨고 재입력을 요구하는지 확인 (Ctrl+C로 중단).

---

## 7. 성능 측정 함수

```python
import time

def measure_mac_time_repeated(pattern, filt, repeat=10):
    """
    MAC 연산을 repeat회 반복 측정해 평균 시간을 ms 단위로 반환한다.
    I/O(입력, 출력, 파일 읽기)는 측정 구간에서 제외하고, 순수 연산 함수 호출만 감싼다.
    """
    total_ms = 0.0
    for _ in range(repeat):
        start = time.perf_counter()
        mac_score(pattern, filt)
        end = time.perf_counter()
        total_ms += (end - start) * 1000
    return total_ms / repeat
```

**설계 포인트**: `measure_mac_time_repeated`는 filt/pattern 크기에 무관하게 재사용 가능하다.
모드 1의 3×3뿐 아니라 모드 2의 5×5/13×13/25×25 성능 표에도 이 함수 그대로 쓴다.

작은 크기(3×3)는 연산이 마이크로초 단위라 측정값이 튈 수 있다는 점을 README에서
언급하면 좋다 (OS 스케줄링 노이즈, 파이썬 인터프리터 오버헤드 등).

---

## 8. 모드 2: data.json 준비 & 스키마 이해

### 8-1. data.json 스키마 설계

요구사항에 따라 아래 구조로 만든다 (5×5, 13×13, 25×25 필터 + 여러 패턴).
아래는 5×5만 손으로 채운 최소 예시다 — 13×13, 25×25는 8-2의 생성 스크립트로 만든다.

```json
{
  "filters": {
    "size_5": {
      "cross": [
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0]
      ],
      "x": [
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,1,0,1,0],
        [1,0,0,0,1]
      ]
    }
  },
  "patterns": {
    "size_5_1": {
      "input": [
        [1,0,0,0,1],
        [0,1,0,1,0],
        [0,0,1,0,0],
        [0,1,0,1,0],
        [1,0,0,0,1]
      ],
      "expected": "x"
    },
    "size_5_2": {
      "input": [
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0]
      ],
      "expected": "+"
    }
  }
}
```

**키 규칙 요약** (README 구현 요약에 그대로 옮겨 적으면 됨):
- `filters.size_N.{cross|x}` : N×N 2차원 배열
- `patterns.size_N_idx.input` : N×N 2차원 배열
- `patterns.size_N_idx.expected` : `"+"`(Cross) 또는 `"x"`(X)
- 패턴 키의 `N`을 파싱해서 같은 `size_N` 필터를 찾아 매칭한다.

### 8-2. 13×13, 25×25 데이터 자동 생성 스크립트 (보너스 "패턴 생성기"와 연결)

손으로 13×13, 25×25를 채우는 것은 비현실적이므로, 십자가/X 패턴을 자동 생성하는
헬퍼를 먼저 만들고 그걸로 data.json을 채운다. 이 함수는 나중에 보너스 과제
"패턴 생성기"로도 그대로 재사용된다.

```python
def generate_cross(n):
    mid = n // 2
    return [[1.0 if (i == mid or j == mid) else 0.0 for j in range(n)] for i in range(n)]

def generate_x(n):
    return [[1.0 if (i == j or i + j == n - 1) else 0.0 for j in range(n)] for i in range(n)]
```

이 두 함수로 data.json 생성 스크립트를 별도 파일로 작성한다 (제출물에는 포함 안 해도 되지만
개발 과정에서 유용):

```bash
touch scripts_generate_data.py
```

```python
# scripts_generate_data.py (개발용 보조 스크립트, main.py와는 별개)
import json
from main import generate_cross, generate_x

def build():
    data = {"filters": {}, "patterns": {}}
    for n in (5, 13, 25):
        cross = generate_cross(n)
        x = generate_x(n)
        data["filters"][f"size_{n}"] = {"cross": cross, "x": x}
        # 케이스 1: X 패턴이 입력 -> expected는 x
        data["patterns"][f"size_{n}_1"] = {"input": x, "expected": "x"}
        # 케이스 2: Cross 패턴이 입력 -> expected는 +
        data["patterns"][f"size_{n}_2"] = {"input": cross, "expected": "+"}
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    build()
```

```bash
python3 scripts_generate_data.py
python3 -c "import json; d=json.load(open('data.json')); print(list(d['filters'].keys())); print(list(d['patterns'].keys()))"
```

이후 손으로 몇 개 케이스를 편집해서, **일부러 동점(0.9 vs 0.8999999999999999)이 나는 케이스**나
**필터/패턴 크기가 일치하지 않는 케이스**를 하나씩 추가해두면, PASS/FAIL 리포트와
스키마 검증 로직을 실제로 테스트할 수 있다 (요구사항의 "재현성" 항목).

동점 케이스를 인위적으로 만들려면 부동소수점 연산 특성을 이용한다:

```bash
python3 -c "
a = 0.1+0.1+0.1+0.1+0.1+0.1+0.1+0.1+0.1
b = 0.9
print(a, b, a==b)   # a와 b가 미세하게 다르게 나오는지 확인
"
```
→ 이런 값을 패턴/필터에 소수로 심어두면 "동점처럼 보이지만 epsilon 안에 들어오는" 케이스를
만들 수 있다.

---

## 9. 모드 2: JSON 로드 & 스키마 검증

```python
import json

def load_data_json(path="data.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_filters(raw_data):
    """
    { 5: {"Cross": [...], "X": [...]}, 13: {...}, 25: {...} } 형태로 정규화해서 반환.
    """
    filters = {}
    for size_key, filt_map in raw_data.get("filters", {}).items():
        n = int(size_key.split("_")[1])  # "size_5" -> 5
        normalized = {}
        for label_key, grid in filt_map.items():
            std_label = normalize_label(label_key)
            normalized[std_label] = grid
        filters[n] = normalized
    return filters


def parse_pattern_size(pattern_key):
    """ "size_13_1" -> 13 """
    parts = pattern_key.split("_")
    return int(parts[1])
```

### 9-1. 케이스 단위 검증 + FAIL 처리 (프로그램이 죽지 않도록)

요구사항 핵심: **크기 불일치/스키마 문제로 예외가 나도 프로그램은 계속 돌아야 한다.**
→ 케이스 하나를 처리하는 로직을 함수로 뽑고, 그 안에서 발생하는 문제를
"결과 dict"로 변환해 반환한다 (예외를 밖으로 던지지 않는다).

```python
def evaluate_pattern_case(case_key, case_data, filters):
    """
    한 개의 패턴 케이스를 평가한다. 실패해도 예외를 던지지 않고
    result dict의 status/reason 필드로 실패를 표현한다.
    """
    result = {
        "key": case_key,
        "status": "FAIL",
        "reason": "",
        "score_cross": None,
        "score_x": None,
        "verdict": None,
        "expected": None,
    }

    try:
        n = parse_pattern_size(case_key)
    except (IndexError, ValueError):
        result["reason"] = f"패턴 키 형식 오류: {case_key}"
        return result

    if n not in filters:
        result["reason"] = f"크기 불일치: size_{n} 필터가 존재하지 않음"
        return result

    pattern = case_data.get("input")
    if pattern is None or len(pattern) != n or any(len(row) != n for row in pattern):
        result["reason"] = f"패턴 크기가 size_{n}과 일치하지 않음"
        return result

    filt_cross = filters[n].get("Cross")
    filt_x = filters[n].get("X")
    if filt_cross is None or filt_x is None:
        result["reason"] = f"size_{n} 필터에 Cross/X가 모두 존재하지 않음"
        return result

    try:
        expected = normalize_label(case_data.get("expected"))
    except ValueError as e:
        result["reason"] = str(e)
        return result

    score_cross = mac_score(pattern, filt_cross)
    score_x = mac_score(pattern, filt_x)
    verdict = judge(score_cross, score_x)

    result["score_cross"] = score_cross
    result["score_x"] = score_x
    result["verdict"] = verdict
    result["expected"] = expected

    if verdict == expected:
        result["status"] = "PASS"
        result["reason"] = ""
    else:
        result["status"] = "FAIL"
        if verdict == "UNDECIDED":
            result["reason"] = "동점(UNDECIDED) 처리 규칙에 따라 FAIL"
        else:
            result["reason"] = f"판정 불일치: 판정={verdict}, expected={expected}"

    return result
```

이렇게 만들면 "스키마 문제", "로직 문제(판정 불일치)", "수치 비교 문제(동점)" 세 가지가
`reason` 문자열로 명확히 구분되어 나온다 — 과제 목표 6번을 그대로 충족한다.

### 9-2. 모드 2 전체 흐름

```python
def run_mode_json(path="data.json"):
    print("\n#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")
    raw = load_data_json(path)
    filters = load_filters(raw)
    for n in sorted(filters.keys()):
        print(f"✓ size_{n} 필터 로드 완료 ({', '.join(filters[n].keys())})")

    print("\n#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")
    results = []
    for case_key, case_data in raw.get("patterns", {}).items():
        r = evaluate_pattern_case(case_key, case_data, filters)
        results.append(r)
        print(f"--- {case_key} ---")
        if r["score_cross"] is not None:
            print(f"Cross 점수: {r['score_cross']}")
            print(f"X 점수: {r['score_x']}")
            print(f"판정: {r['verdict']} | expected: {r['expected']} | {r['status']}"
                  + (f" ({r['reason']})" if r["status"] == "FAIL" else ""))
        else:
            print(f"{r['status']} ({r['reason']})")

    print("\n#---------------------------------------")
    print("# [3] 성능 분석 (평균/10회)")
    print("#---------------------------------------")
    print(f"{'크기':<10}{'평균 시간(ms)':<16}{'연산 횟수':<10}")
    print("-" * 37)
    for n in [3] + sorted(filters.keys()):
        pattern = generate_cross(n)   # 성능 측정용 임의 패턴 (십자가 재사용)
        filt = generate_cross(n)
        avg_ms = measure_mac_time_repeated(pattern, filt, repeat=10)
        print(f"{n}×{n:<8}{avg_ms:<16.3f}{n*n:<10}")

    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = total - passed
    print(f"총 테스트: {total}개")
    print(f"통과: {passed}개")
    print(f"실패: {failed}개")
    if failed:
        print("\n실패 케이스:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"- {r['key']}: {r['reason']}")
```

### 9-2 검증 커맨드

```bash
printf "2\n" | python3 main.py
```

일부러 스키마를 깨서 FAIL 경로를 테스트:

```bash
python3 -c "
import json
d = json.load(open('data.json'))
d['patterns']['size_5_1']['input'] = [[1,0],[0,1]]   # 크기 불일치 유발
json.dump(d, open('data_broken.json','w'), indent=2, ensure_ascii=False)
"
printf "2\n" | python3 -c "
import main
main.run_mode_json('data_broken.json')
"
```
→ 프로그램이 죽지 않고 해당 케이스만 FAIL로 처리되는지 확인 후 `data_broken.json` 삭제.

```bash
rm -f data_broken.json
```

---

## 10. main() — 전체 실행 흐름 통합

```python
def main():
    print("=== Mini NPU Simulator ===")
    print("\n[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    choice = input("선택: ").strip()

    if choice == "1":
        run_mode_console()
    elif choice == "2":
        run_mode_json("data.json")
    else:
        print("잘못된 선택입니다. 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
```

파일 맨 위에 `generate_cross`, `generate_x`가 정의돼 있어야 하므로,
8-2에서 만든 두 함수를 `main.py` 상단부(데이터 구조 섹션 근처)로 옮겨 넣는다.

---

## 11. 전체 통합 후 스모크 테스트

```bash
# 모드 1 스모크 테스트
printf "1\n0 1 0\n1 1 1\n0 1 0\n1 0 1\n0 1 0\n1 0 1\n1 0 1\n0 1 0\n1 0 1\n" | python3 main.py

# 모드 2 스모크 테스트
printf "2\n" | python3 main.py

# 잘못된 모드 선택 테스트
printf "9\n" | python3 main.py
```

세 커맨드 모두 예외 없이 끝까지 출력되는지 확인한다. 특히 모드 2 실행 후
"총 테스트/통과/실패" 숫자가 화면에 나온 PASS/FAIL 라인 개수와 정확히 일치하는지
손으로 세어 대조한다 (재현성 요구사항).

---

## 12. 보너스 과제로 확장하기

### 12-1. 1차원 배열 최적화

```python
def create_grid_1d(n, fill=0.0):
    return [fill] * (n * n)

def mac_score_1d(pattern_1d, filt_1d, n):
    total = 0.0
    for idx in range(n * n):
        total += pattern_1d[idx] * filt_1d[idx]
    return total

def to_1d(grid):
    return [v for row in grid for v in row]
```

동일 입력·동일 반복 횟수로 `mac_score` vs `mac_score_1d`를 `measure_mac_time_repeated`에
각각 넣어 비교하고, 결과를 README에 표로 추가한다.

```bash
python3 -c "
from main import generate_cross, to_1d, mac_score, mac_score_1d, measure_mac_time_repeated
import time
n = 25
g = generate_cross(n)
g1d = to_1d(g)
t2d = measure_mac_time_repeated(g, g, repeat=10)
# 1d 버전은 measure 함수 시그니처가 다르므로 별도 반복 측정 코드 작성 필요
print('2D 평균(ms):', t2d)
"
```

### 12-2. 패턴 생성기 재활용

`generate_cross(n)`, `generate_x(n)`을 모드 1 진입 전에 "예시 패턴 자동 채우기" 옵션으로
연결하거나, 성능 분석 표의 입력 데이터로 재사용한다 (9-2의 `[3] 성능 분석`에서 이미 활용 중).

---

## 13. README.md 작성 가이드 (제출 문서)

`README.md`에는 최소 아래 섹션이 있어야 한다. 각 섹션에 무엇을 쓸지 짧게 정리:

1. **실행 방법**
   - `python3 main.py` 실행 → 모드 1/2 선택 안내
   - data.json은 `main.py`와 같은 디렉터리에 위치해야 함
2. **구현 요약**
   - 라벨 정규화: `normalize_label()`이 `+`/`cross` → `Cross`, `x` → `X`로 표준화하는 이유
   - MAC 연산: 이중 for문 기반, 외부 라이브러리 미사용
   - 동점 처리 정책: `abs(a-b) < 1e-9`이면 `UNDECIDED`
3. **결과 리포트** (최소 10줄 이상)
   - 실행 후 나온 실제 총/통과/실패 숫자를 붙여넣기
   - FAIL 케이스가 있다면 케이스별로 "스키마 문제 / 로직 문제 / 수치 비교 문제" 중 어디에
     해당하는지 분류해서 서술
   - FAIL이 0개라면: 왜 0개가 됐는지 (patterns를 `generate_cross`/`generate_x`로 정확히
     생성했기 때문에 판정이 항상 명확하게 갈렸다는 점, epsilon 정책 덕분에 부동소수점
     오차가 오판정으로 이어지지 않았다는 점)을 서술
   - 성능 표를 붙이고, N이 커질수록 시간이 N²에 비례해 늘어나는지 실측값으로 근거 제시
     (예: 5×5 대비 25×25는 연산 횟수가 25배인데 측정 시간도 대략 그 배수로 늘어나는지 확인)

**성능 표 붙여넣기용 커맨드** (모드 2 실행 결과를 파일로 저장):

```bash
printf "2\n" | python3 main.py > run_output.txt
cat run_output.txt
```
→ `run_output.txt`의 `[3] 성능 분석`, `[4] 결과 요약` 블록을 그대로 README에 인용한다.

---

## 14. 요구사항 ↔ 구현 매핑 체크리스트

제출 전 아래 표로 빠짐없이 구현했는지 자가 점검한다.

| 요구사항 | 구현 위치 |
|---|---|
| n×n 저장/읽기/쓰기 | `create_grid`, `get_cell`, `set_cell` |
| 모드1 입력 검증 + 재입력 유도 | `read_grid_from_console` |
| data.json 로드 | `load_data_json` |
| 필터/패턴 크기 검증, 불일치 시 FAIL | `evaluate_pattern_case` |
| 라벨 정규화 | `normalize_label` |
| MAC 연산 (외부 라이브러리 금지) | `mac_score` |
| epsilon 비교 | `judge` (EPSILON = 1e-9) |
| 성능 측정 (10회 평균, ms) | `measure_mac_time_repeated` |
| 성능 표 (크기/평균시간/연산횟수) | `run_mode_json`의 `[3] 성능 분석` 블록 |
| 결과 요약 (총/통과/실패 + 실패 사유) | `run_mode_json`의 `[4] 결과 요약` 블록 |
| 프로그램 비정상 종료 방지 | `evaluate_pattern_case`가 예외를 삼키고 dict로 반환 |
| 실행 흐름 순서 | `main()` → `run_mode_console()` / `run_mode_json()` |

---

## 15. 다음 실행 순서 요약 (Quick Start)

```bash
cd /Users/thinkover20221658/Documents/mini-calc
python3 --version                       # 3.8+ 확인
# main.py 작성 (3~10단계 코드 순서대로 채우기)
python3 scripts_generate_data.py        # data.json 생성 (8-2)
printf "1\n0 1 0\n1 1 1\n0 1 0\n1 0 1\n0 1 0\n1 0 1\n1 0 1\n0 1 0\n1 0 1\n" | python3 main.py   # 모드1 테스트
printf "2\n" | python3 main.py          # 모드2 테스트
printf "2\n" | python3 main.py > run_output.txt   # README용 출력 캡처
# README.md 작성 (13단계 가이드 참고)
```
