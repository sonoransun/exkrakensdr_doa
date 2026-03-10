from utils import is_float, is_int


class TestIsFloat:
    def test_valid_float(self):
        assert is_float("3.14") is True

    def test_valid_integer_as_float(self):
        assert is_float("42") is True

    def test_invalid_string(self):
        assert is_float("abc") is False

    def test_none(self):
        assert is_float(None) is False

    def test_empty_string(self):
        assert is_float("") is False

    def test_within_range(self):
        assert is_float("5.0", minimum=0, maximum=10) is True

    def test_below_minimum(self):
        assert is_float("-1.0", minimum=0, maximum=10) is False

    def test_above_maximum(self):
        assert is_float("11.0", minimum=0, maximum=10) is False

    def test_boundary_minimum(self):
        assert is_float("0.0", minimum=0, maximum=10) is True

    def test_boundary_maximum(self):
        assert is_float("10.0", minimum=0, maximum=10) is True


class TestIsInt:
    def test_valid_int(self):
        assert is_int("42") is True

    def test_invalid_string(self):
        assert is_int("abc") is False

    def test_none(self):
        assert is_int(None) is False

    def test_float_string(self):
        assert is_int("3.14") is False

    def test_within_range(self):
        assert is_int("5", minimum=0, maximum=10) is True

    def test_below_minimum(self):
        assert is_int("-1", minimum=0, maximum=10) is False

    def test_above_maximum(self):
        assert is_int("11", minimum=0, maximum=10) is False

    def test_boundary_minimum(self):
        assert is_int("0", minimum=0, maximum=10) is True

    def test_boundary_maximum(self):
        assert is_int("10", minimum=0, maximum=10) is True

    def test_negative_number(self):
        assert is_int("-5") is True
