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
    n = len(filter) # 행의 개수
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
    raise ValueError(f"알수없는라벨")

def try_make_grid_from_input(n:int)->list[list[float]]:
    rows=[]
    for _ in range(n):
        line = input().strip()
        splited_vals = line.split()
        if len(splited_vals) != n:
            print(f"입력형식오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
            return None
        try:
            # str -> float 형식으로 변환해서 list[float] 형식으로 만듬, rows에추가
            rows.append([float(t) for t in splited_vals])
        except ValueError:
            print(f"입력형식오류: {splited_vals} -> float으로 변경불가")
            return None
    return rows

def make_grid_from_input(n:int, label:str)->list[list]:
    """
    n줄을 입력받아 nxn 2차원 리스트로 만듬
    각 줄은 공백으로 구분된 n개의 숫자여야 한다.
    실패 시 안내 후 처음부터 다시 입력을 받는다
    """
    while True:
        print(f"{label} ({n}줄 입력, 공백 구분)")
        rows = try_make_grid_from_input(n)
        if rows is not None:
            return rows

import time
def avg_mac_time(pattern, filter, repeat):
    """
    mac 연산을 repeat회 반복 측정하여 평균시간을 ms단위로 반환
    순수 함수호출만 감싼다
    """
    total_ms = 0.0
    for i in range(repeat):
        start_time = time.perf_counter()
        mac_score(pattern,filter)
        end_time = time.perf_counter() # nano second로 나오기 때문에 1000을 곱해 ms로 만듬
        total_ms = total_ms + (end_time-start_time)*1000        
    return total_ms/repeat

def mode1_run():
    print("#[1] 필터 입력")
    filter_a = make_grid_from_input(3,"filter_A")
    filter_b = make_grid_from_input(3,"filter_B")
    print("#[2] 패턴 입력")
    pattern = make_grid_from_input(3,"pattern")
    print("[3] MAC 결과")
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)
    avg_ms = avg_mac_time(pattern,filter_a,10)
    print(f"A점수: {score_a}")
    print(f"B점수: {score_b}")
    print(f"연산시간")

import json
def load(path="data.json"):
    with open(path,"r",encoding="utf-8") as file:
        return json.load(file)

def normalize_filters(data:dict)->dict:
    normalized = {}
    for key, value in data.items():
        normalized[key]={normalize_label(label) : grid for label, grid in value.items()}
    return normalized

def normalize_patterns(data:dict)->dict:
    normalized = {}
    for key_size,size_val in data.items():
        new_size_val = dict(size_val)
        try:
            new_size_val['expected']=normalize_label(size_val.get("expected"))
        except ValueError:
            new_size_val["expected"]=None
        normalized[key_size]=new_size_val
    return normalized


def mode2_run():
    data = load()
    print("#[1] 필터 로드")
    # normalize filter
    nor_filters = normalize_filters(data['filters'])
    nor_patterns = normalize_patterns(data['patterns'])
    
    pass

if __name__ == "__main__":
    mode2_run()