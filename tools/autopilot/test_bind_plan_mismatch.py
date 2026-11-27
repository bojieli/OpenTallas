"""P-KIT-BIND-PLAN-MISMATCH (S81-GATE-LINT 11-26): run-item refuses a spec whose bind_out was bound from another plan.
python3 -m pytest -q tools/autopilot/test_bind_plan_mismatch.py"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def _tree(tmp_path, bind_prov, base="plan_base.json", spec="plan_p2.json"):
    src = tmp_path / "src"
    (src / "physical").mkdir(parents=True)
    (src / "physical" / "plan_base.json").write_text('{"v": "base"}')
    (src / "physical" / "plan_p2.json").write_text('{"v": "p2"}')
    out = tmp_path / "bind"
    out.mkdir()
    (out / "provenance_bind.json").write_text(json.dumps({"provenance": bind_prov}))
    return {"src": str(src), "plan": "physical/" + spec, "kit_rtl": {"bind_out": str(out)}}


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_bind_of_base_plan_refused_for_p2_spec_by_sha(tmp_path):
    sp = _tree(tmp_path, {})
    base = _sha(Path(sp["src"]) / "physical/plan_base.json")
    (Path(sp["kit_rtl"]["bind_out"]) / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan_sha256": base}}))
    why = KW.bind_plan_refusal(sp)
    assert why and why.startswith("BIND-PLAN-MISMATCH") and base[:12] in why


def test_old_bind_without_sha_refused_by_distinct_plan_file(tmp_path):
    sp = _tree(tmp_path, {"plan": "physical/plan_base.json"})
    assert KW.bind_plan_refusal(sp).startswith("BIND-PLAN-MISMATCH")


def test_matching_or_unknown_is_not_refused(tmp_path):
    sp = _tree(tmp_path, {})
    own = _sha(Path(sp["src"]) / "physical/plan_p2.json")
    (Path(sp["kit_rtl"]["bind_out"]) / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan_sha256": own}}))
    assert KW.bind_plan_refusal(sp) is None
    sp2 = _tree(tmp_path / "x", {"plan": "physical/plan_p2.json"})          # old bind naming the spec's own path: cannot tell
    assert KW.bind_plan_refusal(sp2) is None
    assert KW.bind_plan_refusal({"plan": "p.json", "kit_rtl": {}}) is None


def test_run_item_refuses_before_building(tmp_path, monkeypatch):
    sp = _tree(tmp_path, {"plan": "physical/plan_base.json"})
    sp.update(die="s81", item="col_h9_r0_p2", gen_host="localhost", hub="localhost", work=str(tmp_path / "w"))
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(sp))
    assert KW._run_item(str(spec)) == 1
    res = json.loads((tmp_path / "result.json").read_text())
    assert res["stage"] == "bind_plan" and res["verdict"] == "FAIL" and res["tail"].startswith("BIND-PLAN-MISMATCH")


def test_bind_provenance_records_plan_sha():
    assert '"plan_sha256"' in (Path(__file__).resolve().parents[1] / "die_plan" / "bind.py").read_text() or \
        "plan_sha256=plan_sha" in (Path(__file__).resolve().parents[1] / "die_plan" / "bind.py").read_text()


def _collector_alias_spec(tmp_path, monkeypatch):
    import copy

    tools = Path(KW.__file__).resolve().parents[1] / "die_plan"
    monkeypatch.syspath_prepend(str(tools))
    import kit_topology as topology

    rt = tmp_path / "rt"
    mod = rt / "tools/die_plan/kit_topology.py"
    mod.parent.mkdir(parents=True)
    mod.symlink_to(tools / mod.name)
    rt_sha = "a" * 40
    (tmp_path / "rt.manifest.json").write_text(json.dumps({
        "sha": rt_sha, "files": {"tools/die_plan/kit_topology.py": _sha(mod)},
    }))
    (tmp_path / "landing.json").write_text("{}")
    ab = tmp_path / "asbuilt.json"
    ab.write_text(json.dumps({"base": str(tmp_path), "clock_landing_table": "landing.json"}))
    canonical = {"rect_um": [1, 2, 3, 4], "width": 2, "instance": "u_cland_ag"}
    contract = {"bands": {"ag": canonical}, "collector_local_sources": [
        {"name": "ag", "node": "rst_n_t1", "band": dict(canonical, rect_um=[5, 6, 7, 8])}]}
    old = {"partition_types": {
        "tt": {"clock": {"landing_contract": contract}, "buses": []},
        "neighbour": {"buses": []},
        "unemitted": {"buses": []},
    }, "lanes": [], "ports": []}
    producer = tmp_path / "producer.json"
    producer.write_text(json.dumps(old))
    producer_sha = _sha(producer)
    current = copy.deepcopy(old)
    lc = current["partition_types"]["tt"]["clock"]["landing_contract"]
    lc["collector_local_sources"][0]["band"] = copy.deepcopy(lc["bands"]["ag"])
    plan = tmp_path / "new.json"
    plan.write_text(json.dumps(current))
    out = tmp_path / "bind"
    out.mkdir()
    topology.write_bind_receipt(old, out, ab, plan_path=producer)
    (out / "provenance_bind.json").write_text(json.dumps({"provenance": {
        "step": "bind", "plan": str(producer), "plan_sha256": producer_sha}}))
    (out / "bind_report.json").write_text(json.dumps({
        "plan_sha256": producer_sha, "n_errors": 0, "types": old["partition_types"],
        "probe_only": {"emitted": ["tt", "neighbour"]},
    }))
    sp = {"item": "tt", "private": {"lane": "test"}, "gen_host": "localhost",
          "tools_sha": rt_sha, "tools_rt": str(rt), "plan": str(plan), "src": str(tmp_path),
          "kit_rtl": {"mode": "bind", "bind_out": str(out), "asbuilt": str(ab)}}
    return sp, current, producer


def test_exact_collector_alias_refresh_preserves_private_runner_admission(tmp_path, monkeypatch):
    sp, _, _ = _collector_alias_spec(tmp_path, monkeypatch)
    assert KW.bind_plan_refusal(sp) is None
    assert KW.bind_plan_refusal(dict(sp, item="neighbour")) is None
    assert KW.bind_plan_refusal(dict(sp, item="unemitted")).startswith("BIND-PLAN-MISMATCH")
    assert KW.bind_plan_refusal(dict(sp, private=False)).startswith("BIND-PLAN-MISMATCH")
    assert KW.bind_plan_refusal(dict(sp, tools_sha="b"*40)).startswith("BIND-PLAN-MISMATCH")


def test_collector_alias_does_not_authorize_modified_native_plan(tmp_path, monkeypatch):
    sp, current, producer = _collector_alias_spec(tmp_path, monkeypatch)
    plan = Path(sp["plan"])
    lc = current["partition_types"]["tt"]["clock"]["landing_contract"]
    lc["bands"]["ag"]["rect_um"] = [1, 2, 3, 9]
    lc["collector_local_sources"][0]["band"] = dict(lc["bands"]["ag"])
    plan.write_text(json.dumps(current))
    assert KW.bind_plan_refusal(sp).startswith("BIND-PLAN-MISMATCH")
    lc["bands"]["ag"]["rect_um"] = [1, 2, 3, 4]
    lc["collector_local_sources"][0]["band"] = dict(lc["bands"]["ag"])
    plan.write_text(json.dumps(current))
    producer.write_bytes(producer.read_bytes()+b" ")
    assert KW.bind_plan_refusal(sp).startswith("BIND-PLAN-MISMATCH")


def test_alias_probe_timeout_preserves_known_mismatch(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace

    sp, _, _ = _collector_alias_spec(tmp_path, monkeypatch)
    sp["kit_rtl"]["bind_out"] = str(tmp_path / "remote-bind-only")
    old_sha, new_sha = "a"*64, "b"*64
    calls = []

    def run(argv, **_kwargs):
        calls.append(argv)
        if len(calls) == 2:
            raise subprocess.TimeoutExpired(argv, 120)
        return SimpleNamespace(stdout="KW_BIND_PLAN " + json.dumps({
            "bind_sha": old_sha, "spec_sha": new_sha, "how": "provenance plan_sha256"}))

    assert KW.bind_plan_refusal(sp, run=run).startswith("BIND-PLAN-MISMATCH")
    assert len(calls) == 2
