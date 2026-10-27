"""One per-layer reach table for every die (PLAN-TOOL5, COORD DIE-PLAN VISUAL REVIEW 10-23 item (c)).

It replaces the per-die `die.reach_um` constants (HBM 750, QC 1000, KV 1200, S81 1500) in the G0C reach check. Every
value is MEASURED, from one source: REACH-M89, results/arch/die_reach_m89_1022.json (owner-approved measurement,
2026-10-22; tools/die_reach_m89). That run timed a self-pair relay hop (launch relay ETM -> repeated wire -> capture
relay ETM, TT, T 833.333 ps, uncertainty 60 + skew 90 ps) on the release relays of all four dies:
S81 dsfd_dvrlyh_276_NS / dsfd_rly_266_SN, HBM hbfd_rly_48_NS / hbfd_rly_624_NS, QC qfd_cst_n, KV qkd_rlys_296.

    layer   reach   basis (calibrated x1.203, the margin of the 0.76 ps/um planning constant)
    M4-M7   452.5   min over the 6 relays of `M45_BUFx8_160_check.reach_um_calibrated` (M4/M5 avg RC, BUFx8 / 160 um);
                    M6/M7 were not swept: their wider pitch has lower R, so the M4/M5 value is a lower bound
    M8     1001.2   min over the 6 relays of `M8.reach_um_calibrated` (BUFx12f, 200-300 um spacing: slew-legal)
    M9     1012.8   min over the 6 relays of `M9.reach_um_calibrated`

One table for all dies: the minimum over all measured relays, so a lane is planned against the worst release relay
class until a die measures a better relay of its own (then add a row with its source, never a literal).

Owner rules that bound it (memory 10-16/10-17/10-22): plan 405 um for LOCAL partition-layer hops (the M4-M7 row is
min(measured, 405)); repeaters every <= 450 um (slew 320 ps); M8/M9 relay hop 1.0-1.5 mm per die.

A hop's layer set: lane.route_layers, else die.layer_budget.ft_route_layers, else the die layers (M8/M9) when
die.layer_budget.die_use has "ft_reserved" (FT pushdown: over-the-top feedthrough wires use M8/M9), else the partition
ft layers M4-M7. Its reach is the MINIMUM over that set (the router may use any of them). G0C ERROR: a hop longer
than budgets.reach_margin (0.9) x that reach.

    python3 tools/die_plan/reach.py table                       # the table
    python3 tools/die_plan/reach.py derive results/arch/die_reach_m89_1022.json   # recompute it from the source
"""
import json
import sys

SOURCE = "results/arch/die_reach_m89_1022.json"
OWNER_LOCAL_PLAN_UM = 405.0          # owner 10-17: plan 405 um local hops (first closure trials)
REP_UM = 450.0                       # owner 10-22/23: repeaters every <= 450 um (600 breaks the 320-ps slew limit)
MARGIN = 0.9                         # COORD 10-23 (c): hop > 90% of the layer reach is a G0C ERROR

# measured (calibrated) one-cycle reach in um, min over the six REACH-M89 relays (see the module docstring)
MEASURED = {"M4": 452.5, "M5": 452.5, "M6": 452.5, "M7": 452.5, "M8": 1001.2, "M9": 1012.8}
BASIS = {
    "M4": "REACH-M89 M45_BUFx8_160_check calibrated, min hbfd_rly_48_NS",
    "M5": "REACH-M89 M45_BUFx8_160_check calibrated, min hbfd_rly_48_NS",
    "M6": "M4/M5 value (not swept; lower bound: wider pitch, lower R)",
    "M7": "M4/M5 value (not swept; lower bound: wider pitch, lower R)",
    "M8": "REACH-M89 M8 best calibrated (BUFx12f 250 um), min hbfd_rly_48_NS",
    "M9": "REACH-M89 M9 best calibrated (BUFx12f 250 um), min hbfd_rly_48_NS",
}
PARTITION_LAYERS = ("M4", "M5", "M6", "M7")


def table():
    """{layer: {reach_um, measured_um, basis}}: partition layers capped at the owner's 405-um local planning hop."""
    out = {}
    for ln, v in MEASURED.items():
        r = min(v, OWNER_LOCAL_PLAN_UM) if ln in PARTITION_LAYERS else v
        out[ln] = dict(reach_um=r, measured_um=v, basis=BASIS[ln] + (" ; owner local plan 405" if r != v else ""))
    return out


TABLE = table()


def layer_reach(ln):
    return TABLE[ln]["reach_um"] if ln in TABLE else None


def hop_layers(P, lane=None):
    """layer set a lane's hops may route on (see the module docstring)."""
    if lane and lane.get("route_layers"):
        return list(lane["route_layers"])
    lb = P.layer_budget
    if lb.get("ft_route_layers"):
        return list(lb["ft_route_layers"])
    if "ft_reserved" in lb.get("die_use", []):
        return [n for n in lb.get("die_layers", ["M8", "M9"])]
    return list(PARTITION_LAYERS)


def hop_reach(P, lane=None):
    """(reach_um, layers): min table reach over the lane's layer set; a lane.reach_um override (half-cycle hops)
    can only lower it."""
    ls = hop_layers(P, lane)
    vals = [layer_reach(n) for n in ls if layer_reach(n) is not None]
    r = min(vals) if vals else min(v["reach_um"] for v in TABLE.values())
    if lane and "reach_um" in lane:
        r = min(r, float(lane["reach_um"]))
    return r, ls


def derive(src):
    """recompute MEASURED from the REACH-M89 json (min over relays, calibrated)."""
    d = json.load(open(src))
    m45, m8, m9 = [], [], []
    for rel in d["per_relay"].values():
        for r in rel:
            m45.append(r["M45_BUFx8_160_check"]["reach_um_calibrated"])
            m8.append(r["M8"]["reach_um_calibrated"])
            m9.append(r["M9"]["reach_um_calibrated"])
    return {"M4": min(m45), "M5": min(m45), "M6": min(m45), "M7": min(m45), "M8": min(m8), "M9": min(m9)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "derive":
        print(json.dumps(derive(sys.argv[2] if len(sys.argv) > 2 else SOURCE), indent=1))
    else:
        print(json.dumps(dict(source=SOURCE, margin=MARGIN, rep_um=REP_UM, table=TABLE), indent=1))
