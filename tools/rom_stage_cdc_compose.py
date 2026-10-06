#!/usr/bin/env python3
"""Gated stage clock spine with synchronised crossings and a shared per-stage controller (2026-10-04): verdict.

Inputs (results/rtl/rom_stage_spine_cdc_20261004/):
  exact.json                    tools/rom_stage_cdc_sim.py (randomised retention, 4 mutants), one-element stage
  power_k1.json / _k4.json      tools/rom_stage_cdc_power.py power: OpenSTA TT, routed SPEF + gate-level SAIF, ACTIVE /
                                PG_IDLE / CG_IDLE; AO leakage from the always-on block routed alone (A_K)
  power_by_class_k1/_k4.json    per-instance class power
  route_E1_* / route_S4_*       element-level (K = 1) and stage-level (K = 4) routes (WC record + SS/FF signoff)
  ao_route_A1_* / ao_route_A4_* the always-on blocks alone (the new logic): must close SS/FF
The per-element residual of a stage of N elements comes from the two MEASURED stages (K = 1 and K = 4): every power
P(K) = S + K * E (S shared: controller, spine, always-on branch root; E per element), so P(N) / N = E + S / N.

    python3 tools/rom_stage_cdc_compose.py [--dir results/rtl/rom_stage_spine_cdc_20261004]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rom_stage_pg_compose as pgc  # noqa: E402

PG_DIR = ROOT / "results/rtl/rom_stage_power_gating_20261004"
SP_DIR = ROOT / "results/rtl/rom_stage_spine_gate_20261004"
SB = ROOT / "results/arch/measured_scoreboard/scoreboard.json"
S = 81


def j(p):
    return json.loads(Path(p).read_text())


def sig(p):
    c = j(p)["corners"]
    return dict(ss_setup_wns_ps=round(c["SS"]["timing"]["setup_wns_ns"] * 1e3, 2),
                ss_hold_wns_ps=round(c["SS"]["timing"]["hold_wns_ns"] * 1e3, 2),
                ff_hold_wns_ps=round(c["FF"]["timing"]["hold_wns_ns"] * 1e3, 2))


def wc(p):
    d = j(p)["design"]
    return dict(setup_wns_ps=round(d["setup_wns_ns"] * 1e3, 2), hold_wns_ps=round(d["hold_wns_ns"] * 1e3, 2),
                area_um2=d.get("area_um2"), status=j(p).get("status"))


def stage_power(d: Path, k: int, ao_leak: float):
    pw = j(d / f"power_k{k}.json")
    st = {s: v["power_w"]["total"] for s, v in pw["states"].items()}
    i_busy = max(pgc.PAIR_BUSY_W, st["active"]["total"] / k) / pgc.VDD
    n_sw = k * math.ceil(i_busy * pgc.SW_R_ON / pgc.SW_DROP_V)
    sw_leak = n_sw * pgc.inv4_off_leak_w()
    leak_dom = st["cg_idle"]["leakage"] - ao_leak
    pg = st["pg_idle"]["total"] - leak_dom + sw_leak
    return dict(k=k, active=st["active"]["total"], cg_idle=st["cg_idle"]["total"], pg_idle_route=st["pg_idle"]["total"],
                leakage_domain=leak_dom, leakage_ao=ao_leak, header_cells=n_sw, header_off_leak_w=sw_leak, pg_idle=pg,
                residual=round(pg / st["cg_idle"]["total"], 5),
                by_class=j(d / f"power_by_class_k{k}.json"), activity_pass=pw["activity"]["pass"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(ROOT / "results/rtl/rom_stage_spine_cdc_20261004"))
    a = ap.parse_args()
    d = Path(a.dir)
    ex = j(d / "exact.json")
    leak = {k: j(d / f"ao_route_A{k}_signoff.json")["corners"]["TT"]["power_w"]["total"]["leakage"] for k in (1, 4)}
    P = {k: stage_power(d, k, leak[k]) for k in (1, 4)}
    # two-point decomposition: P(K) = S + K E
    def split(key):
        e = (P[4][key] - P[1][key]) / 3.0
        return P[1][key] - e, e
    s_pg, e_pg = split("pg_idle")
    s_cg, e_cg = split("cg_idle")
    per_elem = {}
    for n in (1, 4, 2417):
        per_elem[str(n)] = dict(pg_idle_w=e_pg + s_pg / n, cg_idle_w=e_cg + s_cg / n,
                                residual=round((e_pg + s_pg / n) / (e_cg + s_cg / n), 5))
    # wake (one-element stage, RTL) and the 1M window
    base = next(r for r in ex["runs"] if r["mutant"] is None)
    wl = next(x for x in base["tail"] if x.startswith("WAKE"))
    wmax = int(re.search(r"max=(\d+)", wl).group(1))
    rmax = int(re.search(r"restore max=(\d+)", wl).group(1))
    dc = j(PG_DIR / "domain_cap.json")
    c_f = dc["total_ff"] * 1e-15
    i_busy = max(pgc.PAIR_BUSY_W, P[1]["active"]) / pgc.VDD
    t_charge_ns = c_f * pgc.VDD / i_busy * 1e9
    nsub, sw_d = 4, 8
    seg_cycles = max(sw_d, math.ceil(t_charge_ns / nsub / pgc.CLK_NS))
    wake_cycles = wmax - nsub * sw_d + nsub * seg_cycles
    wake_ns = wake_cycles * pgc.CLK_NS
    e_wake = c_f * pgc.VDD ** 2
    pe = per_elem["2417"]
    t_be_us = e_wake / (pe["cg_idle_w"] - pe["pg_idle_w"]) * 1e6
    f = j(SB)["figures"]
    t_tok = f["ds_rom.ar_us_1m"]["value"]
    win = dict(ar_token_us=round(t_tok, 3), stages=S, stage_busy_us=round(t_tok / S, 3),
               idle_window_us=round(t_tok * (1 - 1 / S), 3), wake_us=round(wake_ns * 1e-3, 4),
               break_even_us=round(t_be_us, 4), wake_fits=wake_ns * 1e-3 < t_tok / S,
               gating_pays=t_be_us + wake_ns * 1e-3 < t_tok * (1 - 1 / S))
    tim = dict(A1_ao=sig(d / "ao_route_A1_signoff.json"), A4_ao=sig(d / "ao_route_A4_signoff.json"),
               E1_element_wc=wc(d / "route_E1_physical.json"), S4_stage_wc=wc(d / "route_S4_physical.json"),
               E1_element_signoff=sig(d / "route_E1_signoff.json"), S4_stage_signoff=sig(d / "route_S4_signoff.json"),
               R4_pg_reference_wc=wc(PG_DIR / "route_R4_physical.json"),
               R5_spine_no_cdc_wc=wc(SP_DIR / "route_R5_physical.json"))
    reasons = []
    exact_ok = ex["verdict"]["exact_with_gating"] and all(ex["verdict"]["mutants_detected"].values())
    if not exact_ok:
        reasons.append("not exact or a mutant escaped")
    for blk in ("A1_ao", "A4_ao"):
        t = tim[blk]
        if t["ss_setup_wns_ps"] < 0 or t["ff_hold_wns_ps"] < 0:
            reasons.append(f"always-on block {blk} does not close SS/FF ({t})")
    r4 = tim["R4_pg_reference_wc"]
    for blk in ("E1_element_wc", "S4_stage_wc"):
        t = tim[blk]
        if t["setup_wns_ps"] < r4["setup_wns_ps"] or t["hold_wns_ps"] < r4["hold_wns_ps"]:
            reasons.append(f"{blk} worse than the PG reference R4 ({t} vs {r4})")
    if not (P[1]["activity_pass"] and P[4]["activity_pass"]):
        reasons.append("gate-level activity bench failed")
    if not win["wake_fits"]:
        reasons.append("wake does not fit the stage window")
    verdict = ("ADOPT (opt-in, the stage power-gating successor): exact under power cycling, the always-on blocks close "
               f"SS/FF, E1/S4 routes no worse than R4 (relative acceptance, not full-stage SS/FF closure); residual per element {P[1]['residual'] * 100:.1f}% (1-element "
               f"stage), {P[4]['residual'] * 100:.2f}% (4-element stage), {pe['residual'] * 100:.2f}% at 2,417 elements a "
               "stage (two-point measured decomposition)") if not reasons else "REJECT: " + "; ".join(reasons)
    out = dict(
        schema="opentallas.rtl.rom_stage_spine_cdc_verdict.v1",
        vehicle="ot_v41_rom_stage_q_pg_cdc_w10: K power-gated S81 pair elements (BF16 0, NB 2, MTP, EARLY, FAST, PP) "
                "sharing one scheduler + W18 controller + spine gate on the always-on branch; K = 1 in one q-frame C "
                "(510.84 x 126.9 um), K = 4 in a 2 x 2 q-frame stage (1021.68 x 253.8 um)",
        exactness=dict(pass_=ex["verdict"]["exact_with_gating"], mutants_detected=ex["verdict"]["mutants_detected"],
                       tail=base["tail"][-5:], domain_state=ex["domain_state"]),
        power_w=dict(stage_k1=P[1], stage_k4=P[4],
                     decomposition=dict(shared_pg_idle_w=s_pg, per_element_pg_idle_w=e_pg, shared_cg_idle_w=s_cg,
                                        per_element_cg_idle_w=e_cg, per_element_at_n=per_elem,
                                        basis="P(K) = S + K E fitted exactly through the measured K = 1 and K = 4 stages"),
                     pg_idle_spine_gated=pe["pg_idle_w"], cg_idle_total=pe["cg_idle_w"],
                     residual_spine_gated_measured=P[1]["residual"],
                     residual_stage_k4_measured=P[4]["residual"],
                     residual_stage_2417=pe["residual"],
                     before=dict(R3_residual=j(PG_DIR / "verdict.json")["power_w"]["residual"],
                                 R5_residual=j(SP_DIR / "verdict.json")["power_w"]["residual_spine_gated_measured"])),
        wake=dict(rtl_req_to_ready_cycles_max=wmax, rtl_restore_cycles_max=rmax, charge_ns=round(t_charge_ns, 3),
                  wake_cycles=wake_cycles, wake_ns=round(wake_ns, 2), wake_energy_nj=round(e_wake * 1e9, 4),
                  break_even_us=round(t_be_us, 4)),
        windows={"1M": win}, timing=tim,
        timing_acceptance=dict(
            scope="E1/S4 WC timing relative to already-unclosed R4 element; not full-stage SS/FF signoff",
            reference_setup_wns_ps=r4["setup_wns_ps"], reference_hold_wns_ps=r4["hold_wns_ps"],
            full_stage_ss_ff_signoff_claim=False,
            always_on_scope="A1/A4 SS setup and FF hold under unchanged 60/25 ps uncertainties"),
        verdict=verdict,
        assumptions=["header switch ring, rush limit and domain capacitance as route R3's verdict (rom_stage_pg_compose)",
                     "a stage of 2,417 elements extrapolated linearly from the measured 1- and 4-element stages (the "
                     "shared controller/spine/branch-root power does not grow with K; the per-element parts do)"])
    (d / "verdict.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(verdict=verdict, wake=out["wake"], windows=win, timing=tim), indent=1))
    print(json.dumps({k: v for k, v in out["power_w"].items() if not k.startswith("stage_")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
