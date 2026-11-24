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


# KIT-STRAP-EVIDENCE 11-23: a kit_rtl.json without instances/bound_only_pins (HEAD wave) must not give an empty evidence
HEAD_TYPE = dict(count_straps=[dict(name="strap_ca_k_coll_i0", width=6)])
HEAD_PARTS = [("lep0N_w", dict(type="t", id_straps={"strap_ca_k_coll_i0": 12, "strap_rst_ph": 1}))]


def head_kit(tmp_path):
    (tmp_path / "kit_rtl.json").write_text(json.dumps(dict(schema="opentallas.head_wave_kit_rtl.v1", plan_type="t")))
    return tmp_path / "kit_rtl.json"


def test_head_wave_kit_rtl_evidence_from_plan(tmp_path):
    ev = CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=HEAD_PARTS, strict=True)
    assert ev["instances"] == ["lep0N_w"] and ev["parent_ties"] == {"strap_ca_k_coll_i0": {"lep0N_w": "6'd12"}}
    assert PA.accepted_count_strap_bits(json.loads((tmp_path / CSE.FILE).read_text())) == {f"strap_ca_k_coll_i0[{b}]" for b in range(6)}


def test_mutant_missing_plan_tie_fails_at_gen(tmp_path):
    parts = [("lep0N_w", dict(type="t", id_straps={"strap_rst_ph": 1}))]
    with pytest.raises(ValueError, match="empty/short"):
        CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=parts, strict=True)


def test_mutant_no_instances_fails_at_gen(tmp_path):
    with pytest.raises(ValueError, match="empty/short"):
        CSE.write_for_kit(tmp_path, HEAD_TYPE, head_kit(tmp_path), parts=[("x", dict(type="t"))], strict=True)


def test_sited_strap_needs_no_evidence(tmp_path):
    typ = dict(count_straps=[dict(name="strap_ca_k_coll_i0", width=6, sites_um=[[0, 0]] * 6)])
    CSE.write_for_kit(tmp_path, typ, head_kit(tmp_path), parts=[("x", dict(type="t"))], strict=True)


def test_kit_rtl_with_bind_audit_still_wins_and_strict_checks_it(tmp_path):
    kit_rtl = tmp_path / "kit_rtl.json"
    kit_rtl.write_text(json.dumps(KIT_RTL))
    (tmp_path / "bind_sidecars").mkdir()
    (tmp_path / "bind_sidecars" / "bind_tie_audit.json").write_text(json.dumps(TIES))
    ev = CSE.write_for_kit(tmp_path, TYPE, kit_rtl, parts=[("a_b", dict(type="t"))], strict=True)
    assert PA.accepted_count_strap_bits(ev) == BITS
    (tmp_path / "bind_sidecars" / "bind_tie_audit.json").write_text(json.dumps(dict(TIES, verdict="FAIL")))
    with pytest.raises(ValueError, match="empty/short"):
        CSE.write_for_kit(tmp_path, TYPE, kit_rtl, parts=[("a_b", dict(type="t"))], strict=True)
