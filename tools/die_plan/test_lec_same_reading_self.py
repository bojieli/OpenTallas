"""DIE-KV-67 11-04: lec._same_reading_self gives the answer of mapping k/c to SELF on both sets and comparing."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def mapped(a, b, k, c):
    two = (k, c)
    return frozenset("SELF" if x in two else x for x in a) == frozenset("SELF" if x in two else x for x in b)


def test_matches_mapped_compare():
    rng = random.Random(7)
    names = ["p", "q", "r", "k", "c", "SELF", ("x", 1)]
    for _ in range(20000):
        a = frozenset(rng.sample(names, rng.randint(0, 7)))
        b = frozenset(rng.sample(names, rng.randint(0, 7)))
        assert lec._same_reading_self(a, b, "k", "c") == mapped(a, b, "k", "c"), (a, b)


def test_size_gap_of_two_is_still_equal():
    assert lec._same_reading_self(frozenset({"r", "SELF", "k", "c"}), frozenset({"r", "k"}), "k", "c")
