#!/usr/bin/env python3
"""DIE-QC-67/HC3 11-04 QC tap class, COORD 01:00: flat density-tap type takes sink_bins_file from its own placed geom.
Same form as delta_reach_hc3_1103.py (DT.KNOBS + measured 10.8-um bins + DT.derive/apply), type list on the command line.
usage: delta_bins_placed_1104.py PLAN_IN PLAN_OUT REPORT.json TYPE..."""
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

BINS = "physical/die_plan/qwen_compute/plan_of_record/sink_bins/{}.json"


def main():
    pin, pout, rep_p, *types = sys.argv[1:]
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    P = copy.deepcopy(P0)
    rep = dict(event="QC tap class: bins from placed geom", types={}, src_sha256=hashlib.sha256(text.encode()).hexdigest())
    for t in types:
        ck = P["partition_types"][t]["clock"]
        assert ck.get("tap_mode") == "density" and not ck.get("sink_bins_file"), (t, ck.get("tap_mode"), ck.get("sink_bins_file"))
        json.dump(P, open(pout, "w"), separators=seps)
        taps0 = S.tap_grid(S.Plan(P, pin), t)
        lc0 = copy.deepcopy(ck["landing_contract"])
        ck.update(DT.KNOBS)
        ck["sink_bins_file"] = BINS.format(t)
        DT.T = t
        if lc0.get("collector_tree") is None:
            assert not lc0.get("collector_local_sources") and not lc0.get("collector_children"), t
            roots = DT.GP.clock_pins(S.Plan(P, pout), t)
            for pn in ck["landing_contract"]["pins"]:
                if pn["kind"] == "clock" and pn["dir"] == "out":
                    pn["source_clock_tap"] = min(roots, key=lambda r: DT.L1((r[1], r[2]), pn["xy_um"]))[0]
        else:
            DT.apply(P, DT.derive(S.Plan(P, pout), P))
        taps1 = S.tap_grid(S.Plan(P, pout), t)
        lc = ck["landing_contract"]
        rep["types"][t] = dict(taps_old=len(taps0), taps_new=len(taps1), collector=lc0.get("collector_tree") is not None,
                               relays_old=len((lc0.get("collector_tree") or {}).get("relays", [])),
                               relays_new=len((lc.get("collector_tree") or {}).get("relays", [])),
                               export_taps_changed=sum(a.get("source_clock_tap") != b.get("source_clock_tap")
                                                       for a, b in zip(lc0["pins"], lc["pins"])))
        print(t, rep["types"][t])
    assert all(json.dumps(P["partition_types"][k], sort_keys=True) == json.dumps(v, sort_keys=True)
               for k, v in P0["partition_types"].items() if k not in types)
    open(pout, "w").write(json.dumps(P, separators=seps) + "\n")
    rep["out_sha256"] = hashlib.sha256(open(pout, "rb").read()).hexdigest()
    json.dump(rep, open(rep_p, "w"), indent=1)


if __name__ == "__main__":
    main()
