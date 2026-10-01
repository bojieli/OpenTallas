#!/usr/bin/env python3
"""W11: the V4.1 stream unit's elements in the SERIAL clock domain (0.9 GHz = 1.111 ns, setup at SS / ORFS WC,
hold at FF / BC, 60 / 25 ps; AGENTS.md c0894b1c).  Summarises the routed records under
results/physical_abi3/asap7/hdc/v41x/w11_serial/<run>/physical.json (each source-pinned by the runner) and the
per-op depths of the serial build (ot_hdc_v41x_vec MLAT / ALAT; tools/rtl_hdc_v41x_vec_campaign.set_mlat) into
w11_serial/summary.json.  Failed verdicts stay listed.

    python3 tools/w11_su_serial_summary.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C   # noqa: E402

DIR = ROOT / "results/physical_abi3/asap7/hdc/v41x/w11_serial"

RUNS = {
    "sc_l5": "light lane (N=1,024, LEAF), MLAT 5 / ALAT 4 serial build: input-cut mul lat5i + add lat4i, keep-prefix "
             "integer arithmetic, three-cycle offset load; M2-M9",
    "sc_l5b": "sc_l5 re-routed on the current source layout (ot_hdc_fastfp_lat.sv split)",
    "sc_s5": "SFU lane (N=1,024, LEAF, lane 5), MLAT 5 / ALAT 4 serial build; M2-M9",
    "sc_s5m5": "SFU lane on M2-M5 only",
    "sc_r6": "the N=1,024 reducer, MLAT 5 / ALAT 4, second attempt (70 GB floor): the runner's flat yosys OOM-killed",
    "sc_r7": "the N=1,024 chunk8 reducer, MLAT 5 / ALAT 4, M2-M6, ORFS synthesis only (--stages pnr)",
    "sc_r64": "N=64 reducer slice (ot_hdc_v41x_vec_red64s), MLAT 5 / ALAT 4, M2-M6",
    "sc_s6": "SFU lane, MLAT 5 / ALAT 4, M2-M6, io-delay 0",
    "sc_s6io": "SFU lane, MLAT 5 / ALAT 4, M2-M6, io-delay 0.2 (the runner's default)",
    "sc_r5": "the reducer, first attempt: yosys OOM-killed at a 32 GB floor",
    "sc_l5m5u20": "sc_l5 on M2-M5 at 20% utilisation: global route overflow 167 (GRT-0116)",
    "sc_l5m5u15": "sc_l5 on M2-M5 at 15% utilisation: routes, misses by 0.4 ps (900 MHz)",
    "ll_m6": "sc_l5 routed on M2-M6 (W18b hub layer plan: SU_VECTOR obstructs M1-M7)",
    "ll_m7": "sc_l5 routed on M2-M7 (W18b hub layer plan)",
    "sc_l5m5": "sc_l5 routed on M2-M5 only (M6/M7 left free over the block): global route congestion (GRT-0116) at "
               "25% utilisation",
    "sc_l3": "light lane, MLAT 4 / ALAT 3 with keep-prefix arithmetic (no input cuts): the multipliers' stage 1 "
             "behind the lane's operand multiplexers",
    "sc_l2": "light lane, MLAT 4, FP units kept as modules, behavioural integer arithmetic",
    "sc_l1": "light lane, MLAT 4, flat synthesis, behavioural integer arithmetic",
    "sc_fmul5i": "standalone ot_hdc_fp32_mul_lat5i (C1 + C3 input-cut LAT 5)",
    "sc_fmul4_abc450": "standalone ot_hdc_fp32_mul_lat4 (ABC delay target 450 ps)",
    "sc_fadd3_abc450": "standalone ot_hdc_fp32_add_lat3 (ABC delay target 450 ps)",
}


def row(name, note):
    d = json.loads((DIR / name / "physical.json").read_text())
    g = d["design"]
    m = d.get("place_and_route", {}).get("metrics", {})
    argv = " ".join(d.get("runner", {}).get("argv", []))
    return dict(run=name, note=note, top=g.get("block"), parameters=g.get("parameters"), status=d.get("status"),
                closed=g.get("closed"), clock_period_ns=g.get("clock_period_ns"),
                ss_fmax_mhz=round(g["fmax_hz"] / 1e6, 1) if g.get("fmax_hz") else None,
                setup_wns_ps=round(g["setup_wns_ns"] * 1e3, 1) if g.get("setup_wns_ns") is not None else None,
                hold_wns_ps=round(g["hold_wns_ns"] * 1e3, 1) if g.get("hold_wns_ns") is not None else None,
                uncertainty_setup_hold_ps=[60, 25] if "--clock-uncertainty-hold-ns 0.025" in argv else None,
                corner="setup WC (SS), hold WC+BC (FF)" if "--hold-corners WC,BC" in argv else None,
                routing_layers=[a for a in ("M2 M5", "M2 M9") if f"--routing-layers {a}" in argv] or None,
                cell_area_um2=g.get("area_um2"), die_area_um2=m.get("die_area_um2"),
                drc=g.get("drc"), signal_integrity_clean=g.get("signal_integrity_clean"),
                commit=(d.get("git") or {}).get("commit"), worktree_dirty=(d.get("git") or {}).get("worktree_dirty"),
                currency=(d.get("currency") or {}).get("state", "current"))


def depths(mlat, alat):
    C.set_mlat(mlat, alat)
    lin = C.D_FETCH + C.D_PRE + C.D_M1 + C.D_STAGE + C.D_AD + 2 * C.D_STAGE + C.D_OUT
    sd = C.SFU_DEPTH
    I = C.I
    return dict(mlat=mlat, alat=alat, linear_emit_to_write=lin, divide_m1=C.D_DIV, exp_in_S=sd[I.SFU_EXP],
                sigmoid_silu_in_S=sd[I.SFU_SIGM], rsqrt_in_S=sd[I.SFU_RSQRT], sqrt_in_S=sd[I.SFU_SQRT],
                sqrt_softplus_in_S=sd[I.SFU_SPSQRT], engram_gate_in_S=sd[I.SFU_EGATE],
                reducer_retire_to_result_tap0=C.D_RED, reducer_per_tree_or_time_level=C.D_RSTEP)


def main():
    rows = [row(n, t) for n, t in RUNS.items() if (DIR / n / "physical.json").exists()]
    rec = dict(schema="opentallas.w11.su_serial_domain/1", clock_period_ns=1.111, clock="0.9 GHz serial-chain domain",
               policy="setup at SS (ORFS WC), hold at FF (BC), 60 ps setup / 25 ps hold uncertainty",
               runs=rows,
               depths=dict(before=depths(3, 3), serial_build=depths(5, 4)),
               added_cycles=None)
    b, s = rec["depths"]["before"], rec["depths"]["serial_build"]
    rec["added_cycles"] = {k: s[k] - b[k] for k in b if k not in ("mlat", "alat")}
    (DIR / "summary.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["added_cycles"]))
    for r in rows:
        print(r["run"], r["status"], r["ss_fmax_mhz"], r["setup_wns_ps"], r["hold_wns_ps"])


if __name__ == "__main__":
    main()
