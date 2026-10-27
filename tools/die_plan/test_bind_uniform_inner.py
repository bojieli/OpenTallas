from types import SimpleNamespace
from bind import Binder


def vehicle(enabled=True):
    b = object.__new__(Binder)
    b.ab = {"inner_uniform": ["T"]} if enabled else {}
    b.types = {"T": {}}
    b.parts = {"a": {"type": "T"}, "b": {"type": "T"}}
    b.members = {"a": [0, 1], "b": [2, 3]}
    b.cpart = {0: "a", 1: "a", 2: "b", 3: "b"}
    b.F = SimpleNamespace(cells=[SimpleNamespace(ports={"x": [0]}) for _ in range(4)])
    b.G = SimpleNamespace(dirs={i: {"x": "input" if i in (1, 3) else "output"} for i in range(4)})
    b.rel_of = lambda ci: "src" if ci % 2 == 0 else "sink"
    b.sinks = {(1, "x", 0): ("int", 0, "q", 0, 1), (3, "x", 0): ("int", 2, "q", 0, 3)}
    b.intra_dly = {"a": {(0, "q", 1)}, "b": {(2, "q", 3)}}
    return b


def test_uniform_inner_retains_longest_path_and_reports_every_added_cycle():
    b = vehicle()
    b.uniform_inner()
    assert b.sinks[(1, "x", 0)] == ("int", 0, "q", 0, 3)
    assert b.sinks[(3, "x", 0)] == ("int", 2, "q", 0, 3)
    assert b._inner_original[(1, "x", 0)] == ("int", 0, "q", 0, 1)
    assert b.inner_uniform_stats["added_stage_bits"] == 2
    assert b.inner_uniform_stats["max_added"] == 2
    assert b.intra_dly["a"] == {(0, "q", 3)}


def test_uniform_inner_default_preserves_original_shape():
    b = vehicle(False)
    before = dict(b.sinks)
    b.uniform_inner()
    assert b.sinks == before
    assert not hasattr(b, "_inner_original")
