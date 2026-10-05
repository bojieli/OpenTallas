#!/usr/bin/env python3
"""W18: first-droop time-domain simulation of V4.1 ROM field-wide op starts at 1.2 GHz, for the candidate
current-management schemes, over the unknown package inductance and die capacitance.

Circuit (lumped): ideal regulator V0 -> series R_pkg, L_pkg -> die node (C_die) -> load current i(t).
Load: a base current (hub, PHYs, links, gated pairs) plus the field's busy current, shaped by the scheme; the
field current is clock-proportional (dynamic ~ 99.9% of the busy pair power, W18 pair record), so a clock
stretch (divide-by-2) halves it after the detector's response delay.

Schemes (each starts one field-wide op at t = 0 and holds it for the op's duration):
  cap50        50% concurrent-pair cap (ot_chip_v41_xcap), natural 17-cycle x-wavefront ramp; no detector
  cap75_r32    75% cap, 32-cycle ramp, droop detector (ot_chip_v41_droop_ctrl) + clock stretch
  ramp64_det   full field, 64-cycle ramp, detector as the safety net (GPU-style adaptive clocking)
  ramp17_det   full field, natural 17-cycle wavefront, detector only
  half_offset  two half-fields (checkerboard), the second starting R cycles after the first, each ramping
               over R, detector as safety net
  dtc_ramp17   full field, 17-cycle ramp, plus on-package deep-trench decap (C + C_dtc behind L_dtc)
Cost per op start (cycles): ramp cycles (the last group starts late), cap: extra issue (W16 prices), stretch:
half of every stretched cycle is lost.

    python3 tools/w18/droop_sim.py --output results/physical_abi3/asap7/chip/v41_w18/droop_schemes_1p2ghz.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIR_REC = ROOT / "results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json"
F = 1.2e9
TCK = 1 / F
V0 = 0.7
PEAK_PAIRS = 6899
POWER_SCALE_1P2 = 1.16          # root: dynamic power x1.16 at 1.2 GHz vs the 1.034-1.087 GHz measurement
I_BASE = 100.0                  # A: hub (model 10.7 W), PHYs, links, ICG-idle pairs (ASSUMED, ~70 W)
R_PKG = 1.0e-5                  # ohm (ASSUMED series package resistance; the regulator's remote sense restores DC, static die IR is PSM's)
L_SWEEP_PH = (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0)
C_SWEEP_UF = (5.0, 15.0, 30.0)
DET = dict(trip_v=0.021, release_v=0.0105, delay_cycles=2, min_cycles=16, hold_cycles=8)
DTC = dict(c_uf=200.0, l_ph=0.2, basis="ASSUMED on-package deep-trench / interposer decap behind 0.2 pH "
                                     "(silicon-interposer eDTC class); not an ASAP7 construct")
OP_CYCLES = 400                 # simulated op length (longer than every ramp and the LC period)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(i_field, scheme, L, C, dt=0.05e-9):
    frac = {"cap50": 0.5, "cap75_r32": 0.75}.get(scheme, 1.0)
    ramp = {"cap50": 17, "cap75_r32": 32, "ramp64_det": 64, "ramp17_det": 17, "half_offset": 32,
            "dtc_ramp17": 17, "preramp256": 256, "preramp1024": 1024, "cap50_preramp256": 256}[scheme]
    if scheme == "cap50_preramp256":
        frac = 0.5
    detector = scheme not in ("cap50", "dtc_ramp17", "preramp256", "preramp1024", "cap50_preramp256")
    Ld, Cd = L, C
    dtc = scheme == "dtc_ramp17"
    v, iL = V0 - (I_BASE) * R_PKG, I_BASE
    vd, iD = v, 0.0                                    # DTC branch
    n = int((max(OP_CYCLES, ramp + 300) + 100) * TCK / dt)
    vmin, stretch, st_on_at, st_cycles, trip_at, ok = V0, False, None, 0.0, None, 0
    last_cyc = -1
    for k in range(n):
        t = k * dt
        cyc = t / TCK
        if scheme == "half_offset":
            a = min(1.0, cyc / ramp)
            b = 0.0 if cyc < ramp else min(1.0, (cyc - ramp) / ramp)
            shape = 0.5 * a + 0.5 * b
        else:
            shape = frac * min(1.0, max(0.0, cyc / ramp))
        clk = 0.5 if stretch else 1.0
        i_load = I_BASE + i_field * shape * clk
        # regulator branch
        diL = (V0 - R_PKG * iL - v) / Ld
        iL += diL * dt
        if dtc:
            # DTC capacitor behind its own inductance, charged to the die voltage
            diD = (vd - v) / (DTC["l_ph"] * 1e-12)
            iD += diD * dt
            vd += (-iD) / (DTC["c_uf"] * 1e-6) * dt
            v += (iL + iD - i_load) / Cd * dt
        else:
            v += (iL - i_load) / Cd * dt
        vmin = min(vmin, v)
        c = int(cyc)
        if detector and c != last_cyc:
            last_cyc = c
            droop = V0 - R_PKG * I_BASE - v
            if not stretch:
                if droop > DET["trip_v"] and trip_at is None:
                    trip_at = c
                if trip_at is not None and c >= trip_at + DET["delay_cycles"]:
                    stretch, st_on_at, ok, trip_at = True, c, 0, None
            else:
                st_cycles += 1
                ok = ok + 1 if droop < DET["release_v"] else 0
                if c - st_on_at >= DET["min_cycles"] and ok >= DET["hold_cycles"]:
                    stretch = False
    # a pre-ramp runs ahead of the op on the static schedule (dummy clocking of the op's pairs): no latency,
    # energy = the ramp's integral of the field current
    ramp_cost = 0 if scheme.startswith("preramp") or scheme.endswith("preramp256") else ramp
    return dict(max_droop_mv=round((V0 - vmin) * 1e3, 1), peak_field_current_a=round(i_field * frac, 1),
                ramp_cycles=ramp, stretched_cycles=int(st_cycles), stretch_cost_cycles=round(st_cycles / 2, 1),
                start_cost_cycles=round(ramp_cost + st_cycles / 2, 1),
                cap_fraction=frac)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    pr = json.loads(PAIR_REC.read_text())
    busy = pr["power_w_per_pair"]["scenarios"]["busy_in0p5"] * POWER_SCALE_1P2
    i_field = PEAK_PAIRS * busy / V0
    schemes = ("cap50", "cap75_r32", "ramp64_det", "ramp17_det", "half_offset", "dtc_ramp17", "preramp256",
               "preramp1024", "cap50_preramp256")
    rows = []
    for s in schemes:
        for L in L_SWEEP_PH:
            for C in C_SWEEP_UF:
                r = run(i_field, s, L * 1e-12, C * 1e-6)
                rows.append(dict(scheme=s, L_pH=L, C_uF=C, **r))
    summ = {}
    for s in schemes:
        rs = [r for r in rows if r["scheme"] == s]
        summ[s] = dict(peak_field_current_a=rs[0]["peak_field_current_a"],
                       worst_droop_mv=max(r["max_droop_mv"] for r in rs),
                       droop_mv_at_L2_C15=next(r["max_droop_mv"] for r in rs if r["L_pH"] == 2.0 and r["C_uF"] == 15.0),
                       worst_start_cost_cycles=max(r["start_cost_cycles"] for r in rs),
                       start_cost_at_L2_C15=next(r["start_cost_cycles"] for r in rs if r["L_pH"] == 2.0 and r["C_uF"] == 15.0),
                       within_35mv_all=all(r["max_droop_mv"] <= 35 for r in rs),
                       max_L_pH_within_35mv={f"C{C}uF": max([r["L_pH"] for r in rs if r["C_uF"] == C and
                                                             r["max_droop_mv"] <= 35] or [0.0]) for C in C_SWEEP_UF},
                       max_L_pH_within_70mv={f"C{C}uF": max([r["L_pH"] for r in rs if r["C_uF"] == C and
                                                             r["max_droop_mv"] <= 70] or [0.0]) for C in C_SWEEP_UF},
                       preramp_energy_mj=(round(i_field * (0.5 if s == "cap50_preramp256" else 1.0) * V0 * 0.5
                                                * {"preramp256": 256, "preramp1024": 1024, "cap50_preramp256": 256}[s]
                                                * TCK * 1e3, 3) if "preramp" in s else None),
                       within_70mv_all=all(r["max_droop_mv"] <= 70 for r in rs))
    rec = dict(schema="opentallas.v41.w18_droop_schemes.v1", clock_hz=F, vdd_v=V0,
               field_current_a_full=round(i_field, 1), pair_busy_w_1p2ghz=round(busy, 4), base_current_a=I_BASE,
               r_pkg_ohm=R_PKG, detector=DET, dtc=DTC, sweep=dict(L_pH=L_SWEEP_PH, C_uF=C_SWEEP_UF),
               summary=summ, rows=rows,
               cost_note=("start_cost_cycles = ramp cycles + half of every stretched cycle, per field-wide op start; "
                          "cap schemes additionally cost the capped op's extra issue (W16 prices 50%: -6.7% AR, "
                          "-15.7% MTP); a 75% cap costs 1/3 of the 50% cap's extra issue"),
               budget_note=("ASAP7 SS sign-off is at 0.63 V (-10%): IR + droop + regulator tolerance must stay within "
                            "70 mV; 35 mV is the droop share if IR and tolerance take the rest"),
               inputs=dict(pair_record=str(PAIR_REC.relative_to(ROOT)), pair_record_sha256=sha(PAIR_REC)),
               package_spec=dict(
                   requirement="effective package + bump loop inductance seen by one die L_eff <= 2 pH with the adopted "
                               "50% cap + 256-cycle schedule-driven pre-ramp (<= 0.5 pH with the pre-ramp alone), for a "
                               "first droop <= 35 mV at 1.2 GHz; per-die decap >= 5 uF (the swept minimum)",
                   b200_class_reference=("no public L_eff figure for B200/GB200-class packages is known to this project; "
                                         "the requirement is ASSUMED feasible for a 2.5D CoWoS-class package with "
                                         "land-side / interposer capacitors and must be confirmed by the package owner"),
                   grade="assumed"),
               claim_boundary="lumped L-C-R first-droop model with assumed L, C, R and detector; no package model",
               tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(i_field=rec["field_current_a_full"], summary=summ), indent=1))


if __name__ == "__main__":
    main()
