#!/usr/bin/env python3
"""Gated stage clock spine (2026-10-04): compose the measured spine-gate results into its verdict.

Inputs (results/rtl/rom_stage_spine_gate_20261004/):
  exact.json                 tools/rom_stage_spine_sim.py: power-aware exactness with the spine gated (randomised
                             retention, every output every cycle), wake cycles, mutants
  power.json                 tools/rom_stage_spine_power.py power: OpenSTA TT, routed SPEF + gate-level SAIF, route R5
                             (ot_v41_rom_elem_q_pg_sp_w10, SPINE = 1) in ACTIVE / PG_IDLE / CG_IDLE; AO-side leakage
                             from route A3 (ot_v41_rom_pg_ao_sp alone)
  power_by_class.json        per-instance power by class (domain / spine / scheduler+controller / AO element / AO clock)
  ao_route_A3_signoff.json   SS / FF timing of the always-on side with the spine gate (the new logic)
  route_R5_*.json            the element route (reported; the element itself is not closed in this frame, R0 -219 ps)
The domain capacitance (wake charge) is the same domain as route R3: results/rtl/rom_stage_power_gating_20261004/
domain_cap.json.  The header ring is sized exactly as tools/rom_stage_pg_compose.py does.

    python3 tools/rom_stage_spine_compose.py [--dir results/rtl/rom_stage_spine_gate_20261004]
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
SB = ROOT / "results/arch/measured_scoreboard/scoreboard.json"
S = 81


def timing(sig: dict) -> dict:
    c = sig["corners"]
    return dict(ss_setup_wns_ps=round(c["SS"]["timing"]["setup_wns_ns"] * 1e3, 2),
                ff_hold_wns_ps=round(c["FF"]["timing"]["hold_wns_ns"] * 1e3, 2),
                ss_hold_wns_ps=round(c["SS"]["timing"]["hold_wns_ns"] * 1e3, 2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=str(ROOT / "results/rtl/rom_stage_spine_gate_20261004"))
    a = ap.parse_args()
    d = Path(a.dir)
    ex = json.loads((d / "exact.json").read_text())
    pw = json.loads((d / "power.json").read_text())
    cls = json.loads((d / "power_by_class.json").read_text())
    dc = json.loads((PG_DIR / "domain_cap.json").read_text())
    old = json.loads((PG_DIR / "verdict.json").read_text())
    st = {k: v["power_w"]["total"] for k, v in pw["states"].items()}
    leak_full = st["cg_idle"]["leakage"]
    leak_ao = pw["ao_route"]["power_w"]["total"]["leakage"]
    leak_dom = leak_full - leak_ao
    i_busy = max(pgc.PAIR_BUSY_W, st["active"]["total"]) / pgc.VDD
    n_sw = math.ceil(i_busy * pgc.SW_R_ON / pgc.SW_DROP_V)
    sw_leak = n_sw * pgc.inv4_off_leak_w()
    p_cg = st["cg_idle"]["total"]
    p_pg = st["pg_idle"]["total"] - leak_dom + sw_leak
    resid = p_pg / p_cg
    ctl = cls["pg_idle"].get("ao_sched_ctrl", {}).get("total_w", 0.0)
    aon = cls["pg_idle"].get("aon_clock", {}).get("total_w", 0.0)
    p_sh = p_pg - ctl * (1 - 1 / pgc.PAIRS_PER_DIE)
    p_sh2 = p_sh - aon * (1 - 1 / pgc.PAIRS_PER_DIE)
    # wake: measured RTL req -> ready with the spine, the ring's charge stretched to the rush limit (as R3)
    base = next(r for r in ex["runs"] if r["mutant"] is None)
    wl = next(x for x in base["tail"] if x.startswith("WAKE"))
    wmax = int(re.search(r"max=(\d+)", wl).group(1))
    rmax = int(re.search(r"restore max=(\d+)", wl).group(1))
    spl = next((x for x in base["tail"] if x.startswith("SPINE")), "")
    c_f = dc["total_ff"] * 1e-15
    t_charge_ns = c_f * pgc.VDD / i_busy * 1e9
    nsub, sw_d = 4, 8
    seg_cycles = max(sw_d, math.ceil(t_charge_ns / nsub / pgc.CLK_NS))
    wake_cycles = wmax - nsub * sw_d + nsub * seg_cycles
    wake_ns = wake_cycles * pgc.CLK_NS
    e_wake = c_f * pgc.VDD ** 2
    t_be_us = e_wake / (p_cg - p_pg) * 1e6
    f = json.loads(SB.read_text())["figures"]
    t_tok = f["ds_rom.ar_us_1m"]["value"]
    win = dict(ar_token_us=round(t_tok, 3), ar_token_src="measured scoreboard ds_rom.ar_us_1m (" +
               f["ds_rom.ar_us_1m"]["status"] + ")", stages=S, stage_busy_us=round(t_tok / S, 3),
               idle_window_us=round(t_tok * (1 - 1 / S), 3), wake_us=round(wake_ns * 1e-3, 4),
               break_even_us=round(t_be_us, 4), wake_fits=wake_ns * 1e-3 < t_tok / S,
               gating_pays=t_be_us + wake_ns * 1e-3 < t_tok * (1 - 1 / S))
    tim = {}
    for name, fn in (("A3_ao_spine", "ao_route_A3_signoff.json"), ("R5_element", "route_R5_signoff.json")):
        p = d / fn
        tim[name] = timing(json.loads(p.read_text())) if p.exists() else None
    a3 = tim["A3_ao_spine"]
    closes = bool(a3 and a3["ss_setup_wns_ps"] >= 0 and a3["ff_hold_wns_ps"] >= 0)
    exact_ok = ex["verdict"]["exact_with_gating"] and all(ex["verdict"]["mutants_detected"].values())
    reasons = []
    if not exact_ok:
        reasons.append("not exact or a mutant escaped")
    if not closes:
        reasons.append(f"AO + spine gate route does not close SS/FF ({a3})")
    if not win["wake_fits"]:
        reasons.append("wake does not fit the stage window")
    # the element frame never closed (R0 ungated -219 ps); the spine must not make it worse than the PG reference R4
    r4 = json.loads((PG_DIR / "route_R4_physical.json").read_text())["design"]
    r5p = d / "route_R5_physical.json"
    if r5p.exists():
        r5 = json.loads(r5p.read_text())["design"]
        tim["R4_pg_reference_wc"] = dict(setup_wns_ps=round(r4["setup_wns_ns"] * 1e3, 2), hold_wns_ps=round(r4["hold_wns_ns"] * 1e3, 2))
        tim["R5_element_wc"] = dict(setup_wns_ps=round(r5["setup_wns_ns"] * 1e3, 2), hold_wns_ps=round(r5["hold_wns_ns"] * 1e3, 2),
                                    worst_setup_path="u_pg.u_elem.drain[2] (spine domain) -> u_pg.g_pg.u_ao.u_sched.u_pg.cnt "
                                                     "(AO branch): domain busy into the scheduler across the unbalanced trees",
                                    src="jobs/R5 6_finish.rpt")
        if r5["setup_wns_ns"] < r4["setup_wns_ns"] or r5["hold_wns_ns"] < r4["hold_wns_ns"]:
            reasons.append(f"in the element frame the spine route is worse than the PG reference R4 (WC setup "
                           f"{r5['setup_wns_ns'] * 1e3:.0f} vs {r4['setup_wns_ns'] * 1e3:.0f} ps, hold "
                           f"{r5['hold_wns_ns'] * 1e3:.0f} vs {r4['hold_wns_ns'] * 1e3:.0f} ps): the domain -> AO "
                           "scheduler crossing pays the skew between the gated spine tree and the AO branch")
    if resid >= old["power_w"]["residual"]:
        reasons.append("no residual reduction")
    verdict = ("ADOPT (opt-in SPINE = 1): exact under power cycling, AO + spine gate closes SS/FF, wake fits the 1M "
               f"window; residual {old['power_w']['residual'] * 100:.1f}% -> {resid * 100:.2f}% per element "
               f"({p_sh / p_cg * 100:.2f}% with one controller a stage)") if not reasons else "REJECT: " + "; ".join(reasons)
    out = dict(
        schema="opentallas.rtl.rom_stage_spine_gate_verdict.v1",
        element="S81 pair element core ot_v41_rom_elem_w10 (BF16 0, NB 2, MTP, EARLY, FAST, PP) as one power domain behind "
                "ot_v41_rom_pg_ao_sp SPINE = 1 (gated stage clock spine + always-on clock branch), top "
                "ot_v41_rom_elem_q_pg_sp_w10, routed in the q-frame C (510.84 x 126.9 um)",
        exactness=dict(pass_=ex["verdict"]["exact_with_gating"], mutants_detected=ex["verdict"]["mutants_detected"],
                       tail=base["tail"][-4:], spine=spl, domain_state=ex["domain_state"]),
        power_w=dict(active=st["active"], cg_idle=st["cg_idle"], pg_idle_route=st["pg_idle"], leakage_domain=leak_dom,
                     leakage_ao_route=leak_ao, header_cells=n_sw, header_off_leak_w=sw_leak,
                     pg_idle_spine_gated=p_pg, cg_idle_total=p_cg, residual_spine_gated_measured=round(resid, 5),
                     by_class=cls, sched_ctrl_pg_idle_w=ctl, aon_clock_pg_idle_w=aon,
                     pg_idle_spine_gated_controller_shared=p_sh,
                     residual_spine_gated_controller_shared=round(p_sh / p_cg, 5),
                     pg_idle_spine_gated_controller_and_aon_shared=p_sh2,
                     residual_spine_gated_controller_and_aon_shared=round(p_sh2 / p_cg, 5),
                     before=dict(pg_idle=old["power_w"]["pg_idle"], residual=old["power_w"]["residual"],
                                 src="results/rtl/rom_stage_power_gating_20261004/verdict.json (route R3)")),
        wake=dict(rtl_req_to_ready_cycles_max=wmax, rtl_restore_cycles_max=rmax, domain_cap_pf=round(c_f * 1e12, 1),
                  charge_ns=round(t_charge_ns, 3), wake_cycles=wake_cycles, wake_ns=round(wake_ns, 2),
                  wake_energy_nj=round(e_wake * 1e9, 4), break_even_us=round(t_be_us, 4)),
        windows={"1M": win}, timing=tim, verdict=verdict,
        assumptions=["header switch ring, wake rush limit and domain capacitance exactly as route R3's verdict "
                     "(tools/rom_stage_pg_compose.py)",
                     "controller-shared rows divide the measured scheduler/controller power over one stage's "
                     f"{pgc.PAIRS_PER_DIE} elements (one controller a stage, as the die instantiates it)",
                     "aon_clk is a separate port in the vehicle: the AO island's own clock branch, as in the die"])
    (d / "verdict.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "wake", "windows", "timing")}, indent=1))
    print(json.dumps({k: v for k, v in out["power_w"].items() if k != "by_class"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
