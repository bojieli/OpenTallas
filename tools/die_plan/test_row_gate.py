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


def test_whole_cow_requires_a_parallel_lease_covering_both_memory_budgets():
    from argparse import Namespace

    a = Namespace(mem=96, bind_mem=128)
    assert RG.whole_cow_lease(a, {"OT_HEAVY_THREADS": "48", "OT_HEAVY_MEM_GB": "512"})
    assert not RG.whole_cow_lease(a, {"OT_HEAVY_THREADS": "1", "OT_HEAVY_MEM_GB": "512"})
    assert not RG.whole_cow_lease(a, {"OT_HEAVY_THREADS": "48", "OT_HEAVY_MEM_GB": "96"})
    assert not RG.whole_cow_lease(a, {})


def test_whole_cow_requires_a_complete_die_latency_receipt():
    receipt = {"scope": "die", "verdict": "PASS", "unobserved": 0, "fail": 0}
    assert RG.whole_latency_complete(0, receipt)
    assert not RG.whole_latency_complete(5, dict(receipt, unobserved=1))
    assert not RG.whole_latency_complete(0, dict(receipt, scope="probe"))
    assert not RG.whole_latency_complete(0, {})


def test_whole_cow_cli_uses_the_existing_overlay_runner_without_a_publish_ledger(tmp_path, monkeypatch):
    import pytest

    seen = {}
    monkeypatch.setenv("OT_HEAVY_THREADS", "48")
    monkeypatch.setenv("OT_HEAVY_MEM_GB", "512")
    monkeypatch.setattr(RG.COW, "mounted", lambda out: False)

    def launch(argv, src, out, ledger):
        seen.update(argv=argv, src=src, out=out, ledger=ledger)
        return 0

    monkeypatch.setattr(RG.COW, "run", launch)
    src, out = tmp_path / "sealed", tmp_path / "attempt"
    argv = ["gate", "--local", "--cow", "--types", "all", "--die", "qwen_compute", "--src", str(src),
            "--base", "p.json", "--asbuilt", "a.json", "--row", "ops:o.json", "--out", str(out)]
    assert RG.main(argv) == 0
    assert seen["argv"][1:] == argv
    assert seen["src"] == src and seen["out"] == out and seen["ledger"] is None
    pins = ["--r8-pin-pre", "pre.json.gz", "--r8-pin-pre-sha256", "a" * 64, "--r8-pin-extra", "0"]
    assert RG.main(argv + pins) == 0
    assert seen["argv"][1:] == argv + pins
    scoped = list(argv)
    scoped[scoped.index("all")] = "a"
    for invalid in (scoped + pins, argv + pins[:-2], argv + pins[:-3] + ["deadbee", "--r8-pin-extra", "0"]):
        with pytest.raises(SystemExit) as exc:
            RG.main(invalid)
        assert exc.value.code == 2
    for option in (["--keep-fork"], ["--ledger", "ledger"], ["--no-r8"], ["--skip-normalize", "retap"]):
        with pytest.raises(SystemExit) as exc:
            RG.main(argv + option)
        assert exc.value.code == 2


def test_whole_cow_requires_exact_sealed_inputs_for_a_deliberate_r8_pin(tmp_path):
    import pytest
    from pin_r8_v2 import PIN_MARK

    src = tmp_path / "sealed"
    src.mkdir()
    (src / "asbuilt.json").write_text(json.dumps({"land_r8": "r8.json"}))
    table = src / "r8.json"
    table.write_text("{}")
    assert RG.whole_cow_r8_pin(src, "asbuilt.json", None, None, None) == {}
    pre = Path("pre.json.gz")
    (src / pre).write_bytes(b"pinned bytes")
    digest = RG.sha(src / pre)
    with pytest.raises(ValueError, match="require a deliberate pin"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", pre, digest, 0)

    table.write_text(json.dumps({"note": f"prefix | DIE-QC-102 {PIN_MARK} extra=0: preserved"}))
    with pytest.raises(ValueError, match="all three|are required"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", None, None, None)
    with pytest.raises(ValueError, match="disagrees with the sealed main"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", pre, digest, 1)
    with pytest.raises(ValueError, match="disagrees with the sealed source file"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", pre, "0" * 64, 0)
    with pytest.raises(ValueError, match="must name a file"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", Path("missing"), digest, 0)
    outside = tmp_path / "outside.json.gz"
    outside.write_bytes((src / pre).read_bytes())
    (src / "escape").symlink_to(outside)
    with pytest.raises(ValueError, match="must name a file inside"):
        RG.whole_cow_r8_pin(src, "asbuilt.json", Path("escape"), digest, 0)
    assert RG.whole_cow_r8_pin(src, "asbuilt.json", pre, digest, 0) == {
        "pin_pre": src / pre, "pin_extra": 0,
    }


def test_normalize_tables_forwards_the_exact_pin_to_r8_refresh(tmp_path, monkeypatch):
    import r8_refresh

    (tmp_path / "asbuilt.json").write_text(json.dumps({"land_r8": "r8.json"}))
    (tmp_path / "r8.json").write_text("{}")
    seen = []

    def refresh(argv):
        seen.append(argv)
        return 0

    monkeypatch.setattr(r8_refresh, "main", refresh)
    pre = tmp_path / "pre.json.gz"
    args = ("plan.json", str(tmp_path), "asbuilt.json", "bus_groups.json")
    assert RG.RN.normalize_tables(*args, pin_pre=pre, pin_extra=0)["rc"] == 0
    assert RG.RN.normalize_tables(*args)["rc"] == 0
    assert seen[0] == seen[1] + ["--pin-pre", str(pre), "--pin-extra", "0"]


def test_bind_paths_survive_the_fork_delete(tmp_path):
    """P-RUNTIME-MANIFEST: bind.f / bind_report.json recorded absolute launch-tree paths; after the fork is deleted they still resolve"""
    import shutil
    src, L, tree, out = (tmp_path / n for n in ("src", "launch", "tree", "out"))
    for r in (src, L):
        (r / "rtl").mkdir(parents=True)
    (src / "rtl/a.sv").write_text("module a; endmodule\n")
    (L / "rtl/a.sv").write_text("module a; endmodule\n")          # identical -> the sealed path
    (src / "rtl/b.sv").write_text("module b; endmodule\n")
    (L / "rtl/b.sv").write_text("module b; // row edit\nendmodule\n")   # changed -> copied
    (out / "bind").mkdir(parents=True)
    paths = [str(L / "rtl/a.sv"), str(L / "rtl/b.sv")]
    (out / "bind/bind.f").write_text("\n".join(paths) + "\n")
    (out / "bind/bind_report.json").write_text(json.dumps(dict(files=paths, extra_lib=[], errors=[])))
    st = RG.relocate_bind_paths(out / "bind", [str(L), str(tree)], src, out / "bind_inputs")
    shutil.rmtree(L)
    assert st["rewritten"] == 2 and st["copied"] == 1 and st["missing"] == 0
    rep = json.loads((out / "bind/bind_report.json").read_text())
    assert [Path(x).is_file() for x in rep["files"]] == [True, True]
    assert rep["files"][0] == str(src / "rtl/a.sv")
    assert "row edit" in Path(rep["files"][1]).read_text()
    assert (out / "bind/bind.f").read_text().split() == rep["files"]
    assert str(L) not in (out / "bind/bind.f").read_text()
