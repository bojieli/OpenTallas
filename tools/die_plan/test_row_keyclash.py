"""P-ROW-SILENT-OVERWRITE: both shapes seen on 11-27 (key pop, key overwrite) fail the composed gate unless the later row overrides."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_gate as RG  # noqa: E402
import row_keyclash as KC  # noqa: E402

BASE = {"partition_types": {"su_c": {"landing_contract": {"fclk_out": "t1", "other": 1}, "x": 1}, "st_a": {"y": 1}}}


def _put(p, o):
    p.write_text(json.dumps(o))
    return str(p)


def _script(tmp, name, body):
    p = tmp / f"{name}.py"
    p.write_text("import json, sys\nraw = json.load(open(sys.argv[1]))\n" + body + "\njson.dump(raw, open(sys.argv[2], 'w'))\n")
    return RG.parse_spec(f"script:{p}")


def _run(tmp, specs, meta, prior=None):
    _put(tmp / "base.json", BASE)
    (tmp / "w").mkdir(exist_ok=True)
    wr = []
    rc, recs = RG.apply_rows(specs, str(tmp / "base.json"), str(tmp / "out.json"), str(tmp / "w"), str(tmp), {}, writes_out=wr)
    assert rc == 0
    rows = [dict(m, writes=w) for m, w in zip(meta, wr)]
    return KC.check(rows, prior)


def test_key_overwrite_clash(tmp_path):
    a = _script(tmp_path, "suc", "raw['partition_types']['su_c']['landing_contract']['fclk_out'] = 't9'")
    b = _script(tmp_path, "fwd", "raw['partition_types']['su_c']['landing_contract']['fclk_out'] = 't2'")
    cl = _run(tmp_path, [a, b], [dict(group=0, ids=["SU_C"]), dict(group=1, ids=["FWD"])])
    assert [c["path"] for c in cl] == ["partition_types/su_c/landing_contract/fclk_out"]
    assert cl[0]["earlier"] == "SU_C" and cl[0]["later"] == "FWD" and "KEYCLASH" in KC.describe(cl)


def test_key_pop_clash(tmp_path):
    a = _script(tmp_path, "suc", "raw['partition_types']['su_c']['clk_land_clear'] = True")
    b = _script(tmp_path, "sta", "raw['partition_types']['su_c'].pop('clk_land_clear')")
    cl = _run(tmp_path, [a, b], [dict(group=0, ids=["SU_C"]), dict(group=1, ids=["STA"])])
    assert [c["kind"] for c in cl] == ["del"] and cl[0]["path"].endswith("su_c/clk_land_clear")
    # popping the whole subtree that holds the earlier write is the same clash
    c = _script(tmp_path, "pt", "raw['partition_types'].pop('su_c')")
    cl = _run(tmp_path, [a, c], [dict(group=0, ids=["SU_C"]), dict(group=1, ids=["PT"])])
    assert cl and cl[0]["path"] == "partition_types/su_c"


def test_declared_override_and_disjoint_pass(tmp_path):
    a = _script(tmp_path, "suc", "raw['partition_types']['su_c']['clk_land_clear'] = True")
    b = _script(tmp_path, "sta", "raw['partition_types']['su_c'].pop('clk_land_clear')")
    assert _run(tmp_path, [a, b], [dict(group=0, ids=["SU_C"]), dict(group=1, ids=["STA"], overrides=["SU_C"])]) == []
    d = _script(tmp_path, "st", "raw['partition_types']['st_a']['y'] = 2")
    assert _run(tmp_path, [a, d], [dict(group=0, ids=["SU_C"]), dict(group=1, ids=["ST"])]) == []
    # specs of one ledger row set do not clash with each other; layering inside a newly added subtree is not a clash
    e = _script(tmp_path, "add", "raw['partition_types']['n'] = {'k': 1}")
    f = _script(tmp_path, "lay", "raw['partition_types']['n']['k'] = 2")
    assert _run(tmp_path, [e, f], [dict(group=0, ids=["A"]), dict(group=1, ids=["B"])]) == []
    assert _run(tmp_path, [a, a], [dict(group=0, ids=["SU_C"]), dict(group=0, ids=["SU_C"])]) == []


def test_prior_round_writers_clash(tmp_path):
    b = _script(tmp_path, "sta", "raw['partition_types']['su_c'].pop('x')")
    prior = {"partition_types/su_c/x": [["SU_C", "abc12345"]]}
    cl = _run(tmp_path, [b], [dict(group=0, ids=["STA"])], prior)
    assert len(cl) == 1 and cl[0]["earlier"] == "SU_C"
    assert _run(tmp_path, [b], [dict(group=0, ids=["STA"], overrides=["abc12345"])], prior) == []


def test_keyed_list_elements_are_separate_keys():
    old = {"t": [{"name": "a", "v": 1}, {"name": "b", "v": 1}]}
    new = {"t": [{"name": "a", "v": 2}, {"name": "b", "v": 1}]}
    assert list(KC.writes(old, new)) == [("t", "[name=a]", "v")]


def test_row_compose_meta_names_row_ids():
    import row_compose as RC
    r = dict(lane="STA", row_id="sta_clr", _key="0123456789abcdef", rows=[dict(path="/x/clr2.py")])
    assert RC.row_ids(r, r["rows"][0]) == ["sta_clr", "STA", "0123456789abcdef", "01234567", "clr2.py"]
