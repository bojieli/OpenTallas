"""DIE-HEAD-21 (COORD 10-28 22:37, TOK-HEAD-LAND-1 ASK2): the external START-tree pins (cland_tstart_in/out on the die
start stages) are DECLARED in landing_network.start_tree and PROVED by landing_contract.check; undeclared unused pins
still fail; any landing-contract error fails the HEAD compose (non-zero exit, status FAIL)."""
import copy
import gzip
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import landing_contract as LC  # noqa: E402

IN, OUT = LC.START_PIN_IN, LC.START_PIN_OUT


def _pin(name, d):
    return dict(name=name, dir=d, kind="ctl", layer="M5", xy_um=[1.0, 1.0], epoch=False)


def _plan(start_tree=None, edges=()):
    """3 partitions: org (origin: START in from a stage), lnc (launch: START out to a stage), cp (type-shared copy of
    lnc's type that launches nothing).  ctl pins o, o2 -> i carry ordinary landing_network edges."""
    T = dict(t_org=dict(outline_um=[10.0, 10.0], clock=dict(landing_contract=dict(pins=[_pin(IN, "in"), _pin("o", "out"), _pin("o2", "out")]))),
             t_lnc=dict(outline_um=[10.0, 10.0], clock=dict(landing_contract=dict(pins=[_pin(OUT, "out"), _pin("i", "in")]))))
    parts = dict(org=dict(type="t_org"), lnc=dict(type="t_lnc"), cp=dict(type="t_lnc"))
    net = dict(edges=[dict(id="e_org_lnc", src=dict(part="org", bus="o"), dst=dict(part="lnc", bus="i"), width=1,
                           epoch=False, kind="ctl", source_registered=True, capture_registered=True, max_hop_um=405),
                      dict(id="e_org_cp", src=dict(part="org", bus="o2"), dst=dict(part="cp", bus="i"), width=1,
                           epoch=False, kind="ctl", source_registered=True, capture_registered=True, max_hop_um=405)]
               + list(edges), root_observer=dict(part="org", module="m", fault_port="f", ready_port="r"))
    if start_tree is not None:
        net["start_tree"] = start_tree
    return types.SimpleNamespace(clock=dict(landing_network=net), types=T, parts=parts, layers={"M5": {}},
                                 to_die=lambda pn, xy: (0.0, 0.0))


SP = dict(die_inputs=[dict(port="start:lnc->st:a", src_part="lnc", net="rs_lnc", stage_region="st:a"),
                      dict(port="start:lnc->st:b", src_part="lnc", net="rs_lnc", stage_region="st:b")],
          die_outputs=[dict(port="start:st:a->org", dst_part="org", net="pst_org", stage_region="st:a")],
          plan_ports=[], ports={"x": {}})
SIDE = dict(count_aligned=dict(start_pins=SP))


def _decl():
    P = _plan()
    return LC.start_declaration(SP, {pn: p["type"] for pn, p in P.parts.items()},
                                {"t_org": {IN: "in", "o": "out", "o2": "out"}, "t_lnc": {OUT: "out", "i": "in"}},
                                {("org", "o"), ("org", "o2"), ("lnc", "i"), ("cp", "i")})


def test_undeclared_start_pins_fail_used_0_times():
    errs = LC.check(_plan())["errors"]
    assert sorted(errs) == sorted(f"{pn}.{n}: infrastructure pin used 0 times (no absent-child ties)"
                                  for pn, n in (("org", IN), ("lnc", OUT), ("cp", OUT)))


def test_declared_start_tree_passes_and_is_proved_against_sidecar():
    d = _decl()
    assert d["uses"] == [dict(part="lnc", pin=OUT, net="rs_lnc"), dict(part="org", pin=IN, net="pst_org")]
    assert d["open"] == [dict(part="cp", pin=OUT)]
    r = LC.check(_plan(d), sidecar=SIDE)
    assert r["errors"] == [] and r["start_tree"] == dict(uses=2, open=1, stage_nets=2)
    assert LC.check(_plan(d))["errors"] == []            # plan-only proof (die check.py) passes too


@pytest.mark.parametrize("mut,frag", [
    (lambda d: d["uses"].pop(), "used 0 times"),                                               # origin input undeclared
    (lambda d: d["open"].append(dict(part="org", pin=IN)), "cannot be open"),                  # START input never open
    (lambda d: d["uses"].__setitem__(1, dict(part="org", pin=IN, net="rs_org")), "not a die start-stage"),
    (lambda d: d["uses"].append(dict(part="org", pin=IN, net="pst_x")), "more than one stage net"),
    (lambda d: d["uses"].append(dict(part="cp", pin=IN, net="pst_cp")), "has no such landing-contract pin"),
    (lambda d: d["uses"].append(dict(part="org", pin="o", net="rs_o")), "only cland_tstart_in"),
    (lambda d: d["open"].append(dict(part="lnc", pin=OUT)), "also declared used"),
    (lambda d: d.__setitem__("form", "anything"), "form"),
    (lambda d: d["uses"].append(dict(part="cp", pin=OUT, net="rs_lnc")), "on 2 partitions"),
])
def test_bad_declaration_fails(mut, frag):
    d = _decl()
    mut(d)
    errs = LC.check(_plan(d))["errors"]
    assert errs and any(frag in e for e in errs), errs


def test_declaration_must_equal_sidecar_start_tree():
    d = _decl()
    d["open"] = []
    d["uses"].append(dict(part="cp", pin=OUT, net="rs_cp"))   # plan-consistent, but cp launches nothing in the sidecar
    assert LC.check(_plan(d))["errors"] == []
    errs = LC.check(_plan(d), sidecar=SIDE)["errors"]
    assert any("not in the sidecar start tree" in e for e in errs) and any("declaration != sidecar" in e for e in errs)
    side = copy.deepcopy(SIDE)
    side["count_aligned"]["start_pins"]["die_outputs"].append(dict(port="p", dst_part="lnc", net="pst_lnc", stage_region="st:a"))
    assert any("not declared" in e for e in LC.check(_plan(_decl()), sidecar=side)["errors"])
    assert any("declares no landing_network.start_tree" in e for e in LC.check(_plan(), sidecar=SIDE)["errors"])


def test_start_pin_on_edge_and_stage_net_fails():
    d = _decl()
    e = dict(id="e_bad", src=dict(part="lnc", bus=OUT), dst=dict(part="org", bus=IN), width=1, epoch=False, kind="ctl",
             source_registered=True, capture_registered=True, max_hop_um=405)
    errs = LC.check(_plan(d, edges=[e]))["errors"]
    assert any("also used by a landing_network edge" in x for x in errs)


def test_default_without_start_tree_unchanged():
    P = _plan()
    for t in P.types.values():
        t["clock"]["landing_contract"]["pins"] = [p for p in t["clock"]["landing_contract"]["pins"] if "tstart" not in p["name"]]
    assert LC.check(P)["errors"] == [] and "start_tree" not in LC.check(P)


HEAD = ROOT / "results" / "die_head_21_1028" / "head_landed_tstart.json.gz"


@pytest.mark.skipif(not HEAD.is_file(), reason="HEAD landed fixture not checked out")
def test_head_landed_plan_zero_errors_and_undeclared_fails():
    """HEAD real landed plan (DIE-HEAD-17 CA strap bind, TOK-HEAD-LAND-1 inputs) composed on this branch: 0 errors with
    the sidecar proof; stripping the declaration brings back the 362 'used 0 times' errors."""
    import schema as S
    d = json.loads(gzip.decompress(HEAD.read_bytes()))
    raw, side = d["plan"], dict(count_aligned=dict(start_pins=d["start_pins"]))
    P = S.Plan(raw, str(ROOT / "physical" / "die_plan" / "s81_head" / "landed_plan.json"))
    r = LC.check(P, sidecar=side)
    assert r["errors"] == [] and r["start_tree"] == dict(uses=346, open=16, stage_nets=346)
    raw["clock"]["landing_network"].pop("start_tree")
    errs = LC.check(S.Plan(raw, str(ROOT / "physical" / "die_plan" / "s81_head" / "landed_plan.json")))["errors"]
    assert len(errs) == 362 and all("used 0 times" in e and ".cland_tstart_" in e for e in errs)


@pytest.mark.parametrize("errs,status,rc", [([], "OK", 0), (["x.y: injected"], "FAIL", 1)])
def test_compose_fails_closed_on_any_error(tmp_path, monkeypatch, errs, status, rc):
    """fallback_land compose: any landing-contract error -> status FAIL + exit 1 (was status OK + exit 0); the heavy
    composer is stubbed (the real HEAD compose is the CHECKED run in the READY)."""
    sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
    import fallback_land as F
    import clock_landing_plan as CLP
    import clock_landings as CL
    import head_source_delta as HSD
    import schema as S
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps(dict(partition_types=dict(t=dict(module="m")), ports=[], partitions=[dict(name="ctl", type="t")])))
    tab = tmp_path / "t.json"
    tab.write_text(json.dumps(dict(granularity="part")))
    raw = dict(partition_types=dict(t=dict(module="m")), ports=[], partitions=[dict(name="ctl", type="t")],
               clock=dict(landing_network=dict(edges=[])))
    side = dict(collector=dict(placement_failures=[], boot_budget=dict(ready_at_glue_max_cycles=1), max_die_hop_um=0))
    monkeypatch.setattr(CL, "requirements", lambda p, t: dict(crossings=0, required_new_scalar_pins=0, split_types=[],
                        added_live_data_storage_flops=0, type_count_before=0, type_count_after=0))
    monkeypatch.setattr(CLP, "compose", lambda *a, **k: (raw, side))
    monkeypatch.setattr(HSD, "rebase_pin_assets", lambda *a: [])
    monkeypatch.setattr(S, "Plan", lambda r, p=None: None)
    monkeypatch.setattr(CL, "network_lane_cycles", lambda r: {})
    monkeypatch.setattr(LC, "check", lambda P, sidecar=None: dict(errors=list(errs), pins=0, edges=0, max_hop_um=0.0))
    a = types.SimpleNamespace(plan=str(plan), table=str(tab), out=str(tmp_path / "o"), observer="ctl",
                              observer_spec=None, monitor="region", band_reserve="padded", band_spread=1.0, band_ring="all")
    assert F.cmd_compose(a) == rc
    rep = json.loads((tmp_path / "o" / "compose_report.json").read_text())["compose"]
    assert rep["status"] == status and rep["landing_contract"]["errors"] == len(errs)
    assert ("injected" in rep.get("error", "")) == bool(errs)
