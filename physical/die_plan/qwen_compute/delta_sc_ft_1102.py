#!/usr/bin/env python3
"""DIE-QC-64/SC 11-02 (QC SC event step 2, OWNER 11-02: reach problems fixed with added pipeline stages, tok/s loss
accepted): ft-slot stations of the nine SC types moved off the new SC hard core.

Step 1 (delta_sc_hard1_1102.py) puts the 244.56 x 514.08 um SC leaf core u_core at (345.6, 648.0) in every SC type.
The SC types are ft-heavy (17 slots, ~9k ft bits per type); with the slot stations still interpolated along the
in->out routes (no declared sites), 5208 station sites per type fell INSIDE the core box (E-W slots at y 648-1162 cross
it), which G0C cannot accept and which made taps.density_taps bisect every in-core site to a singleton (the 19:44 G0C
ran > 2.7 h).  Class fix = the QC actual-bit station tool already used for every other core-bearing QC type:
bit_stations.repair(only_types = the 9 SC types) -> ft_sites strict mode (row-legal exact per-bit cell sites outside
every core + 8.64 um halo, every bit leg an L route in the macro-free channels, hop <= budgets.ft_station_max_um - 2).
Slots whose exact bit hops need it get extra stations (the owner-accepted reach stages); the plan latency table is
regenerated for exactly the lanes whose Plan.lane_latency changed.  lane_eq is NOT run: on main it is not a fixed point
(it adds 6 stations / leaves 30 unequal families on the unmodified plan), so running it would change unrelated types.
Every non-SC type and every top-level key other than latency is asserted unchanged.
usage: delta_sc_ft_1102.py PLAN_IN PLAN_OUT REPORT.json"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import bit_stations  # noqa: E402
import schema as S  # noqa: E402
from gen import latency_table  # noqa: E402

SC = ["slw_sc_v2", "sle_sc_v2", "slw_sc_v1__cl63e5a7a2", "slw_sc_v1__cl64543eaf__cl5e017c6f",
      "slw_sc_v1__cl64543eaf__cl4590432d", "sle_sc_v1__cl115da35f", "sle_sc_v1__cl7479a5ec", "slw_sc_v3", "sle_sc_v3"]


def main():
    pin, pout, prep = sys.argv[1:4]
    text = open(pin).read()
    raw = json.loads(text)
    assert json.dumps(raw) + "\n" == text, "plan text style is not one-line json.dumps"
    orig = json.loads(text)
    for tn in SC:
        assert raw["partition_types"][tn].get("hard_cores"), f"{tn}: run delta_sc_hard1_1102.py first"
    before = S.Plan(json.loads(text))
    old = {lid: before.lane_natural(lid)["cycles"] for lid in before.lanes}
    phys = bit_stations.repair(raw, only_types=SC)
    after = S.Plan(raw)
    tab = latency_table(after)
    lanes = [dict(lane=lid, before=old[lid], after=after.lane_natural(lid)["cycles"]) for lid in after.lanes
             if after.lane_natural(lid)["cycles"] != old[lid]]
    tab0 = latency_table(before)
    cur = raw.get("latency", {}).get("lanes", {})
    drift = sorted(lid for lid in tab0 if cur.get(lid) != tab0[lid])      # pre-existing table drift: reported, untouched
    moved = sorted(lid for lid in tab if tab[lid] != tab0[lid])
    for lid in moved:
        cur[lid] = tab[lid]
    # only the SC types and the latency rows of lanes that changed move
    for tn in raw["partition_types"]:
        if tn not in SC:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    assert {k: v for k, v in raw.items() if k not in ("partition_types", "latency")} == \
        {k: v for k, v in orig.items() if k not in ("partition_types", "latency")}
    fails = [f for f in bit_stations.geometry_failures(raw, check_channels=True) if f["type"] in SC]
    open(pout, "w").write(json.dumps(raw) + "\n")
    rep = dict(event="QC SC event step 2: SC ft stations off the SC hard core (DIE-QC-64/SC 11-02)",
               slots=phys["slots"], added=phys["added"], lane_cycles=lanes, latency_rows_rewritten=moved, latency_rows_predrift=drift,
               sc_geometry_failures_after=fails)
    open(prep, "w").write(json.dumps(rep, indent=1, default=str) + "\n")
    print(f"{len(phys['slots'])} SC slots sited, {len(phys['added'])} got stations, {len(lanes)} lanes +cycles, "
          f"{len(moved)} latency rows rewritten ({len(drift)} pre-existing drift rows untouched), SC geometry failures after: {len(fails)}")
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()
