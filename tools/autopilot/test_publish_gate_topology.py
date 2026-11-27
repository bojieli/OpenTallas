"""publish gate: the per-type topology check blocks an adoption record (C-ISTATION-PACKED-DELAY)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_gate as PG  # noqa: E402

W = "a" * 64


def record(tmp_path, topology):
    checks = {c: {"verdict": "PASS"} for c in PG.CHECKS}
    if topology is not None:
        checks["topology"] = topology
    r = {"schema": PG.SCHEMA_ID, "die": "s81", "tree": "/t", "manifest_hash": W, "plan_sha256": "p", "checks": checks, "verdict": "PASS"}
    p = PG.record_path(tmp_path, "s81", W)
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(r))


def test_require_pass_refuses_a_failed_topology_check(tmp_path):
    record(tmp_path, {"verdict": "FAIL", "types_failed": ["t27", "t36"]})
    assert "topology" in PG.require_pass(tmp_path, "s81", "/t", W, "p")


def test_require_pass_accepts_pass_unknown_and_old_records(tmp_path):
    for i, topo in enumerate((None, {"verdict": "PASS"}, {"verdict": "UNKNOWN"})):
        d = tmp_path / str(i)
        record(d, topo)
        assert PG.require_pass(d, "s81", "/t", W, "p") == ""


def test_topology_check_unknown_without_bind_or_tool_and_runs_tool(tmp_path, monkeypatch):
    assert PG.topology_check("/t", "/p", None, None, str(tmp_path), str(tmp_path))["verdict"] == "UNKNOWN"
    bo = tmp_path / "bind"
    bo.mkdir()
    (bo / "bind_report.json").write_text("{}")
    assert "missing" in PG.topology_check("/t", "/p", None, str(bo), str(tmp_path), str(tmp_path))["why"]
    (tmp_path / "kit_topology_dry.py").write_text("")
    out = tmp_path / "topology_dry.json"

    def fake_sub(argv, cwd, timeout=0):
        out.write_text(json.dumps({"verdict": "FAIL", "n_types": 3, "n_pass": 1, "failed": [{"type": "t27", "stage": "kit_topology", "why": "x"},
                                                                                              {"type": "t36", "stage": "kit_topology", "why": "y"}]}))
        return 1, "FAIL TOPOLOGY-DRY"
    monkeypatch.setattr(PG, "_sub", fake_sub)
    r = PG.topology_check("/t", "/p", "/ab", str(bo), str(tmp_path), str(tmp_path))
    assert r["verdict"] == "FAIL" and r["types_failed"] == ["t27", "t36"] and r["n_failed"] == 2


def test_kit_rtl_stage_failures_alone_are_advisory_topology_stage_failures_block(tmp_path, monkeypatch):
    bo = tmp_path / "bind"
    bo.mkdir()
    (bo / "bind_report.json").write_text("{}")
    (tmp_path / "kit_topology_dry.py").write_text("")
    out = tmp_path / "topology_dry.json"

    def mk(failed):
        def fake_sub(argv, cwd, timeout=0):
            out.write_text(json.dumps({"verdict": "FAIL", "n_types": 5, "failed": failed}))
            return 1, ""
        monkeypatch.setattr(PG, "_sub", fake_sub)
        return PG.topology_check("/t", "/p", None, str(bo), str(tmp_path), str(tmp_path))
    r = mk([{"type": "svc1", "stage": "kit_rtl", "why": "timed out after 3600 s"}])
    assert r["verdict"] == "ADVISORY" and r["kit_rtl_unverified"] == ["svc1"]
    r = mk([{"type": "svc2", "stage": "kit_rtl", "why": "bind: ERROR kit-rtl svc2: core clock clk_c0: expected one bound leaf x, got 0"}])
    assert r["verdict"] == "FAIL" and r["types_failed"] == ["svc2"]
    r = mk([{"type": "svc1", "stage": "kit_rtl", "why": "timed out"}, {"type": "t31", "stage": "kit_topology", "why": "y"}])
    assert r["verdict"] == "FAIL" and r["types_failed"] == ["svc1", "t31"]


def test_topology_check_ships_the_live_baseline_and_reports_held(tmp_path, monkeypatch):
    bo = tmp_path / "bind"
    bo.mkdir()
    (bo / "bind_report.json").write_text("{}")
    (tmp_path / "kit_topology_dry.py").write_text("")
    out = tmp_path / "topology_dry.json"
    seen = []

    def fake_sub(argv, cwd, timeout=0):
        seen.append(argv)
        out.write_text(json.dumps({"verdict": "PASS", "n_types": 5, "failed": [], "held": [{"type": "svc1", "stage": "kit_rtl", "why": "x", "baseline": "same"}]}))
        return 0, ""
    monkeypatch.setattr(PG, "_sub", fake_sub)
    r = PG.topology_check("/t", "/p", None, str(bo), str(tmp_path), str(tmp_path),
                          {"plan": "/live/plan.json", "bind_out": "/live/bind", "asbuilt": "/live/ab.json", "tree": "/live/src"})
    a = seen[0]
    assert a[a.index("--baseline-plan") + 1] == "/live/plan.json" and a[a.index("--baseline-tree") + 1] == "/live/src"
    assert a[a.index("--baseline-asbuilt") + 1] == "/live/ab.json"
    assert r["verdict"] == "PASS" and r["held_preexisting"][0]["type"] == "svc1"
