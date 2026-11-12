#!/usr/bin/env python3
"""DIE-S81-87 ready12 stage ctap (JSON-level): early core taps lost in the clean-slate lineage, for the 10 S81 types KW-FIX-43 had pinned to
the old plan c839 (CORE-CTAP-WIDE-1109 / ENG-CTAP-1109).  Same data mutation as delta_core_ctap_wide_1109.apply / delta_eng_ctap_1109.main
(only clock.taps / clock.core_taps), but on parsed JSON because composer intermediates are not in the plan's own text style.
  eng__t1: ENG-CTAP-1109 ENTRIES (3 taps), pin_xy from the core pins files.
  9 dsdv_slice types (c1x_C t1/3/4/5/7/8/9, lepw_mu_C t1, lepw_mus_C t1): CORE-CTAP-WIDE entries re-derived on the event plan (sites follow
  the moved cores); each type's hard_cores hash must equal the derivation plan's, else fail.
usage: ctapw_fold_1112.py IN OUT REPORT --entries ENTRIES.json --repo REPO"""
import copy, hashlib, json, sys
from pathlib import Path
inp, out, rep = sys.argv[1:4]
ent = sys.argv[sys.argv.index("--entries") + 1]; repo = Path(sys.argv[sys.argv.index("--repo") + 1])
s81 = repo / "physical/die_plan/s81"
sys.path[:0] = [str(s81)]
import delta_eng_ctap_1109 as EN
P = json.load(open(inp)); orig = copy.deepcopy(P); PT = P["partition_types"]
report = dict(eng={}, wide={})
# --- eng__t1 (ENG-CTAP-1109)
for tn, ents in EN.ENTRIES.items():
    t = PT[tn]; ck = t["clock"]; taps = ck.setdefault("taps", [])
    assert ck.get("core_taps") in (None, "early"), (tn, ck.get("core_taps"))
    for inst, cpin, tt, ff, basis in ents:
        hc = next(c for c in t["hard_cores"] if c["inst"] == inst)
        name = f"{inst}.{cpin}"
        assert not any(x.get("name") in (name, inst) for x in taps), (tn, name, "already tapped")
        xy = EN.pin_xy(s81, hc, cpin)
        taps.append(dict(name=name, kind="core", xy=xy, insertion_ps=tt, insertion_ff_ps=ff,
                         budget_owner=f"parent_budget {basis}; {EN.EVENT} DIE-S81-85",
                         note=f"CORELAT-SQ-1: early core tap (12.3 v5.0) at the core clock pin; {EN.EVENT} (pair.py --core-taps rule: internal {tt:g} > {EN.TARGET_PS - 40:g} ps)"))
        report["eng"].setdefault(tn, []).append(name)
    ck["core_taps"] = "early"
# --- CORE-CTAP-WIDE
E = json.load(open(ent)); EV = E["event"]
bad = [tn for tn, h in E["hard_cores_sha"].items()
       if hashlib.sha256(json.dumps(PT[tn]["hard_cores"], sort_keys=True).encode()).hexdigest()[:16] != h]
if bad:
    sys.exit(f"hard_cores differ from the derivation plan for {bad}: re-derive the entries")
for tn, e in E["types"].items():
    assert not e["fix"], (tn, "fix entries not expected here")
    ck = PT[tn].setdefault("clock", {})
    assert ck.get("core_taps") == e["core_taps_was"] and ck.get("core_taps") in (None, "early"), (tn, ck.get("core_taps"))
    taps = ck.setdefault("taps", []); names = {t.get("name") for t in taps}
    for a in e["add"]:
        assert a["name"] not in names, (tn, a["name"])
        taps.append(dict(name=a["name"], kind="core", xy=a["xy"], insertion_ps=a["insertion_ps"], insertion_ff_ps=a["insertion_ff_ps"],
                         budget_owner=f"parent_budget {a['basis']} {a['src']}; {EV} DIE-S81-85",
                         note=f"CORELAT-SQ-1: early core tap (12.3 v5.0) at the core clock pin (pair.py core_tap_xy / schema.tap_clear); {EV} "
                              f"(pair.py --core-taps rule: internal {a['insertion_ps']:g} > 210 ps; was grid)"))
        report["wide"].setdefault(tn, []).append(a["name"])
    ck["core_taps"] = "early"
# --- assert nothing else changed
touched = set(report["eng"]) | set(report["wide"])
for k in P:
    if k != "partition_types": assert P[k] == orig[k], k
for tn in PT:
    if tn in touched:
        a, b = PT[tn], orig["partition_types"][tn]
        assert {k for k in set(a) | set(b) if a.get(k) != b.get(k)} == {"clock"}, tn
        assert {k for k in set(a["clock"]) | set(b["clock"]) if a["clock"].get(k) != b["clock"].get(k)} <= {"taps", "core_taps"}, tn
    else:
        assert PT[tn] == orig["partition_types"][tn], tn
json.dump(P, open(out, "w"), indent=1); json.dump(report, open(rep, "w"), indent=1)
print(json.dumps(report))
