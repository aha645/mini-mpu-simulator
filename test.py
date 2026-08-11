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
