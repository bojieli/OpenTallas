#!/usr/bin/env python3
"""DIE-QC-65/KITS 11-03 'QC reach' plan event, part T (clock taps), ESTIMATE-FIRST delta on plan_qc52.

AUTO-GEOM T row on slw_hc3__clccfc3e6b / __cld86a7ad4 (d90 kit wave attempt_3 3_place): the density tap profile
had no sink_bins_file, so tap_grid fell back to 4 taps for 69.5k die-clock registers (~17k sinks per tap, limit 1500).
Delta = the tt_ctlm form (delta_ttctlm_1101.py, DIE-QC-61): the type's MEASURED placed die-clock sinks
(sink_bins/<type>.json, 10.8-um bins, u_cland_* ring flops excluded) + the standard density knobs; dependent landing
data (collector_tree, local-source taps, collector_children nodes, forwarded-clock source_clock_tap) are re-derived
with the same composer rules (delta_ttctlm_1101.derive/apply).  Estimate on main plan_qc52: 4 -> 119 / 116 taps.
The cw_n3 relay stages (+2 cycles) and rrl reset-hop split of the same event are separate RTL/plan parts (not here).
usage: delta_reach_hc3_1103.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import delta_ttctlm_1101 as DT  # noqa: E402
import schema as S  # noqa: E402

TYPES = ("slw_hc3__clccfc3e6b", "slw_hc3__cld86a7ad4")
BINS = "physical/die_plan/qwen_compute/plan_of_record/sink_bins/{}.json"


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    P = copy.deepcopy(P0)
    rep = dict(event="QC reach / T (hc3 density taps)", types={}, src_sha256=hashlib.sha256(text.encode()).hexdigest())
    for t in TYPES:
        ck = P["partition_types"][t]["clock"]
        if ck.get("sink_bins_file") == BINS.format(t):
            rep["types"][t] = "already applied"
            continue
        assert ck.get("tap_mode") == "density" and not ck.get("sink_bins_file"), (t, ck.get("tap_mode"))
        taps0 = S.tap_grid(S.Plan(P, pin), t)
        lc0 = copy.deepcopy(ck["landing_contract"])
        ck.update(DT.KNOBS)
        ck["sink_bins_file"] = BINS.format(t)
        DT.T = t
        if lc0.get("collector_tree") is None:
            # no collector on this type (registered_monitor false): only the forwarded-clock export taps follow the taps
            assert not lc0.get("collector_local_sources") and not lc0.get("collector_children"), t
            roots = DT.GP.clock_pins(S.Plan(P, pout), t)
            for pn in ck["landing_contract"]["pins"]:
                if pn["kind"] == "clock" and pn["dir"] == "out":
                    pn["source_clock_tap"] = min(roots, key=lambda r: DT.L1((r[1], r[2]), pn["xy_um"]))[0]
        else:
            DT.apply(P, DT.derive(S.Plan(P, pout), P))
        taps1 = S.tap_grid(S.Plan(P, pout), t)
        lc = ck["landing_contract"]
        rep["types"][t] = dict(taps_old=len(taps0), taps_new=len(taps1),
                              collector_tree=dict(old=len((lc0["collector_tree"] or {}).get("relays", [])),
                                                  new=len((lc["collector_tree"] or {}).get("relays", []))),
                              export_taps_changed=sum(a.get("source_clock_tap") != b.get("source_clock_tap")
                                                      for a, b in zip(lc0["pins"], lc["pins"])))
        print(t, "taps", len(taps0), "->", len(taps1))
    other = {k: v for k, v in P.items() if k != "partition_types"}
    assert json.dumps(other, sort_keys=True) == json.dumps({k: v for k, v in P0.items() if k != "partition_types"}, sort_keys=True)
    assert all(json.dumps(P["partition_types"][k], sort_keys=True) == json.dumps(v, sort_keys=True)
               for k, v in P0["partition_types"].items() if k not in TYPES)
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep["dst_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
