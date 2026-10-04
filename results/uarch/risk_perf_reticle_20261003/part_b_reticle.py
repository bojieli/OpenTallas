#!/usr/bin/env python3
"""Part B: Qwen3-8B ROM r2 die area vs corridor routable ratio, and corridor-demand fallbacks (model only).

Uses the corridor gate's own die_statement (tools/qwen_corridor_gate.py, which re-runs the r2 floorplan
build_frame unchanged) from a git-archive of origin/claude/qwen-corridor-gate-20261003 (19a660e14), so the
outline arithmetic is the floorplan owner's, not a re-implementation.

  git -C /home/ubuntu/OpenTallas archive origin/claude/qwen-corridor-gate-20261003 | tar -x -C TREE
  python3 part_b_reticle.py --tree TREE > part_b_reticle.json

A fallback that lowers the tile-column demand from 637 to D bits at a gate-measured density d is
evaluated as the r2 frame at effective density d * 637 / D (same tracks per micron, same pitch).
"""
import argparse, contextlib, io, json, sys

TC_BITS = dict(clock=64, reset=64, instruction=379, go=1, x=128, ready=1)   # qwen_rom_floorplan_nearhbm.py:91
TC_DEMAND = sum(TC_BITS.values())                                            # 637
TRK_M7_M9 = 1 / 0.064 + 1 / 0.080                                            # 28.125 tracks/um (r2.py:68)
TRK_M5 = 1 / 0.048                                                           # ASAP7 M5 pitch 48 nm

# Each fallback: demand per tile column (bits), track multiplier, latency (cycles per token, low/high),
# re-qualification list.  Latency is priced against the Part A central token (207,010 cycles at 1.2 GHz).
ME_OPS_PER_TOKEN = 36 * 8 + 8   # <= 8 serial ME ops a layer + 8 head chunks (upper count; 4 matvecs a layer measured)
FALLBACKS = [
    dict(id="F1", name="pipelined reset tree: 1 reset wire + per-tile synchroniser (reset is off the token path)",
         demand=TC_DEMAND - 63, track_mult=1.0, latency_cycles=[0, 0],
         requal=["reset/drain bench of one column (assert/deassert order, ICG)", "column STA"],
         routability="removes 63 of 637 static nets; no timing-critical wire added"),
    dict(id="F2", name="instruction 2:1 time-multiplexed into a 2-deep per-column instruction FIFO (static decode schedule)",
         demand=TC_DEMAND - 189, track_mult=1.0, latency_cycles=[0, ME_OPS_PER_TOKEN],
         requal=["default-off emitter/spine parameter; exact gate: identical instruction stream, outputs cycle-shifted <= 1/op",
                 "layer A/B in the layer-parallel runtime (3,930-cycle reference)", "corridor gate re-run at 448 bits"],
         routability="-30% tile-column tracks; 2 beats/op is far below the op issue interval, so a 2-deep FIFO hides it"),
    dict(id="F3", name="column-pair shared corridor: mirror tile slots, one corridor feeds two columns; instruction/clock/reset carried once per pair (r2's own least-cost note)",
         demand=(64 + 64 + 379) / 2 + 128 + 2, track_mult=1.0, latency_cycles=[0, 0],
         requal=["mirrored tile abstract + pin rows on both corridor faces (the one-sided B series overflowed at 0.43 in the tap fan-out zone: re-gate the two-sided tap)",
                 "column-pair clock/ICG plan", "corridor gate re-run (pair corridor, 32 corridors)"],
         routability="-40% tracks per column, but tap fan-out density doubles at the corridor faces; that is exactly where B failed"),
    dict(id="F4", name="add M5 (vertical, 48 nm) to the tile-column corridor; latency-tolerant nets (reset, FIFO-decoupled instruction) take it. Multiplier is an UPPER BOUND (all M5 tracks usable)",
         demand=TC_DEMAND, track_mult=(TRK_M7_M9 + TRK_M5) / TRK_M7_M9, latency_cycles=[0, 0],
         requal=["corridor gate with M5 in the assignment (repeater/station pin access on M5)", "ROM macro OBS check at corridor edges"],
         routability="+74% raw tracks if M5 is fully usable; only latency-tolerant nets go there because M5 RC shortens the stage reach; alone (without F2) x/go/ready must stay on M7/M9, so F4 is only credible together with F2"),
    dict(id="F1+F2", name="F1 + F2 (RECOMMENDED immediate fallback)",
         demand=TC_DEMAND - 63 - 189, track_mult=1.0, latency_cycles=[0, ME_OPS_PER_TOKEN],
         requal=["F1 and F2 lists; both are single-column, default-off, class-A (no arithmetic change)"],
         routability="-40% tile-column tracks (637 -> 385) with no change to tile abstracts, slot geometry or the hub"),
    dict(id="F1+F2+F4", name="F1 + F2 + M5 for static nets", demand=TC_DEMAND - 63 - 189, track_mult=(TRK_M7_M9 + TRK_M5) / TRK_M7_M9,
         latency_cycles=[0, ME_OPS_PER_TOKEN], requal=["F1+F2 and F4"], routability="reserve"),
]
OTHER_FALLBACKS = [
    dict(id="F5", name="narrow/serialised horizontal links and spine (128-bit links)",
         effect="r2 record: 888.14 mm2 at the pass density, +10.1 us/token; the links and spine are not the area driver (links+spine at 0.225 with r2 tile column = 800.5 mm2)",
         verdict="REJECT as a reticle lever"),
    dict(id="F6", name="hub relocation / reduction-broadcast trees on M8/M9",
         effect="moves the 45-stage hub path, not the 64 x tile-column corridors that hold ~105 mm2; the tile column already uses M7/M9",
         verdict="REJECT as a reticle lever (keep for wire-stage timing)"),
    dict(id="F7", name="split across more reticles: TP-8 (4 packages x 2 dies, G = 3,072 per die)",
         effect="die ~480 mm2 at any density; +1 board hop per all-reduce (~+170 cycles x 72 = +12.2k cycles, +10.2 us); with 2 stacks/die (same 16 stacks) attention unchanged -> ~5,470 tok/s; with 4 stacks/die attention halves -> faster but 32 stacks",
         verdict="LAST RESORT: still meets 3,000 but doubles dies/packages, regenerates every TP image, all-reduce and floorplan; AGENTS 'more dies only after pricing' satisfied by this pricing"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.tree + '/tools'); sys.path.insert(0, a.tree + '/src')
    import os
    os.chdir(a.tree)
    import qwen_corridor_gate as G

    def die(r):
        with contextlib.redirect_stdout(io.StringIO()):
            return G.die_statement(r)

    def uni(x):
        return {"tile_column": x, "horizontal_link": x, "vertical_spine": x}

    rows = []
    for i in range(20, 46):
        x = i / 100
        u, t = die(uni(x)), die({"tile_column": x})
        rows.append(dict(d=x, uniform_mm2=u['gated_die_mm2'], uniform_die_um=u['die_um'], uniform_fits_26x33=u['fits_26x33'],
                         tile_only_mm2=t['gated_die_mm2'], tile_only_die_um=t['die_um'], tile_only_fits_26x33=t['fits_26x33']))

    def solve(limit, key, which):
        lo, hi = 0.15, 0.45
        for _ in range(40):
            m = (lo + hi) / 2
            d = die({"tile_column": m} if which == 'tile' else uni(m))
            v = d['gated_die_mm2'] if key == 'area' else d['die_um'][0]
            lo, hi = (lo, m) if v <= limit else (m, hi)
        return round(hi, 4)

    thr = dict(uniform=dict(width_26mm=solve(26000, 'w', 'u'), area_858=solve(858, 'area', 'u'), area_815=solve(815, 'area', 'u')),
               tile_column_only=dict(width_26mm=solve(26000, 'w', 'tile'), area_858=solve(858, 'area', 'tile'),
                                     area_815=solve(815, 'area', 'tile')))

    def solve_fb(mult, limit, key):
        lo, hi = 0.05, 0.45
        for _ in range(40):
            m = (lo + hi) / 2
            d = die({"tile_column": min(m * mult, 0.95), "horizontal_link": m, "vertical_spine": m})
            v = d['gated_die_mm2'] if key == 'area' else d['die_um'][0]
            lo, hi = (lo, m) if v <= limit else (m, hi)
        return round(hi, 4)

    gate_points = [0.20, 0.225, 0.25, 0.30, 0.33, 0.36]
    fb = []
    for f in FALLBACKS:
        mult = TC_DEMAND / f['demand'] * f['track_mult']
        pts = {}
        for g in gate_points:
            eff = g * mult
            d = die({"tile_column": min(eff, 0.95), "horizontal_link": g, "vertical_spine": g})
            pts[str(g)] = dict(effective_tile_density=round(eff, 3), die_mm2=d['gated_die_mm2'], die_um=d['die_um'],
                               fits_26x33=d['fits_26x33'], within_815=d['within_815'])
        lat = [c / 1.2e9 * 1e6 for c in f['latency_cycles']]
        fb.append(dict(f, demand=round(f['demand'], 1), density_multiplier=round(mult, 3),
                       gate_density_needed_for_815=solve_fb(mult, 815, 'area'),
                       gate_density_needed_for_outline=solve_fb(mult, 26000, 'w'),
                       latency_us_per_token=[round(x, 3) for x in lat],
                       rate_change_pct_vs_central=[round(-100 * c / (207010 + c), 3) for c in f['latency_cycles']],
                       die_at_gate_density=pts))
    print(json.dumps(dict(
        schema="opentallas.qwen-rom-reticle-fallback.v1", status="MODEL_ONLY_FALLBACK_PREPARATION",
        basis=dict(r2_record="origin/claude/qwen-rom-floorplan-nearhbm-20261003 @ ced04cd96 results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json",
                   gate_tool="origin/claude/qwen-corridor-gate-20261003 @ 19a660e14 tools/qwen_corridor_gate.py die_statement",
                   r2_die_mm2=792.0, legal_outline_um=[26000, 33000], legal_field_mm2=858, hc1_budget_mm2=815,
                   tile_column_bits=TC_BITS, tile_column_demand=TC_DEMAND, corridors=64,
                   tracks_per_um_M7_M9=TRK_M7_M9, note="the binding limit below ~0.28 is the 26 mm WIDTH, not 858 mm2: 64 corridors add width only"),
        sweep=rows, thresholds=thr,
        gate_status_20261003=dict(
            source="ot-agidock128:/home/ubuntu/otjobs/qcg_records/*.json, ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-corridor-gate/STATUS.md (uncommitted, summary not yet run)",
            tile_column_centred_pins_C={"0.43 (r2)": "ROUTED_CLEAN, SS setup -31.4 ps, FF hold met", "0.50/0.60": "placement failed (8.64 um station slab); D series (17.28 um slab) running"},
            tile_column_one_sided_B={"0.43": "GRT overflow 24 (tap fan-out)", "0.362": "GRT overflow 333,803 (flagged anomalous; rerun queued)", "0.30": "ROUTED_CLEAN, SS -10.8 ps"},
            link_span_A={"0.388 (r2)": "ROUTED_CLEAN, SS -42.6/-52.0 ps", "0.50": "ROUTED_CLEAN, SS -57.6 ps", "0.60": "GRT overflow 3,984"},
            strip_fan={"0.388": "ROUTED_CLEAN, SS -41.3 ps", "0.362": "ROUTED_CLEAN, SS -36.9 ps"},
            reading="routability currently supports r2 densities (C at 0.43, A at 0.50) -> 792 mm2 holds; the 0.225 premise (GRT-only, M4/M6/M8 basis) is superseded. Every span misses SS setup by 11-58 ps at 504 um/stage: a wire-stage (latency) risk, not an area risk."),
        fallbacks=fb, other_fallbacks=OTHER_FALLBACKS,
        recommendation=dict(
            adopt_if_gate_below_0p36_exact_thresholds={f['id']: dict(fit_815=f['gate_density_needed_for_815'], fit_outline=f['gate_density_needed_for_outline']) for f in fb},
            adopt_if_gate_below_0p36="F1+F2: pipelined single-wire reset tree + 2:1 time-multiplexed instruction bus into a 2-deep per-column FIFO. Demand 637 -> 385 bits (x1.655). Fits 815 at a gate density >= %.3f and the 26 mm outline at >= %.3f (links/spine held at the same gate density); cost 0 to %d cycles/token (<= 0.14%%, 0 when the FIFO prefetches). No tile abstract, slot, hub or arithmetic change; class A; default-off parameter." % (
                [f for f in fb if f['id'] == 'F1+F2'][0]['gate_density_needed_for_815'], [f for f in fb if f['id'] == 'F1+F2'][0]['gate_density_needed_for_outline'], ME_OPS_PER_TOKEN),
            if_gate_below_f1f2_threshold="add F4 (instruction/reset nets, already FIFO-decoupled by F2, also on M5) -> fits 815 down to a gate density of %.3f (upper bound: assumes M5 in the corridor is fully usable); beyond that F3 (column pairs, re-gate two-sided taps) then F7 (TP-8)." % (
                [f for f in fb if f['id'] == 'F1+F2+F4'][0]['gate_density_needed_for_815']),
            note="the B-series (one-sided pins) overflow at 0.43 means the PIN ROW arrangement matters as much as density: keep the centred pin row (C) as the selected arrangement in any fallback")),
        indent=1))


if __name__ == '__main__':
    main()
