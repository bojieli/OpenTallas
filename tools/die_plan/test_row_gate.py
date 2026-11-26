"""ROW-GATE (COMPOSE-FAST 11-25): row specs, the three apply forms, ot-run re-exec and the ROW-READY record."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_gate as RG  # noqa: E402

BASE = {"die": {"name": "x"}, "partitions": [{"name": "p0", "type": "a"}],
        "partition_types": {"a": {"v": 1, "hard_cores": [{"name": "c0", "origin_um": [0, 0]}, {"name": "c1", "origin_um": [5, 5]}]},
                            "b": {"v": 2}}}


def test_parse_spec_forms(tmp_path):
    s = RG.parse_spec("script:/r/ROW.py")
    assert s == dict(kind="script", path="/r/ROW.py", args="{in} {out} {report}")
    assert RG.parse_spec("script:/r/ROW.py::{in} {out} --d=1")["args"] == "{in} {out} --d=1"
    assert RG.parse_spec("ops:/r/o.json")["kind"] == "ops"
    m = RG.parse_spec("merge:/r/b.json:/r/p.json")
    assert (m["base"], m["path"]) == ("/r/b.json", "/r/p.json")
    for bad in ("merge:/only", "nope:x"):
        try:
            RG.parse_spec(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


def test_merge3_keyed_lists_and_conflicts():
    cur = json.loads(json.dumps(BASE))
    cur["partition_types"]["b"]["v"] = 7                       # another row already moved b.v
    row = json.loads(json.dumps(BASE))
    row["partition_types"]["a"]["hard_cores"][1]["origin_um"] = [9, 9]
    row["partition_types"]["b"]["v"] = 3                       # conflicts with 7
    conf, applied = [], []
    out = RG.merge3(cur, BASE, row, "", conf, applied)
    assert out["partition_types"]["a"]["hard_cores"][1]["origin_um"] == [9, 9]
    assert out["partition_types"]["b"]["v"] == 7 and conf == ["/partition_types/b/v"]


def test_apply_ops_old_value_check():
    raw = json.loads(json.dumps(BASE))
    n, conf = RG.apply_ops(raw, [dict(op="replace", path="/partition_types/a/v", old=1, value=4),
                                 dict(op="replace", path="/partition_types/b/v", old=99, value=5),
                                 dict(op="replace", path="/partition_types/a/hard_cores/0/origin_um", old=[0, 0], value=[1, 1])])
    assert n == 2 and conf == ["/partition_types/b/v"] and raw["partition_types"]["a"]["hard_cores"][0]["origin_um"] == [1, 1]


def test_apply_rows_in_order_and_stop_at_conflict(tmp_path):
    (tmp_path / "base.json").write_text(json.dumps(BASE))
    (tmp_path / "row.py").write_text("import json, sys\nr = json.load(open(sys.argv[1]))\nr['partition_types']['a']['v'] = 10\n"
                                     "json.dump(r, open(sys.argv[2], 'w'))\nopen(sys.argv[3], 'w').write('{}')\n")
    (tmp_path / "ops.json").write_text(json.dumps({"ops": [dict(op="replace", path="/partition_types/a/v", old=10, value=11)]}))
    specs = [RG.parse_spec(f"script:{tmp_path / 'row.py'}"), RG.parse_spec(f"ops:{tmp_path / 'ops.json'}")]
    rc, recs = RG.apply_rows(specs, str(tmp_path / "base.json"), str(tmp_path / "out.json"), str(tmp_path), str(tmp_path), None)
    assert rc == 0 and json.loads((tmp_path / "out.json").read_text())["partition_types"]["a"]["v"] == 11
    assert all(r["sha256"] for r in recs) and recs[1]["applied"] == 1
    (tmp_path / "ops2.json").write_text(json.dumps({"ops": [dict(op="replace", path="/partition_types/a/v", old=1, value=2)]}))
    rc, recs = RG.apply_rows(specs + [RG.parse_spec(f"ops:{tmp_path / 'ops2.json'}")], str(tmp_path / "base.json"),
                             str(tmp_path / "out2.json"), str(tmp_path), str(tmp_path), None)
    assert rc == 3 and recs[-1]["conflicts"] == ["/partition_types/a/v"]


def test_touched_bound_types():
    raw = json.loads(json.dumps(BASE))
    raw["partition_types"]["a"]["v"] = 5
    raw["partition_types"]["b"]["v"] = 5                       # b is not instantiated: nothing to bind for it
    assert RG.touched_bound_types(raw, BASE) == ["a"]


def test_main_reexecs_under_ot_run(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.delenv("OT_HEAVY_PRIO", raising=False)
    monkeypatch.delenv("OT_HEAVY_THREADS", raising=False)
    monkeypatch.delenv("OT_ROW_GATE_LOCAL", raising=False)

    class R:
        returncode = 0
    monkeypatch.setattr(RG.subprocess, "run", lambda cmd, **k: seen.setdefault("cmd", cmd) and R())
    assert RG.main(["gate", "--die", "qwen_kvsys", "--src", str(tmp_path), "--base", "p.json", "--asbuilt", "a.json",
                    "--row", "ops:o.json", "--out", str(tmp_path / "o")]) == 0
    c = seen["cmd"]
    assert c[1:5] == ["--die", "--mem", "96", "--dir"] and c[-1] == "--local" and "row_gate.py" in " ".join(c)


def test_gate_missing_input_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "rt_dir", lambda rt=None: str(tmp_path))
    rc = RG.main(["gate", "--die", "x", "--src", str(tmp_path), "--base", "nope.json", "--asbuilt", "a.json", "--row", "ops:o.json",
                  "--out", str(tmp_path / "o"), "--local", "--ledger", str(tmp_path / "led")])
    rec = json.loads((tmp_path / "o" / "ROW-READY.json").read_text())
    assert rc == 1 and rec["verdict"] == "NOT-READY" and "input missing" in rec["why"][0] and rec["schema"] == RG.SCHEMA


def test_r8_only_triggers_the_bind_loop():
    assert RG.r8_only(dict(classes={"R8_STALE": 30, "R8_STALE_TOTAL": 1}))
    assert not RG.r8_only(dict(classes={"R8_STALE": 3, "GAP": 1})) and not RG.r8_only(dict(classes={}))


def test_repriced_rows_audit_the_full_die_top():
    base = {"latency": {"lanes": {"L0": {"cycles": 4}}}}
    repriced = {"latency": {"lanes": {"L0": {"cycles": 5}}}}
    assert RG.row_bind_scope(["kv_sys"], base, base) == ["kv_sys"]
    assert RG.row_bind_scope(["kv_sys"], base, repriced) == []
    assert RG.row_bind_scope([], base, base) == []
