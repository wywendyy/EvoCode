"""故意保留空列表 Bug，作为 P0 修复样例。"""


def average(numbers: list[float]) -> float:
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
