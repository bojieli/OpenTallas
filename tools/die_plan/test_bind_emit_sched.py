"""EMIT-PAR-MERGE-1123 + EMIT-SCHED-1123 (COORD 11-23 bind speed review)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_emit_par as EP  # noqa: E402
import pytest  # noqa: E402


def test_bound_group_products_appends_merge():
    p = (("k", "bound_group_products"),)
    assert EP.merge_set(["/o/g1"], ["/o/g2"], p) == ["/o/g1", "/o/g2"]
    assert EP.merge_set(["/o/g1"], ["/o/g1", "/o/g3"], p) == ["/o/g1", "/o/g3"]
    with pytest.raises(EP.ParUnsafe):
        EP.merge_set(["/o/g1"], ["/o/g2"], (("k", "other_list"),))          # other lists stay last-writer values


def test_history_orders_the_slowest_type_first(tmp_path):
    h = tmp_path / "walls.json"
    EP.hist_save([{"type": "coll_ftc", "wall_s": 3018.0}, {"type": "slw_a", "wall_s": 130.0}], path=str(h))
    out = tmp_path / "bind" / "rtl"
    out.mkdir(parents=True)
    (out.parent / "bind_emit_par.json").write_text(json.dumps({"per_type": [{"type": "slw_b", "wall_s": 400.0}]}))
    got = EP.hist_load(out, path=str(h))
    assert got == {"coll_ftc": 3018.0, "slw_a": 130.0, "slw_b": 400.0}
    order = [("aa", ["p1"]), ("coll_ftc", ["p2"]), ("slw_b", ["p3"])]
    todo = sorted(order, key=lambda kv: (-got.get(kv[0], 0.0), 0))
    assert [t for t, _ in todo] == ["coll_ftc", "slw_b", "aa"]


def test_scheduler_wiring():
    src = (Path(__file__).resolve().parent / "bind_emit_par.py").read_text()
    assert "_h = hist_load(out)" in src and 'hist_save(rec["per_type"])' in src
