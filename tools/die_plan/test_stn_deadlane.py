"""tests for stn_deadlane.py (STN-DEADLANE): python3 -m pytest tools/die_plan/test_stn_deadlane.py"""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stn_deadlane as SD  # noqa: E402

T = dict(buses=[dict(name="o_a", dir="out"), dict(name="o_b", dir="out"), dict(name="i_c", dir="in")],
         internal_stations=[dict(conn="bus:o_a", regs_um=[[0, 0]]), dict(conn="bus:o_a", regs_um=[[1, 1]]),
                            dict(conn="bus:o_b", regs_um=[[2, 2]]), dict(conn="bus:i_c", regs_um=[[3, 3]])])


def _b(out_bus):
    return SimpleNamespace(parts={"p1": dict(type="t"), "p2": dict(type="t")}, types={"t": T}, out_bus=out_bus)


def test_dead_on_every_part_is_dead_type_and_ops_drop_only_that_bus():
    b = _b({"p1": [dict(oname="o_b", lane="L2")], "p2": [dict(oname="o_b", lane="L3")]})
    rows = SD.collect(b)
    assert {(r["part"], r["bus"], r["state"]) for r in rows} == {("p1", "o_a", "DEAD"), ("p2", "o_a", "DEAD"),
                                                                ("p1", "o_b", "OK"), ("p2", "o_b", "OK")}
    found = SD.classify(rows)
    assert list(found) == [("t", "o_a")] and found[("t", "o_a")]["state"] == "DEAD-TYPE"
    doc = SD.ops_for(dict(partition_types={"t": T}), found)
    assert doc["schema"] == "plan_ops.v1" and len(doc["ops"]) == 1
    op = doc["ops"][0]
    assert op["path"] == "/partition_types/t/internal_stations" and op["old"] == T["internal_stations"]
    assert [s["conn"] for s in op["value"]] == ["bus:o_b", "bus:i_c"]


def test_dead_on_some_parts_is_partial_and_not_dropped():
    b = _b({"p1": [dict(oname="o_a", lane="L1"), dict(oname="o_b", lane="L2")], "p2": [dict(oname="o_b", lane="L3")]})
    found = SD.classify(SD.collect(b))
    assert found[("t", "o_a")]["state"] == "DEAD-PARTIAL" and found[("t", "o_a")]["dead_parts"] == ["p2"]
    assert SD.ops_for(dict(partition_types={"t": T}), found)["ops"] == []


def test_multi_and_clean():
    b = _b({"p1": [dict(oname="o_a", lane="L1"), dict(oname="o_a", lane="L9"), dict(oname="o_b", lane="L2")],
            "p2": [dict(oname="o_a", lane="L4"), dict(oname="o_b", lane="L3")]})
    found = SD.classify(SD.collect(b))
    assert found[("t", "o_a")]["state"] == "MULTI" and found[("t", "o_a")]["multi_parts"] == ["p1"]
    clean = _b({"p1": [dict(oname="o_a"), dict(oname="o_b")], "p2": [dict(oname="o_a"), dict(oname="o_b")]})
    assert SD.classify(SD.collect(clean)) == {}


def test_not_checked_without_elab(tmp_path, capsys):
    assert SD.main([str(tmp_path / "p.json"), "--asbuilt", "x", "--elab", str(tmp_path), "--out", str(tmp_path / "o")]) == 2
    assert "not checked" in capsys.readouterr().out
