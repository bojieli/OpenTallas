"""pytest: ADV-GEN-PARSE (KV-ALLFIX 11-25): a plan whose types fail the gen-step parse (reg_leaf_split rows, bound R8 count
declarations) is reported per type; a clean plan passes; the check is report-only."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_gen_parse as G  # noqa: E402
import plan_advisory as PA  # noqa: E402

COPY = {"name": "a", "pins": ["u_x.*"], "site_um": [1.0, 2.0]}
LANE = "strap_r8pad_lane_i_hsl_Q_N_fo"


def _plan(rls_ok=True, r8_ok=True):
    good = {"reg_leaf_split": [{"leaf": "u_g", "copies": [COPY]}], "count_straps": [{"name": LANE, "width": 1}]}
    bad_rls = {"reg_leaf_split": [{"leaf": "u_g", "copies": []}], "count_straps": [{"name": LANE, "width": 1}]}
    bad_r8 = {"count_straps": []}               # the lane strap carries no plan width: only a 4..max pad width would be legal
    return {"partition_types": {"ok": good, "bad_rls": bad_rls, "bad_r8": bad_r8},
            "partitions": [{"name": f"i_{k}", "type": k} for k in ("ok", "bad_rls", "bad_r8")]}


def _bind(tmp_path):
    types, inst = {}, {}
    for k in ("ok", "bad_rls", "bad_r8"):
        types[k] = {LANE: {"width": 1, "kind": "r8pad_strap"}}
        inst[f"i_{k}"] = {LANE: {"kind": "r8pad_strap", "width": 1, "value": 0}}
    (tmp_path / "rtl").mkdir()
    (tmp_path / "bind_report.json").write_text("{}")
    (tmp_path / "bind_parent_id_straps.json").write_text(json.dumps({"schema": 1, "types": types, "instances": inst}))
    (tmp_path / "bind_r8pad_strap_audit.json").write_text(json.dumps({"verdict": "PASS", "errors": [], "checked_bits": 8}))
    return str(tmp_path)


def test_both_error_classes_reported(tmp_path):
    out = G.findings(_plan(), None, bind_out=_bind(tmp_path))
    assert any(x.startswith("WARN ADV-GEN-PARSE bad_rls: ValueError reg_leaf_split") and "copy needed" in x for x in out), out
    assert any(x.startswith("WARN ADV-GEN-PARSE bad_r8: ValueError invalid bound R8 count declaration: " + LANE) for x in out), out
    assert not any(" ok:" in x for x in out)
    assert out[-1].startswith("WARN ADV-GEN-PARSE summary 2 of 3 type(s)")


def test_clean_plan_passes(tmp_path):
    p = _plan()
    for k in ("bad_rls", "bad_r8"):
        del p["partition_types"][k]
    p["partitions"] = p["partitions"][:1]
    out = G.findings(p, None, bind_out=_bind(tmp_path))
    assert len(out) == 1 and out[0].startswith("WARN ADV-GEN-PARSE summary 0 of 1 type(s)"), out


def test_no_bind_out_reports_r8_not_checked_but_rls_still_runs():
    out = G.findings(_plan(), None)
    assert any("bad_rls:" in x for x in out) and not any("bad_r8:" in x for x in out)
    assert "R8 declarations not checked" in out[-1]


def test_block_env_makes_fail_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_GEN_PARSE_BLOCK", "1")
    out = G.findings(_plan(), None, bind_out=_bind(tmp_path))
    assert any(x.startswith("FAIL ADV-GEN-PARSE bad_rls:") for x in out)
    assert out[-1].startswith("WARN ADV-GEN-PARSE summary")


def test_never_raises_on_garbage():
    for raw in (None, [], {"partition_types": 5}, {"partition_types": {"T": None}}):
        assert isinstance(G.findings(raw, None), list)


def test_registered_and_forced_warn(tmp_path, monkeypatch):
    assert ("GEN-PARSE", "adv_gen_parse") in PA.CHECKS
    monkeypatch.setenv("OT_GEN_PARSE_BLOCK", "1")
    out = PA.run(_plan(), None, checks=["GEN-PARSE"], jobs=1, bind_out=_bind(tmp_path))
    assert out and all(x.startswith("WARN ") for x in out)
