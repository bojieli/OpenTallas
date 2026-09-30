#!/usr/bin/env python3
"""W12: peak current and first droop of the Qwen3-8B ROM die (TP-4 product, G = 6,144, 1,536 tiles) when every
tile's matrix engine starts an op at once, at 1.2 GHz -- the W18 V4.1 analysis (tools/w18/droop_sim.py) applied
to the Qwen die with the Qwen tile's power.

Inputs:
  * the tile's power (OpenSTA report_power on the W12 tile route's CTS database, TT 0.7 V, 0.833 ns clock,
    placement parasitics; activity scenarios as W18's pair record): --tile-power (a record written by this
    tool's --write-tile-power from the report log);
  * the die's ME op list (tools/hdc_program.build_program on the TP-4 die shape, AR only): every ME op is
    field-wide -- each op's rounds cover all 6,144 groups -- so every op start is a full-field current step.
The droop circuit, schemes, detector and sweep are W18's (droop_sim.run, imported unchanged); only the field
current and the base current differ.  Cost per scheme: ramp cycles and stretch per op start times the ops a
token, and the 50% cap's extra issue (the capped ops issue at half rate: + their issue cycles).

    python3 tools/qwen_rom_droop_w12.py --tile-power R.json --output results/floorplan/qwen_rom_w12/droop_1p2ghz.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/w18"))
import droop_sim as DS  # noqa: E402

TILES = 1536
V0 = DS.V0
I_BASE = 60.0        # A: spine (engine top, sequencer, SU, VM), 4 HBM PHYs, UCIe, gated tiles (ASSUMED; W18 used 100 A)
MODEL_CYCLES = 201080  # cycles a token, the model at SW = 64 (W16, 2026-09-30)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_power(log: str) -> dict:
    out = {}
    for tag, body in re.findall(r"OT_POWER_BEGIN (\S+)\n(.*?)(?=OT_POWER_BEGIN|OTC|\Z)", log, re.S):
        row = {}
        for grp in ("Sequential", "Combinational", "Clock", "Macro", "Total"):
            m = re.search(rf"^{grp}\s+([-0-9.e+]+)\s+([-0-9.e+]+)\s+([-0-9.e+]+)\s+([-0-9.e+]+)", body, re.M)
            if m:
                row[grp.lower()] = dict(internal_w=float(m.group(1)), switching_w=float(m.group(2)),
                                        leakage_w=float(m.group(3)), total_w=float(m.group(4)))
        out[tag] = row
    return out


def me_ops(ctx: int, tp: int = 4, groups: int = 6144, su_width: int = 64):
    import arch_budget_qwen3 as Q
    import hdc_isa as I
    import hdc_program as P
    import hdc_timing as T
    sw0 = I.SU_WIDTH
    I.SU_WIDTH = su_width
    try:
        s = Q.Q
        shape = dict(s, NH=s["NH"] // tp, KV=s["KV"] // tp, FF=s["FF"] // tp, V=s["V"] // tp)
        prog = P.build_program(Q.capped_layout(groups, None, shape))
    finally:
        I.SU_WIDTH = sw0
    d = T.dyn_values(ctx - 1, groups=groups, H=Q.Q["H"], half=Q.Q["HD"] // 2, HD=Q.Q["HD"])
    n = issue = kv = 0
    for f in prog:
        if f.get("unit") != I.UNIT_ME:
            continue
        f = {nm: f.get(nm, 0) for nm, _ in I.FIELDS}
        r, kk = T.me_loop(f, d, ctx - 1, groups)
        n += 1
        issue += r * kk * I.INTERLEAVE
        kv += f["me_wsrc"]
    return dict(ops=n, kv_ops=kv, issue_cycles=issue, ctx=ctx, tp=tp, groups=groups, su_width=su_width)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tile-power", type=Path, required=True)
    ap.add_argument("--write-tile-power", type=Path, help="report_power log -> write the --tile-power record")
    ap.add_argument("--odb-sha256", help="with --write-tile-power: the database the log measured")
    ap.add_argument("--output", type=Path)
    a = ap.parse_args(argv)
    if a.write_tile_power:
        pw = parse_power(a.write_tile_power.read_text())
        rec = dict(schema="opentallas.qwen-rom-w12.tile-power.v1",
                   element="ot_qwen_rom_tile (W12 route tile_n518, 518.4 x 386.64 um, 0.833 ns, 60/25; CTS database "
                           "4_cts.odb: synthesised at ORFS CORNER=TC with ripple adders, NOT timing-closed)",
                   basis="OpenSTA report_power, TT 0.7 V RVT + the macros' _tt.lib, 1.2 GHz, placement parasitics "
                         "(setRC), propagated clock; scenarios: default activity, input activity 0.5 / 0.25 (duty 0.5), "
                         "input activity 0 with the clock running (idle, clock on)",
                   odb_sha256=a.odb_sha256, log_sha256=sha(a.write_tile_power),
                   scenarios={k: v["total"]["total_w"] for k, v in pw.items() if "total" in v}, breakdown=pw,
                   note="the macro group (0.090 W) is the 12 macros' clock/internal power at every edge: ICG must gate "
                        "the 8 unselected code-ROM banks and the idle KV SRAMs (W18 icg_requirement)")
        a.tile_power.parent.mkdir(parents=True, exist_ok=True)
        a.tile_power.write_text(json.dumps(rec, indent=1) + "\n")
        if not a.output:
            return
    tp = json.loads(a.tile_power.read_text())
    busy = tp["scenarios"]["busy_in0p5"]
    idle = tp["scenarios"]["idle_clock_on"]
    i_field = TILES * busy / V0
    DS.I_BASE = I_BASE
    schemes = ("cap50", "cap75_r32", "ramp64_det", "ramp17_det", "half_offset", "dtc_ramp17", "preramp256",
               "preramp1024", "cap50_preramp256")
    rows = []
    for s in schemes:
        for L in DS.L_SWEEP_PH:
            for C in DS.C_SWEEP_UF:
                rows.append(dict(scheme=s, L_pH=L, C_uF=C, **DS.run(i_field, s, L * 1e-12, C * 1e-6)))
    ops = {c: me_ops(c) for c in (1, 8192)}
    o8k = ops[8192]
    summ = {}
    for s in schemes:
        rs = [r for r in rows if r["scheme"] == s]
        at = next(r for r in rs if r["L_pH"] == 2.0 and r["C_uF"] == 15.0)
        cap = at["cap_fraction"] < 1.0
        start = at["start_cost_cycles"] * o8k["ops"]
        extra_issue = o8k["issue_cycles"] * (1 / at["cap_fraction"] - 1) if cap else 0.0
        cyc = start + extra_issue
        summ[s] = dict(peak_field_current_a=rs[0]["peak_field_current_a"],
                       droop_mv_at_L2_C15=at["max_droop_mv"], worst_droop_mv=max(r["max_droop_mv"] for r in rs),
                       max_L_pH_within_35mv={f"C{C}uF": max([r["L_pH"] for r in rs if r["C_uF"] == C and
                                                             r["max_droop_mv"] <= 35] or [0.0]) for C in DS.C_SWEEP_UF},
                       max_L_pH_within_70mv={f"C{C}uF": max([r["L_pH"] for r in rs if r["C_uF"] == C and
                                                             r["max_droop_mv"] <= 70] or [0.0]) for C in DS.C_SWEEP_UF},
                       start_cost_cycles_per_op_at_L2_C15=at["start_cost_cycles"],
                       cycles_per_token_at_L2_C15=round(cyc, 1),
                       tok_s_cost_fraction_vs_model=round(cyc / MODEL_CYCLES, 4),
                       preramp_energy_mj_per_op=(round(i_field * at["cap_fraction"] * V0 * 0.5 * at["ramp_cycles"]
                                                       / DS.F * 1e3, 4) if "preramp" in s else None))
    rec = dict(
        schema="opentallas.qwen-rom-w12.droop.v1", clock_hz=DS.F, vdd_v=V0, tiles=TILES,
        tile_power_w=dict(busy_in0p5=busy, idle_clock_on=idle, record=str(a.tile_power), record_sha256=sha(a.tile_power)),
        field=dict(power_w_busy=round(TILES * busy, 1), current_a_busy=round(i_field, 1),
                   power_w_idle_clock_on=round(TILES * idle, 1),
                   vs_b200=dict(current_a=[1300.0, 1500.0], basis="root's B200-class envelope, ASSUMED (W18)",
                                ratio_to_upper=round(i_field / 1500.0, 3))),
        base_current_a=I_BASE, base_basis="ASSUMED: spine, SU, VM, 4 HBM PHYs, UCIe and gated tiles",
        me_ops_per_token=ops, model_cycles_per_token=MODEL_CYCLES,
        every_op_field_wide=("each ME op's rounds cover all 6,144 groups (the K split times the tiles a round), so every "
                             "op start steps the whole field; %d starts a token (%d KV-sourced)" % (o8k["ops"], o8k["kv_ops"])),
        summary=summ, rows=rows,
        verdict=None,
        w18_reference=dict(record="results/physical_abi3/asap7/chip/v41_w18/droop_schemes_1p2ghz.json",
                           adopted="50% cap + 256-cycle schedule-driven pre-ramp"),
        claim_boundary=("lumped L-C-R first droop (W18's model and assumptions: R_pkg, detector, DTC, L and C sweeps); "
                        "tile power from a pre-route CTS database synthesised at TT with ripple adders, not a signed-off "
                        "tile; base current assumed"),
        sources={p: sha(ROOT / p) for p in ("tools/qwen_rom_droop_w12.py", "tools/w18/droop_sim.py",
                                            "tools/arch_budget_qwen3.py", "tools/hdc_program.py", "tools/hdc_timing.py")})
    s = summ
    rec["verdict"] = (
        f"full-field step {i_field:.0f} A ({TILES * busy:.0f} W) vs the V4.1 die's 2,625 A: "
        f"ramp17 {s['ramp17_det']['droop_mv_at_L2_C15']} mV at 2 pH / 15 uF; preramp256 "
        f"{s['preramp256']['droop_mv_at_L2_C15']} mV (0 cycles); cap50+preramp256 {s['cap50_preramp256']['droop_mv_at_L2_C15']} mV "
        f"but +{s['cap50_preramp256']['tok_s_cost_fraction_vs_model'] * 100:.1f}% cycles (the cap doubles every op's issue)")
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(field=rec["field"], ops=o8k, verdict=rec["verdict"],
                          summary={k: {kk: v[kk] for kk in ("droop_mv_at_L2_C15", "max_L_pH_within_35mv",
                                                            "cycles_per_token_at_L2_C15",
                                                            "tok_s_cost_fraction_vs_model")} for k, v in summ.items()}),
                     indent=1))


if __name__ == "__main__":
    main()
