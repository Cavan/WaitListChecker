from src.checker import has_value_changed


def test_different_values_returns_true():
    assert has_value_changed("new", "old") is True


def test_same_values_returns_false():
    assert has_value_changed("same", "same") is False


def test_first_run_no_old_value():
    # First time running — there's no previous value
    assert has_value_changed("something", None) is True


def test_value_disappeared():
    # The element is gone from the page
    assert has_value_changed(None, "was_here") is True


def test_both_none():
    # No value before, no value now — nothing changed
    assert has_value_changed(None, None) is False