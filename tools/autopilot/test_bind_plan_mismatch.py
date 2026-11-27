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
