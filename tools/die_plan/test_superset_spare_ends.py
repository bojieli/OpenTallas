"""UNIFY-TOOLS-0300: schema superset key + per-instance spare_ends (FABLE-SUPERSET-0415 section 10, U5)."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

EX = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())


def plan(superset=True, spare=("aux_i",), bind_pm1=False):
    """tiny plan + type mid gains input aux_i (bound on pm2 from pb) and ft slot fz (bound on neither)"""
    p = copy.deepcopy(EX)
    t = p["partition_types"]["mid"]
    t["buses"].append(dict(name="aux_i", dir="in", width=4, kind="data"))
    p["partition_types"]["sink"]["buses"].append(dict(name="aux_o", dir="out", width=4, kind="data"))
    t["ft_slots"].append(dict(copy.deepcopy(t["ft_slots"][0]), name="fz"))
    if superset:
        t["superset"] = {"class": "mid"}
    p["ports"].append(dict(id="aux", src=dict(part="pb", bus="aux_o"), dst=dict(part="pm2", bus="aux_i"), width=4,
                           kind="data", face="W", layers=["M6", "M4"], window_um=[700.0, 705.0]))
    p["lanes"].append(dict(id="aux", ports=["aux"]))
    if bind_pm1:
        p["ports"].append(dict(id="aux1", src=dict(part="@die", bus="aux1"), dst=dict(part="pm1", bus="aux_i"), width=4,
                               kind="data", face="S", layers=["M5", "M7"], window_um=[1000.0, 1010.0]))
        p["lanes"].append(dict(id="aux1", ports=["aux1"]))
    for x in p["partitions"]:
        if x["name"] == "pm1":
            x["spare_ends"] = list(spare)
        if x["name"] in ("pm1", "pm2"):
            x["spare_ends"] = x.get("spare_ends", []) + ["fz"]
    return p


def errs(p):
    return [e for e in S.validate(p) if "fz" in e or "aux" in e or "spare" in e or "superset" in e]


def test_declared_spares_on_a_superset_type_validate():
    assert errs(plan()) == []


def test_an_undeclared_unbound_end_is_still_an_error():
    e = errs(plan(spare=()))
    assert any("pm1: bus 'aux_i' is unbound" in x for x in e), e


def test_spare_ends_need_the_superset_key():
    e = errs(plan(superset=False))
    assert any("without the superset key" in x for x in e), e


def test_a_bound_end_cannot_be_declared_spare():
    e = errs(plan(bind_pm1=True))
    assert any("spare end 'aux_i' is bound" in x for x in e), e


def test_unknown_spare_end_and_half_slot():
    e = errs(plan(spare=("nope", "fz_i")))
    assert any("'nope' is not a bus" in x for x in e), e
    p = plan(spare=())
    for x in p["partitions"]:
        if x["name"] == "pm2":
            x["spare_ends"] = ["fz_i"]
    e = errs(p)
    assert any("spare at one end only" in x for x in e), e


def test_spare_ends_helper_expands_slots():
    P = S.Plan(plan())
    assert P.spare_ends("pm1") == {"aux_i", "fz_i", "fz_o"}
    assert P.spare_ends("pa") == frozenset()
    assert P.spare_ends(S.DIE_PART) == frozenset()


def test_check_superset_pin_tables():
    import check as C

    class R:
        def __init__(self):
            self.e = []

        def err(self, kind, msg, **k):
            self.e.append(msg)
    P = S.Plan(plan())
    r = R()
    pin = ("M6", "W", 1.0)
    C.superset_pin_tables(P, r, "mid", {"pm1": {("cfg_i", 0): pin}, "pm2": {("cfg_i", 0): pin, ("aux_i", 0): pin}})
    assert r.e == []
    C.superset_pin_tables(P, r, "mid", {"pm1": {("cfg_i", 0): pin}, "pm2": {("cfg_i", 0): ("M6", "W", 2.0)}})
    assert r.e and "one pin table" in r.e[0]
    r = R()
    P2 = S.Plan(plan(spare=()))
    C.superset_pin_tables(P2, r, "mid", {"pm1": {("cfg_i", 0): pin}, "pm2": {("cfg_i", 0): pin, ("aux_i", 0): pin}})
    assert r.e and "spare_ends" in r.e[0]
