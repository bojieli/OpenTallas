"""STRAP-EVIDENCE-PRIV-1124 (HEAD-WEST 86b4806b, COORD): a private HEAD kit names the bind tie audit of its declared bind
(private-spec --bind-out -> kit_wave OT_KIT_BIND_OUT), and gen's count-strap evidence is then strict: VERIFIED or the gen fails."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

H = Path(__file__).resolve().parent
sys.path[:0] = [str(H), str(H.parent / "die_plan")]
import head_wave_kit_rtl as K  # noqa: E402
import count_strap_evidence as CSE  # noqa: E402

TYPE = {"count_straps": [{"name": "strap_k", "width": 2}]}
PARTS = [("u0", {"type": "t", "id_straps": {"strap_k": 1}})]


def plan(tmp):
    p = tmp / "prep" / "source_plan.json"; p.parent.mkdir(parents=True); p.write_text('{"x": 1}')
    return p


def audit(dirp, plan_path, rows=(("u0", "strap_k", "2'd1"),), verdict="PASS"):
    dirp.mkdir(parents=True, exist_ok=True)
    f = dirp / "tie_audit.json"
    f.write_text(json.dumps({"verdict": verdict, "rows": [list(r) for r in rows],
                             "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest()}))
    return f


def test_declared_bind_out_names_the_audit_and_makes_it_strict(tmp_path, monkeypatch):
    p = plan(tmp_path)
    audit(tmp_path / "bind_r18w3c", p)
    out = tmp_path / "kit_rtl"; out.mkdir()
    monkeypatch.delenv("OT_BIND_TIE_AUDIT", raising=False)
    monkeypatch.setenv("OT_KIT_BIND_OUT", str(tmp_path / "bind_r18w3c"))
    r = K.tie_audit_record(p, out)
    assert r["strap_evidence_strict"] is True and Path(r["tie_audit"]) == out / "tie_audit.json"
    assert r["tie_audit_source"] == str(tmp_path / "bind_r18w3c" / "tie_audit.json")
    monkeypatch.setenv("OT_KIT_BIND_OUT", str(tmp_path / "nobind"))          # declared but missing: refused, never a silent NONE
    with pytest.raises(ValueError, match="OT_KIT_BIND_OUT"):
        K.tie_audit_record(p, out)
    monkeypatch.delenv("OT_KIT_BIND_OUT")
    assert K.tie_audit_record(p, out) == {}                                     # nothing declared, no bind_of_record: as before


def kit(tmp_path, strict, with_audit):
    kd = tmp_path / "kit"; rtl = tmp_path / "w" / "rtl"; rtl.mkdir(parents=True)
    kr = {"instances": ["u0"], "bound_only_pins": [{"port": "strap_k", "dir": "input", "width": 2}], "strap_evidence_strict": strict}
    if with_audit:
        kr["tie_audit"] = str(audit(tmp_path / "b", plan(tmp_path)))
    (rtl / "kit_rtl.json").write_text(json.dumps(kr))
    return kd, rtl / "kit_rtl.json"


def test_strict_kit_writes_verified_with_the_audit(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OT_STRAP_EVIDENCE_STRICT", raising=False)
    monkeypatch.delenv("OT_BIND_TIE_AUDIT", raising=False)
    kd, kj = kit(tmp_path, True, True)
    ev = CSE.write_for_kit(kd, TYPE, kj, parts=PARTS)
    assert ev["verification"] == "VERIFIED" and ev["tie_audit"]["verdict"] == "PASS"
    assert "COUNT_STRAP_EVIDENCE_CHECK VERIFIED" in capsys.readouterr().out


def test_strict_kit_without_audit_literal_fails_gen(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_STRAP_EVIDENCE_STRICT", raising=False)
    monkeypatch.delenv("OT_BIND_TIE_AUDIT", raising=False)
    kd, kj = kit(tmp_path, True, False)
    with pytest.raises(ValueError, match="UNVERIFIED"):
        CSE.write_for_kit(kd, TYPE, kj, parts=PARTS)
    kd2, kj2 = kit(tmp_path / "b2", False, False)                               # not declared: report-only, as before
    assert CSE.write_for_kit(kd2, TYPE, kj2, parts=PARTS)["verification"] == "UNVERIFIED"
