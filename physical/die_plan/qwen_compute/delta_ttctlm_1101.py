#!/usr/bin/env python3
"""DIE-QC-61 11-01: tt_ctlm density clock taps (plan_qc52 delta; the DIE-QC-50/51 'tt_ctlm taps' item never landed).

Measured failure (GEOM-107 16:16 FAIL PLAN, QC 5346b95c915 kit wave, tt_ctlm 3_place): the R4 400-um grid gives
4 clock taps for 38,056 registers (34,121 die-clock sinks) -> ~9.5k sinks per tap, far above the 1500 tap limit.
Delta = the standard QC density profile used by the stm types (compose_qc51.py, OWNER decision 5 density taps):
clock.tap_mode "density", tap_max_sinks 1200, tap_target_sinks 960, tap_radius_um 200, sink_bins_file = the type's
MEASURED placed die-clock sinks (sink_bins/tt_ctlm.json, 10.8-um bins, landing-band ring flops excluded).
Taps are computed by the main tools (schema.tap_grid -> taps.density_taps).  Dependent landing data are re-derived with
the composer rules of compose_qc51.py (self-tested first: re-derivation on the input plan must reproduce it exactly):
collector_tree = reset_tree.for_type; collector_local_sources[].tap = nearest tap relay to the ring pin (band centre
if > 405 um); collector_children[].node renumbered; forwarded-out clock pins source_clock_tap = nearest clock tap.
Outline, buses, ft slots, bands, hard cores, ports and every other type are unchanged.
usage: delta_ttctlm_1101.py PLAN_IN PLAN_OUT [REPORT.json]"""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S  # noqa: E402
import gen_phys as GP  # noqa: E402
import reset_tree as RT  # noqa: E402

T = "tt_ctlm"
BINS = "physical/die_plan/qwen_compute/plan_of_record/sink_bins/tt_ctlm.json"
KNOBS = dict(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=200.0)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])  # noqa: E731


def derive(P, raw):
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree = json.loads(json.dumps(RT.for_type(P, T)))
    n = RT.consumer_count(tree)
    tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    srcs = []
    for s in lc.get("collector_local_sources", []):
        pt = s["pin_xy_um"]
        tap = min(range(n), key=lambda i: L1(tapxy[i], pt))
        b = s.get("band") or {}
        if b.get("rect_um") and L1(tapxy[tap], pt) > 405:
            x0, y0, x1, y1 = b["rect_um"]
            c = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = min(range(n), key=lambda i: L1(tapxy[i], c))
        srcs.append(tap)
    old_n = RT.consumer_count(lc["collector_tree"])
    kids = [f"rst_n_t{n + int(c['node'].split('rst_n_t')[1]) - old_n}" if c["node"].startswith("rst_n_t") else c["node"]
            for c in lc.get("collector_children", [])]
    roots = GP.clock_pins(P, T)
    exp = {p["name"]: min(roots, key=lambda r: L1((r[1], r[2]), p["xy_um"]))[0]
           for p in lc["pins"] if p["kind"] == "clock" and p["dir"] == "out"}
    return tree, srcs, kids, exp


def apply(raw, d):
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree, srcs, kids, exp = d
    lc["collector_tree"] = tree
    for s, tap in zip(lc.get("collector_local_sources", []), srcs):
        s["tap"] = tap
    for c, k in zip(lc.get("collector_children", []), kids):
        c["node"] = k
    for p in lc["pins"]:
        if p["name"] in exp:
            p["source_clock_tap"] = exp[p["name"]]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    # one-line plan text, default (main) or compact (codex/qc-event-1131 d90) separators; the output keeps the style
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    ck0 = P0["partition_types"][T]["clock"]
    if ck0.get("tap_mode") == "density":
        assert ck0.get("sink_bins_file") == BINS, ck0.get("sink_bins_file")
        open(pout, "w").write(text)
        print("already applied")
        return
    assert "tap_mode" not in ck0 and "tap_pitch_um" not in ck0, ck0.get("tap_mode")
    # self-test: the composer rules re-derived on the INPUT plan.  plan_qc52 (5346/d90) does not reproduce byte-exactly
    # (reset tree max_hop_um 321.8 vs stored 324.0, fclk_out_table_req clk_t1 vs stored clk_t3: the stored data predate
    # current reset_tree / snap rules), so the drift is recorded in the report instead of asserted; every derived field
    # of tt_ctlm is rewritten below from the current tools, which is what gen/bind recompute anyway.
    chk = copy.deepcopy(P0)
    apply(chk, derive(S.Plan(P0, pin), P0))
    lcc, lci = chk["partition_types"][T]["clock"]["landing_contract"], ck0["landing_contract"]
    drift = sorted(k for k in set(lcc) | set(lci) if json.dumps(lcc.get(k), sort_keys=True) != json.dumps(lci.get(k), sort_keys=True))
    assert json.dumps({k: v for k, v in chk.items() if k != "partition_types"}, sort_keys=True) == \
        json.dumps({k: v for k, v in P0.items() if k != "partition_types"}, sort_keys=True)
    taps0 = S.tap_grid(S.Plan(P0, pin), T)
    lc0 = copy.deepcopy(ck0["landing_contract"])
    P = copy.deepcopy(P0)
    ck = P["partition_types"][T]["clock"]
    ck.update(KNOBS)
    ck["sink_bins_file"] = BINS
    apply(P, derive(S.Plan(P, pout), P))
    Pf = S.Plan(P, pout)
    taps1 = S.tap_grid(Pf, T)
    lc = ck["landing_contract"]
    t0, t1 = lc0["collector_tree"], lc["collector_tree"]
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep = dict(type=T, knobs=KNOBS, input_rederivation_drift=drift, sink_bins_file=BINS, taps_old=len(taps0), taps_new=len(taps1),
               tap_xy=[[n, round(x, 3), round(y, 3)] for n, x, y in taps1],
               collector_tree=dict(old=dict(depth=t0.get("depth"), relays=len(t0.get("relays", []))),
                                   new=dict(depth=t1.get("depth"), relays=len(t1.get("relays", [])))),
               local_source_taps=[[a["name"], a["tap"], b["tap"]] for a, b in zip(lc0.get("collector_local_sources", []),
                                                                             lc.get("collector_local_sources", []))],
               export_taps=[[a["name"], a.get("source_clock_tap"), b.get("source_clock_tap")]
                            for a, b in zip(lc0["pins"], lc["pins"]) if a.get("source_clock_tap") != b.get("source_clock_tap")],
               src_sha256=hashlib.sha256(text.encode()).hexdigest(), dst_sha256=hashlib.sha256(out.encode()).hexdigest())
    print(T, "taps", rep["taps_old"], "->", rep["taps_new"], "reset tree", rep["collector_tree"])
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
