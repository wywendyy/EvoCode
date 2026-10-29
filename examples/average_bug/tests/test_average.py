from average import average


def test_empty():
    assert average([]) == 0


def test_regular():
    assert average([2, 4, 6]) == 4


def test_negative():
    assert average([-2, -4]) == -3
