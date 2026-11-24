"""PIN-AUDIT-COUNT-STRAP: an extra pin passes only as a plan count strap, bound-only input and tied at the parent."""
import copy
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_strap_evidence as CSE
import pin_audit as PA

TYPE = dict(count_straps=[dict(name="strap_ca_pad", width=2), dict(name="strap_ca_efall", width=1)])
KIT_RTL = dict(bound_type="t", instances=["a.b", "c"],
               bound_only_pins=[dict(port="strap_ca_pad", dir="input", width=2),
                                dict(port="strap_ca_efall", dir="input", width=1), dict(port="other", dir="input", width=1)])
TIES = dict(verdict="PASS", rows=[["a_b", "strap_ca_pad", "2'b01"], ["c", "strap_ca_pad", "2'b10"],
                                  ["a_b", "strap_ca_efall", "1'b1"], ["c", "strap_ca_efall", "1'b0"],
                                  ["z", "strap_ca_pad", "1'b0"]])
BITS = {"strap_ca_pad[0]", "strap_ca_pad[1]", "strap_ca_efall[0]", "strap_ca_efall"}


def evidence():
    return copy.deepcopy(CSE.build(TYPE, KIT_RTL, TIES))


def run_audit(tmp_path, monkeypatch, names, ev):
    class Term:
        def __init__(self, name):
            self.name = name

        def getName(self):
            return self.name

        def getSigType(self):
            return "SIGNAL"

    class Area:
        def xMax(self):
            return 1000

        def yMax(self):
            return 1000

    class Block:
        def getDefUnits(self):
            return 1000

        def getDieArea(self):
            return Area()

        def getBTerms(self):
            return [Term(n) for n in names]

    chip = types.SimpleNamespace(getBlock=Block)
    db = types.SimpleNamespace(getChip=lambda: chip)
    odb = types.SimpleNamespace(dbDatabase=types.SimpleNamespace(create=lambda: db), read_db=lambda d, p: d)
    monkeypatch.setitem(sys.modules, "odb", odb)
    pins, out = tmp_path / "audit_pins.json", tmp_path / "pin_audit.json"
    pins.write_text("[]")
    if ev is not None:
        (tmp_path / CSE.FILE).write_text(json.dumps(ev))
    monkeypatch.setenv("ODB", "x")
    monkeypatch.setenv("PINS", str(pins))
    monkeypatch.setenv("OUT", str(out))
    rc = PA.main()
    return rc, json.loads(out.read_text())


def test_all_three_facts_accept_every_bit():
    assert PA.accepted_count_strap_bits(evidence()) == BITS


def test_audit_passes_with_only_accepted_straps(tmp_path, monkeypatch):
    rc, res = run_audit(tmp_path, monkeypatch, ["strap_ca_pad[0]", "strap_ca_pad[1]", "strap_ca_efall[0]"], evidence())
    assert (rc, res["verdict"], res["extra_n"], res["count_straps_accepted_n"]) == (0, "PASS", 0, 3)


def test_mutant_extra_pin_not_in_count_straps_fails(tmp_path, monkeypatch):
    rc, res = run_audit(tmp_path, monkeypatch, ["strap_ca_pad[0]", "strap_other[0]"], evidence())
    assert (rc, res["verdict"], res["extra"], res["count_straps_accepted"]) == (1, "FAIL", ["strap_other[0]"], ["strap_ca_pad[0]"])


def test_no_evidence_file_stays_strict(tmp_path, monkeypatch):
    rc, res = run_audit(tmp_path, monkeypatch, ["strap_ca_pad[0]"], None)
    assert (rc, res["verdict"], res["extra_n"]) == (1, "FAIL", 1)


def test_bit_beyond_declared_width_fails(tmp_path, monkeypatch):
    rc, res = run_audit(tmp_path, monkeypatch, ["strap_ca_pad[2]"], evidence())
    assert (rc, res["extra"]) == (1, ["strap_ca_pad[2]"])


def drop_plan(ev):
    ev["plan_count_straps"] = [r for r in ev["plan_count_straps"] if r["name"] != "strap_ca_pad"]


def drop_bound(ev):
    ev["bound_only_pins"] = [r for r in ev["bound_only_pins"] if r["port"] != "strap_ca_pad"]


def bound_output(ev):
    next(r for r in ev["bound_only_pins"] if r["port"] == "strap_ca_pad")["dir"] = "output"


def bound_width(ev):
    next(r for r in ev["bound_only_pins"] if r["port"] == "strap_ca_pad")["width"] = 3


def plan_width(ev):
    next(r for r in ev["plan_count_straps"] if r["name"] == "strap_ca_pad")["width"] = 3


def drop_tie(ev):
    del ev["parent_ties"]["strap_ca_pad"]["c"]


def tie_width(ev):
    ev["parent_ties"]["strap_ca_pad"]["c"] = "1'b0"


def tie_net(ev):
    ev["parent_ties"]["strap_ca_pad"]["c"] = "some_net"


@pytest.mark.parametrize("mutate", [drop_plan, drop_bound, bound_output, bound_width, plan_width, drop_tie, tie_width, tie_net])
def test_each_missing_fact_rejects_that_strap(mutate):
    ev = evidence()
    mutate(ev)
    assert PA.accepted_count_strap_bits(ev) == {"strap_ca_efall[0]", "strap_ca_efall"}


def test_no_instances_accepts_nothing():
    ev = evidence()
    ev["instances"] = []
    assert PA.accepted_count_strap_bits(ev) == set()


def test_failed_tie_audit_gives_no_ties():
    assert CSE.build(TYPE, KIT_RTL, dict(TIES, verdict="FAIL"))["parent_ties"] == {}


def test_type_without_count_straps_writes_no_file(tmp_path):
    assert CSE.write_for_kit(tmp_path, {}, tmp_path / "missing.json") is None
    assert not (tmp_path / CSE.FILE).exists()


def test_missing_tie_audit_writes_no_ties(tmp_path):
    kr = tmp_path / "kit_rtl.json"
    kr.write_text(json.dumps(dict(KIT_RTL, bind_out=str(tmp_path / "no_such_bind"))))
    assert CSE.write_for_kit(tmp_path, TYPE, kr)["parent_ties"] == {}
    assert PA.accepted_count_strap_bits(json.loads((tmp_path / CSE.FILE).read_text())) == set()


# KIT-STRAP-EVIDENCE 11-23: HEAD wave kit_rtl.json has no instances/bound_only_pins; ties come from the bound plan's PASS tie audit
HEAD_TYPE = dict(count_straps=[dict(name="strap_ca_k_coll_i0", width=6)])
HEAD_PARTS = [("lep0N_w", dict(type="t", id_straps={"strap_rst_ph": 1}))]
HEAD_AUDIT = dict(verdict="PASS", rows=2029, accepted=[["lep0N_w.strap_ca_k_coll_i0", "6'b001100"], ["lk.strap_rst_ph", "1'd1"]])
BITS6 = {f"strap_ca_k_coll_i0[{b}]" for b in range(6)}


def head_kit(tmp_path, audit=HEAD_AUDIT):
    (tmp_path / "kit_rtl.json").write_text(json.dumps(dict(schema="opentallas.head_wave_kit_rtl.v1", plan_type="t",
                                                          **({"tie_audit": str(tmp_path / "ta.json")} if audit else {}))))
    if audit:
        (tmp_path / "ta.json").write_text(json.dumps(audit))
    return tmp_path / "kit_rtl.json"


def test_head_wave_evidence_from_bind_tie_audit_with_sha(tmp_path):
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=HEAD_PARTS, strict=True)
    assert ev["verification"] == "VERIFIED" and len(ev["tie_audit"]["sha256"]) == 64
    assert ev["parent_ties"] == {"strap_ca_k_coll_i0": {"lep0N_w": "6'b001100"}}
    assert PA.accepted_count_strap_bits(json.loads((tmp_path / CSE.FILE).read_text())) == BITS6


def test_missing_audit_plan_literals_are_unverified_report_only(tmp_path, capsys):
    parts = [("lep0N_w", dict(type="t", id_straps={"strap_ca_k_coll_i0": 12}))]
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path, None), parts=parts)       # no raise, report-only
    assert ev["verification"] == "UNVERIFIED" and PA.accepted_count_strap_bits(ev) == set()
    assert PA.accepted_count_strap_bits(ev, unverified=True) == BITS6
    assert "COUNT_STRAP_EVIDENCE_WARN" in capsys.readouterr().out


def test_strict_raises_on_unverified(tmp_path):
    with pytest.raises(ValueError, match="UNVERIFIED"):
        CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path, None), parts=HEAD_PARTS, strict=True)


def test_fail_audit_is_not_evidence(tmp_path):
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path, dict(HEAD_AUDIT, verdict="FAIL")), parts=HEAD_PARTS)
    assert PA.accepted_count_strap_bits(ev) == set()


def test_cross_check_counts_mismatch(tmp_path, capsys):
    parts = [("lep0N_w", dict(type="t", id_straps={"strap_ca_k_coll_i0": 13}))]
    CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=parts)
    assert "compared=1 mismatch=1" in capsys.readouterr().out


def test_sited_strap_needs_no_evidence(tmp_path):
    typ = dict(count_straps=[dict(name="strap_ca_k_coll_i0", width=6, sites_um=[[0, 0]] * 6)])
    CSE.write_for_kit(tmp_path, typ, head_kit(tmp_path), parts=HEAD_PARTS, strict=True)


def test_pin_audit_unverified_bits_warn_not_fail(tmp_path, monkeypatch):
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path, None), parts=[("lep0N_w", dict(type="t", id_straps={"strap_ca_k_coll_i0": 12}))])
    rc, res = run_audit(tmp_path, monkeypatch, [f"strap_ca_k_coll_i0[{b}]" for b in range(6)], ev)
    assert (rc, res["extra_n"], res["count_straps_unverified_n"]) == (0, 0, 6)


def test_no_audit_no_plan_literal_listed_unverified_and_pin_audit_warns(tmp_path, monkeypatch, capsys):
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path, None), parts=HEAD_PARTS)      # K strap not in id_straps
    assert ev["verification"] == "UNVERIFIED" and ev["unverified_bits"] == sorted(BITS6)
    assert "NO PASS bind tie audit" in capsys.readouterr().out
    rc, res = run_audit(tmp_path, monkeypatch, sorted(BITS6), ev)
    assert (rc, res["extra_n"], res["count_straps_unverified_n"]) == (0, 0, 6)


def test_no_parts_missing_ties_not_verified_and_strict_raises(tmp_path):
    kr = tmp_path / "kit_rtl.json"
    kr.write_text(json.dumps(KIT_RTL))
    ev = CSE.write_for_kit(tmp_path, TYPE, kr, strict=False)
    assert ev["verification"] == "UNVERIFIED"
    with pytest.raises(ValueError, match="UNVERIFIED"):
        CSE.write_for_kit(tmp_path, TYPE, kr, strict=True)


def test_mismatch_raises_only_in_strict(tmp_path, monkeypatch):
    parts = [("lep0N_w", dict(type="t", id_straps={"strap_ca_k_coll_i0": 13}))]
    assert CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=parts)["verification"] == "VERIFIED"
    monkeypatch.setenv("OT_STRAP_EVIDENCE_STRICT", "1")
    with pytest.raises(ValueError, match="differ"):
        CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=parts)


def test_bind_plan_sha_recorded_and_warned(tmp_path, capsys):
    (tmp_path / "bplan.json").write_text("{}")
    (tmp_path / "kplan.json").write_text("{\"x\": 1}")
    (tmp_path / "pre.json").write_text(json.dumps(dict(plan=str(tmp_path / "bplan.json"))))
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=HEAD_PARTS, plan_path=tmp_path / "kplan.json")
    ta = ev["tie_audit"]
    assert ta["bind_plan_sha256"] and ta["kit_plan_sha256"] and ta["bind_plan_sha256"] != ta["kit_plan_sha256"]
    assert "differs from the kit plan sha" in capsys.readouterr().out
