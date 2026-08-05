EPSILON = 1e-9 # 0.000000001
def create_grid(n:int, fill=float(0.0)):
    """
    nxn 크기의 2차원 리스트를 생성한다. 행마다 새 리스트를 만들어서 참조공유 버그를 피한다
    """
    return [[fill for row in range(n)] for col in range(n)]

def set_cell(grid:list[list[float]],row:int,col:int,value:float):
    grid[row][col]=value

def get_cell(grid:list[list[float]],row:int,col:int)->float:
    return grid[row][col]

def mac_score(pattern:list[list[int]], filter:list[list[int]])->float:
    """
    입력패턴과 필터를 위치별로 곱하고 모두 더한다
    """
    n = len(filter)
    total = 0.0
    for row in range(n):
        for col in range(n):
            total = total + pattern[row][col] * filter[row][col]
    return total

def judge(score_cross:float, score_x:float)->str:
    """
    두 점수를 epsilon 기준으로 비교해 Cross , X , UNDECIDED 를 반환한다
    """
    diff = abs(score_cross - score_x)
    if diff < EPSILON: # 동일한 경우는 당연히 오차보다 더 작을것이다
        return "UNDECIDED"
    return "Cross" if score_cross > score_x else "X"

def normalize_label(raw)->str:
    """
    다양한 표기를 표준 라벨('Cross'또는 'X')로 변환한다.
    - filter키: 'cross' -> 'Cross', 'x' -> 'X'
    - expected값: '+' -> 'Cross', 'x' -> 'X'
    알 수 없는 라벨이면 ValueError를 발생시킴
    """
    key = str(raw).strip().lower()
    if key in ("cross","+"):
        return "Cross"
    if key == "x":
        return "X"

def read_grid_from_console(n:int, label:str)->list:
    """
    n줄을 입력받아 nxn 2차원 리스트로 변환한다
    각 줄은 공백으로 구분된 n개의 숫자여야 한다.
    실패 시 안내 후 처음부터 다시 입력을 받는다
    """
    while True:
        print(f"{label} ({n}줄 입력, 공백 구분)")
        rows = []
        ok = True
        for _ in range(n):
            line = input().strip()
            tokens = line.split()
            if len(tokens) != n:
                print(f"입력형식오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
                ok = False
                break
            try:
                rows.append([float(t) for t in tokens])
            except ValueError:
                print(f"입력형식오류: token을 float으로 변경불가{tokens}")
                ok = False
                break
        if ok:
            return rows

import time
def measure_avg_mac_time(pattern, filter, repeat)
def run_mode_console():
    print("#[1] 필터 입력")
    filter_a = read_grid_from_console(3,"filter_A")
    filter_b = read_grid_from_console(3,"filter_B")
    print("#[2] 패턴 입력")
    pattern = read_grid_from_console(3,"pattern")
    print("[3] MAC 결과")
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)
    avg_ms = measure_mac_time_repeated()
