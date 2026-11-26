import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fix_landed as fl  # noqa: E402

ENTRY = {"clock": {"taps": [{"name": "clk", "xy": [1.5, 2.5]}, {"name": "clk_t1", "xy": [3.0, 4.0]}],
                   "landing_writer_start": {"branches": {"b": {"stages": [{"xy_um": [7.0, 8.0], "raw_reset": "rst_rl_1"}]}}}},
         "tap_group": {"x": "", "fixed_taps": {"u_a": "clk_t1"}},
         "internal_stations": [{"conn": "bus:fi", "regs_um": [[10.0, 20.0]]}],
         "relay_sites": {"u/q[0]": [5.0, 6.0]}}


def _kit(root, typ, taps, mtime, src=True):
    k = root / "job" / "gen" / typ
    k.mkdir(parents=True)
    (k / "budget.json").write_text(json.dumps({"clock": {"taps": taps}}))
    (k / "clock_taps.tcl").write_text(("source /work/vpw_bank_clock.tcl\n" if src else "# refreshed from main\n") + "# u_a clk_t1 x\n")
    (k / "istations.tcl").write_text("is_place_alt a b c 10.0 20.0 ist:fi\n")
    (k / "relay_mid.tcl").write_text("pt 5.0 6.0 7.0 8.0\n")
    os.utime(k / "clock_taps.tcl", (mtime, mtime))
    return k


def _scope(epoch):
    return [{"scope_id": "S", "die": "S81", "base_sha": "abc", "types": ["t"], "adopted_epoch": epoch}]


def _status(rows):
    return {r["op_class"]: r["status"] for r in rows}


def test_landed(tmp_path):
    good = [{"name": "clk", "xy": [1.5, 2.5]}, {"name": "clk_t1", "xy": [3.0, 4.0]}]
    _kit(tmp_path, "t", good, 2000)
    rows = fl.audit(_scope(1000), {"t": ENTRY}, fl.find_kits([str(tmp_path)]))
    assert set(_status(rows).values()) == {fl.LANDED}, _status(rows)


def test_dropped_source_and_tap_not_landed(tmp_path):
    _kit(tmp_path, "t", [{"name": "clk", "xy": [1.5, 2.5]}], 2000, src=False)
    st = _status(fl.audit(_scope(1000), {"t": ENTRY}, fl.find_kits([str(tmp_path)])))
    assert st["clock_taps_source"] == fl.NOT_LANDED and st["taps"] == fl.NOT_LANDED and st["stations"] == fl.LANDED


def test_kit_older_than_scope_not_yet_built(tmp_path):
    _kit(tmp_path, "t", [], 500)
    rows = fl.audit(_scope(1000), {"t": ENTRY}, fl.find_kits([str(tmp_path)]))
    assert rows and {r["status"] for r in rows} == {fl.NOT_YET}
    assert {r["status"] for r in fl.audit(_scope(1000), {"t": ENTRY}, {})} == {fl.NOT_YET}


def test_stale_base_flag(tmp_path):
    k = _kit(tmp_path, "t", [{"name": "clk", "xy": [1.5, 2.5]}], 2000)
    (k / "budget.json").write_text(json.dumps({"clock": {"taps": []}, "io_hold": {"plan_sha256": "ffff" * 16}}))
    rows = fl.audit(_scope(1000), {"t": ENTRY}, fl.find_kits([str(tmp_path)]))
    assert all(r["stale_base"] == 1 for r in rows)


def test_freeze_thaw_roundtrip_and_merge(tmp_path):
    ex = fl.expected_items(ENTRY)
    assert fl.thaw(json.loads(json.dumps(fl.freeze(ex)))) == ex
    good = [{"name": "clk", "xy": [1.5, 2.5]}, {"name": "clk_t1", "xy": [3.0, 4.0]}]
    _kit(tmp_path, "t", good, 2000)
    rows_a = fl.audit(_scope(1000), {"t": fl.thaw(json.loads(json.dumps(fl.freeze(ex))))}, fl.find_kits([str(tmp_path)]))
    assert {r["status"] for r in rows_a} == {fl.LANDED}
    rows_b = fl.audit(_scope(1000), {"t": ENTRY}, {})
    import csv as _csv
    paths = []
    for i, rows in enumerate((rows_b, rows_a)):
        p = tmp_path / f"h{i}.tsv"
        with open(p, "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=fl.COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        paths.append(str(p))
    assert {r["status"] for r in fl.merge(paths)} == {fl.LANDED}
