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

def generate_cross_pattern(n:int, on=1.0, off=0.0)->list[list[float]]:
    """N×N 십자가(Cross) 패턴을 생성한다: 가운데 행·열만 on, 나머지는 off"""
    grid = create_grid(n, off)
    mid = n // 2
    for i in range(n):
        set_cell(grid, mid, i, on)
        set_cell(grid, i, mid, on)
    return grid

def generate_x_pattern(n:int, on=1.0, off=0.0)->list[list[float]]:
    """N×N X 패턴을 생성한다: 두 대각선만 on, 나머지는 off"""
    grid = create_grid(n, off)
    for i in range(n):
        set_cell(grid, i, i, on)
        set_cell(grid, i, n-1-i, on)
    return grid

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
    grid = create_grid(n)
    for row in range(n):
        line = input().strip()
        splited_vals = line.split()
        if len(splited_vals) != n:
            print(f"입력형식오류: 각 줄에 {n}개의 숫자를 공백으로 구분해 입력하세요.")
            return None
        try:
            for col in range(n):
                set_cell(grid, row, col, float(splited_vals[col]))
        except ValueError:
            print(f"입력형식오류: {splited_vals} -> float으로 변경불가")
            return None
    return grid

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
def avg_mac_time(pattern, filter, repeat, score_fn=mac_score):
    """
    mac 연산을 repeat회 반복 측정하여 평균시간을 ms단위로 반환
    순수 함수호출만 감싼다
    """
    total_ms = 0.0
    for i in range(repeat):
        start_time = time.perf_counter()
        score_fn(pattern,filter)
        end_time = time.perf_counter() # nano second로 나오기 때문에 1000을 곱해 ms로 만듬
        total_ms = total_ms + (end_time-start_time)*1000        
    return total_ms/repeat

def print_grid(grid, label):
    print(f"{label} 메모리에 저장 완료")
    n = len(grid) # 행 이 몇개 인지 알 수 있다
    for row in range(n):
        values = [str(get_cell(grid,row,col)) for col in range(n)]
        print(" ".join(values))

def mode1_run():
    repeat = 10
    print(f"#{'-'*40}")
    print("# [1] 필터 입력")
    print(f"#{'-'*40}")
    choice = input("입력 방식 선택 (1: 직접 입력 3x3, 2: 자동 생성 NxN): ").strip()

    if choice == "2":
        while True:
            raw_n = input("생성할 크기 N 입력(홀수만 가능): ").strip()
            try:
                n = int(raw_n)
            except ValueError:
                print(f"입력형식오류: {raw_n} -> 정수로 변환할 수 없습니다.")
                continue
            if n % 2 == 1:
                break
            print("입력형식오류: N은 홀수여야 정확한 가운데를 잡을 수 있습니다.")
        filter_a = generate_cross_pattern(n)
        filter_b = generate_x_pattern(n)
        print_grid(filter_a, "필터 A(자동 생성 Cross)")
        print_grid(filter_b, "필터 B(자동 생성 X)")

        print(f"#{'-'*40}")
        print("#[2] 패턴 입력")
        print(f"#{'-'*40}")
        pattern = generate_cross_pattern(n)
        print_grid(pattern, "패턴(자동 생성 Cross)")
    else:
        filter_a = make_grid_from_input(3,"필터 A")
        print_grid(filter_a,"필터 A")
        filter_b = make_grid_from_input(3,"필터 B")
        print_grid(filter_b,"필터 B")

        print(f"#{'-'*40}")
        print("#[2] 패턴 입력")
        print(f"#{'-'*40}")
        pattern = make_grid_from_input(3,"패턴")

    print(f"#{'-'*40}")
    print("[3] MAC 결과")
    print(f"#{'-'*40}")
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)
    avg_ms = avg_mac_time(pattern,filter_a, repeat)

    print(f"A점수: {score_a}")
    print(f"B점수: {score_b}")
    print(f"연산 시간(평균/{repeat}회): {avg_ms:.4f} ms")
    diff = abs(score_a - score_b)
    if diff < EPSILON: # 동일한 경우는 당연히 오차보다 더 작을것이다
        msg = "판정불가 (|A-B|<1e-9)"
    else: # 오차값 보다 작거나 같지 않은 경우
        if score_a > score_b:
            msg = "A"
        else:
            msg = "B"
    print(f"판정:{msg}")

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
        raw_expected = size_val.get("expected")
        try:
            new_size_val['expected']=normalize_label(raw_expected)
        except ValueError:
            new_size_val["expected"]=None
        new_size_val["expected_raw"]=raw_expected # 정규화실패시 원래기록되어있는정보 저장
        normalized[key_size]=new_size_val
    return normalized

# size_3, size_5, size_13 순서대로 정렬하기 위한 함수
def size_number(size_key):
    return int(size_key.split("_")[1])

def mean(values:list[float])->float:
    return sum(values)/len(values)

def grid2flat(grid:list[list])->list[float]:
    """
    2차원 배열을 받으면 1차원 배열로 변환하여 리턴한다
    """
    n = len(grid)
    return [ get_cell(grid,row,col) for row in range(n) for col in range(n) ]

def mac_score_flat(pattern_flat:list[float],filter_flat:list[float])->float:
    """
    flat(ten) 1차원으로 펼쳐진 패턴과 필터를 곱하고 더한다
    """
    total = 0.0
    for i in range(len(pattern_flat)):
        total = total + pattern_flat[i]*filter_flat[i]
    return total

def compare_2d_1d_optimization(nor_patterns,nor_filters,repeat=10):
    print(f"{'크기':<8}{'2D 평균(ms)':>13}{'1D 평균(ms)':>13}{'개선비율':>6}")
    seen = set()
    for p_name,p_data in nor_patterns.items():
        size_key = "_".join(p_name.split('_')[:2])
        if size_key in seen:
            continue
        seen.add(size_key)
        input_data = p_data["input"]
        cross_filter = nor_filters[size_key]["Cross"]

        time_2d = avg_mac_time(input_data,cross_filter,repeat,mac_score)

        flat_pattern = grid2flat(input_data)
        flat_filter = grid2flat(cross_filter)
        time_1d = avg_mac_time(flat_pattern,flat_filter,repeat,mac_score_flat)

        improve = (time_2d-time_1d)/time_2d*100
        n = len(input_data)
        shape = f"{n}x{n}"
        print(f"{shape:<10}{time_2d:>15.4f}{time_1d:>15.4f}{improve:>9.1f}%")

def mode2_run():
    data = load()
    print(f"#{'-'*40}")
    print("#[1] 필터 로드")
    print(f"#{'-'*40}")
    nor_filters = normalize_filters(data['filters'])

    for key, val in nor_filters.items():
        filter_names = " ,".join(val.keys())
        print(f"✔︎{key} 필터 로드 완료({filter_names})")

    print(f"#{'-'*40}")
    print("#[2] 패턴 분석(라벨 정규화 적용)")
    print(f"#{'-'*40}")
    nor_patterns = normalize_patterns(data['patterns'])

    total_test=0
    pass_count=0
    fail_count=0
    fail_cases=[]
    #성능분석용 dictionary
    perf_log = {}

    for p_name,p_data in nor_patterns.items():
        input_data = p_data["input"]
        p_expected = p_data['expected']

        # p_name이 "size_3_1"이면 "size_3 추출
        size_key = "_".join(p_name.split("_")[:2])

        # size_3 키가 nor_filters에 없는 경우 -> 필터 자체가 없는경우 (데이터/스키마문제)
        if size_key not in nor_filters:
            fail_count += 1
            total_test += 1
            fail_cases.append(f"- {p_name}: [데이터/스키마] {size_key} 필터를 찾을 수 없음")
            print(f"-- {p_name} --")
            print(f"판정: SKIP|expected: {p_expected}|FAIL(데이터/스키마)")
            continue

        cross_filter = nor_filters[size_key]["Cross"]
        x_filter = nor_filters[size_key]["X"]

        # 패턴과 필터의 크기 불일치 (데이터/스키마문제) - cross/x는 서로 독립된 배열이라 각각 검사해야 한다
        size_mismatch = (
            len(input_data)!=len(cross_filter) or len(input_data[0])!=len(cross_filter[0])
            or len(input_data)!=len(x_filter) or len(input_data[0])!=len(x_filter[0])
        )
        if size_mismatch:
            fail_count += 1
            total_test += 1
            fail_cases.append(f"- {p_name}: [데이터/스키마] 크기 불일치(패턴 {len(input_data)}x{len(input_data[0])})")
            print(f"-- {p_name} --")
            print(f"판정: SKIP|expected: {p_expected}|FAIL(데이터/스키마)")
            continue

        #MAC점수 계산
        s_cross = mac_score(input_data, cross_filter)
        s_x = mac_score(input_data, x_filter)

        # 연산 시간 측정
        avg_ms = avg_mac_time(input_data, cross_filter, 10)

        row = len(input_data)
        col = len(input_data[0])
        if size_key not in perf_log:
            perf_log[size_key]={
                "elapsedtimes":[],
                "op_count":row*col,
                "shape":f"{row}x{col}"
            }

        perf_log[size_key]['elapsedtimes'].append(avg_ms)

        print(f"-- {p_name} --")
        print(f"Cross 점수: {s_cross:.2f}")
        print(f"{'X 점수':<10}: {s_x:.2f}")
        j_msg = judge(s_cross,s_x)

        if p_expected is None:
            # 라벨 정규화 실패(데이터/스키마 문제)
            pass_msg = "FAIL(데이터/스키마)"
            fail_count += 1
            fail_cases.append(f"- {p_name}: [데이터/스키마] expected 레이블 정규화 실패(raw={p_data['expected_raw']})")
        elif j_msg=="UNDECIDED":
            pass_msg="FAIL(동점규칙)"
            fail_count +=1
            fail_cases.append(
                f"- {p_name}: [수치비교] 동점(UNDECIDED) 처리 규칙에 따라 FAIL"
            )
        else:
            if j_msg==p_expected:
                pass_msg="PASS"
                pass_count +=1
            else:
                pass_msg="FAIL(로직)"
                fail_count +=1
                fail_cases.append(
                    f"- {p_name}: [로직] expected={p_expected}, predicted={j_msg}"
                )

        print(f"판정: {j_msg}|expected: {p_expected}|{pass_msg}")

        total_test += 1

    print(f"#{'-'*40}")
    print("# [3] 성능 분석 (평균/10회)")
    print(f"#{'-'*40}")
    print(f"{'크기':<8}{'평균 시간(ms)':>11}{'연산 횟수':>8}")
    print(f"#{'-'*40}")

    for size_key in sorted(perf_log.keys(), key=size_number):
        shape = perf_log[size_key]["shape"]
        avg_time = mean(perf_log[size_key]["elapsedtimes"])
        op_count = perf_log[size_key]["op_count"]
        print(f"{shape:<10}{avg_time:>15.4f}{op_count:>12}")

    print()
    compare_2d_1d_optimization(nor_patterns,nor_filters)
    #---------------------------------------
    # [4] 결과 요약
    #---------------------------------------

    print()
    print("#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total_test}개")
    print(f"통과: {pass_count}개")
    print(f"실패: {fail_count}개")

    print()
    print("실패 케이스:")

    if fail_cases:
        for case in fail_cases:
            print(case)
    else:
        print("- 없음")
        






if __name__ == "__main__":
    print("=== Mini NPU Simulator ===")
    print("[모드 선택]")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    mode_num = int(input("선택: ").strip())
    if mode_num == 1:
        mode1_run()
    elif mode_num == 2:
        mode2_run()        