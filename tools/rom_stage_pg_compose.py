#!/usr/bin/env python3
"""ROM stage power gating (2026-10-04): compose the measured element results into the gating verdict and re-price DS ROM.

Inputs (results/rtl/rom_stage_power_gating_20261004/):
  exact.json   tools/rom_stage_pg_sim.py: power-aware RTL exactness (domain state randomised on every power-off),
               wake / restore cycles measured in RTL, mutants
  power.json   tools/rom_stage_pg_power.py: OpenSTA report_power (TT, routed SPEF, gate-level SAIF) of the routed
               gated element in ACTIVE / PG_IDLE / CG_IDLE, and the always-on side's own route (leakage)
  domain_cap.json  tools/rom_stage_pg_compose.py cap: the gated domain's capacitance from the route (SPEF wire +
               Liberty pin caps) and the ROM macros' compiler model
Output: verdict.json (per element: residual, wake latency vs idle window, break-even; DS ROM re-price through
tools/ds_energy_silicon_authoritative.py with the measured residual in place of its ASSUMED 10%).

    python3 tools/rom_stage_pg_compose.py cap --routed <R1 results dir> --out .../domain_cap.json
    python3 tools/rom_stage_pg_compose.py verdict --dir results/rtl/rom_stage_power_gating_20261004
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

VDD = 0.7
CLK_NS = 0.833
LIB_INVBUF = Path.home() / ".local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib"
LIBS = [Path.home() / f".local/opentallas-pdk-asap7/lib/NLDM/asap7sc7p5t_{n}_RVT_TT_{d}.lib" for n, d in
        (("AO", "nldm_211120"), ("INVBUF", "nldm_220122"), ("OA", "nldm_211120"), ("SEQ", "nldm_220123"),
         ("SIMPLE", "nldm_211120"))]
ROM_JSON = ROOT / "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.json"
# header switch: W18's ring cell (tools/w18/die_pdn.py SWITCH_CELL): the pull-up of an ASAP7 INVx4, R_on 912.5 ohm,
# 0.432 x 0.27 um.  Its off-state leakage is the Liberty INVx4 leakage with A = 1 (PMOS off, Vds = VDD).
SW_R_ON = 912.5
SW_AREA_UM2 = 0.432 * 0.27
SW_DROP_V = 0.010                    # W18 ring budget (10 mV), tools/uarch_model.py SWITCH_RING
PAIR_BUSY_W = 0.2296                 # W18 measured busy pair (toggle 0.5), tools/uarch_model.py PAIR_W: switch sizing
ELEM_AREA_UM2 = 510.84 * 126.9
PAIRS_PER_DIE = 2417                 # S81 NP (results/uarch/dsrom_c_recheck_20261004 area.pairs)


def inv4_off_leak_w() -> float:
    s = LIB_INVBUF.read_text()
    body = s[s.index("cell (INVx4_ASAP7_75t_R)"):]
    body = body[:body.index("\n  cell (", 10)]
    v = re.search(r'leakage_power \(\) \{\s*value : ([0-9.eE+-]+);\s*when : "\(A \* !Y\)";\s*related_pg_pin : VDD;', body)
    return float(v.group(1)) * 1e-12


def pin_caps() -> dict:
    caps = {}
    for lib in LIBS:
        s = lib.read_text()
        for m in re.finditer(r"\n  cell \((\w+)\) \{(.*?)(?=\n  cell \(|\Z)", s, re.S):
            tot = 0.0
            for p in re.finditer(r"pin \((\w+)\) \{(.*?)\n    \}", m.group(2), re.S):
                if re.search(r"direction : input;", p.group(2)):
                    c = re.search(r"\n      capacitance : ([0-9.eE+-]+);", p.group(2))
                    tot += float(c.group(1)) if c else 0.0
            caps[m.group(1)] = tot                      # fF
    return caps


def cap(a) -> int:
    rd = Path(a.routed)
    spef = rd / "6_final.spef"
    unit = 1.0
    wire_ff = 0.0
    with open(spef) as f:
        for ln in f:
            if ln.startswith("*C_UNIT"):
                v, u = ln.split()[1:3]
                unit = float(v) * {"FF": 1.0, "PF": 1e3}[u.upper()]
            elif ln.startswith("*D_NET"):
                wire_ff += float(ln.split()[2]) * unit
    caps = pin_caps()
    counts: dict[str, int] = {}
    for m in re.finditer(r"^\s*(\w+)\s+\\?\S+\s*\(", (rd / "6_final.v").read_text(), re.M):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    pin_ff = sum(caps.get(c, 0.0) * n for c, n in counts.items())
    rom = json.loads(ROM_JSON.read_text())
    bd = rom["timing"]["tt"]["breakdown"]
    nrom = counts.get("ot_rom_4096x274_m8", 0)
    rom_ff = nrom * (2192 * bd["bitline_cap_ff"] + 512 * bd["wordline_cap_ff"])
    out = dict(spef_wire_ff=round(wire_ff, 1), liberty_input_pin_ff=round(pin_ff, 1),
               intrinsic_ff_assumed=round(pin_ff, 1), rom_macros=nrom, rom_array_ff=round(rom_ff, 1),
               total_ff=round(wire_ff + 2 * pin_ff + rom_ff, 1),
               basis=("routed SPEF D_NET totals + Liberty input-pin capacitance of every instance (measured); "
                      "cell-internal/diffusion capacitance ASSUMED equal to the input-pin total; ROM macros: compiler "
                      "model 2,192 bitlines x bitline_cap + 512 wordlines x wordline_cap (TT), an upper bound "
                      "(every via present)"),
               cells=sum(counts.values()))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


def verdict(a) -> int:
    d = Path(a.dir)
    ex = json.loads((d / "exact.json").read_text())
    pw = json.loads((d / "power.json").read_text())
    dc = json.loads((d / "domain_cap.json").read_text())
    st = {k: v["power_w"]["total"] for k, v in pw["states"].items()}
    leak_full = st["cg_idle"]["leakage"]
    leak_ao = pw["ao_route"]["power_w"]["total"]["leakage"]
    leak_dom = leak_full - leak_ao
    # header ring sized for the W18 10 mV budget at the busy pair current
    i_busy = max(PAIR_BUSY_W, st["active"]["total"]) / VDD
    n_sw = math.ceil(i_busy * SW_R_ON / SW_DROP_V)
    sw_leak = n_sw * inv4_off_leak_w()
    p_cg = st["cg_idle"]["total"]
    p_pg = st["pg_idle"]["total"] - leak_dom + sw_leak     # the off domain leaks only through its headers
    resid = p_pg / p_cg
    # sensitivity (ASSUMED sharing): one scheduler + power controller per die region of PAIRS_PER_DIE elements instead
    # of one per element; its measured class power (flops, ICG, logic) is divided among them.  The root clock tree
    # stays charged per element (conservative: in a die it is the shared AO spine)
    cls = json.loads((d / "power_by_class.json").read_text())
    ctl = cls["pg_idle"]["ao_sched_ctrl"]["total_w"]
    p_pg_shared = p_pg - ctl * (1 - 1 / PAIRS_PER_DIE)
    resid_shared = p_pg_shared / p_cg
    # sensitivity (ASSUMED die design): the stage clock spine is also gated while the whole stage sleeps (only the
    # shared controller keeps a clock), so the per-element root clock tree measured here drops out
    rc = cls["pg_idle"]["root_clock"]["total_w"]
    p_pg_spine = p_pg_shared - rc
    resid_spine = p_pg_spine / p_cg
    # wake: measured RTL sequence (req_on -> ready) with the bench's ring model; the ring's charge time bounded
    # by a rush current no larger than the busy current
    wl = next(x for r in ex["runs"] if r["mutant"] is None for x in r["tail"] if x.startswith("WAKE"))
    wmax = int(re.search(r"max=(\d+)", wl).group(1))
    rmax = int(re.search(r"restore max=(\d+)", wl).group(1))
    c_f = dc["total_ff"] * 1e-15
    t_charge_ns = c_f * VDD / i_busy * 1e9
    nsub, sw_d = 4, 8
    seg_cycles = max(sw_d, math.ceil(t_charge_ns / nsub / CLK_NS))
    wake_cycles = wmax - nsub * sw_d + nsub * seg_cycles
    e_wake = c_f * VDD ** 2
    t_be_us = e_wake / (p_cg - p_pg) * 1e6
    import ds_energy_silicon_authoritative as E
    R, _, _ = E.rates()
    S = 81
    windows = {}
    for c in E.CTX:
        t_tok = 1e6 / R[c]["rom"]["ar"]
        windows[c] = dict(ar_token_us=round(t_tok, 2), stage_busy_us=round(t_tok / S, 2),
                          idle_window_us=round(t_tok - t_tok / S, 2), wake_us=round(wake_cycles * CLK_NS * 1e-3, 4),
                          break_even_us=round(t_be_us, 4),
                          wake_fits=wake_cycles * CLK_NS * 1e-3 < t_tok / S,
                          gating_pays=t_be_us + wake_cycles * CLK_NS * 1e-3 < t_tok - t_tok / S)
    # re-price: ds_energy_silicon_authoritative charges PG_RES on the whole layer-die always-on (logic 19.596 W +
    # SerDes 30.6 W); the measured residual replaces the logic part, the SerDes lane-gating residual stays ASSUMED
    logic_w = E.LAYER_DIE_W - E.SERDES_W
    res_eff = (logic_w * resid + E.SERDES_W * 0.10) / E.LAYER_DIE_W
    base_P, _, _ = E.power(R)
    E.PG_RES = res_eff
    meas_P, _, _ = E.power(R)
    res_eff_sh = (logic_w * resid_shared + E.SERDES_W * 0.10) / E.LAYER_DIE_W
    E.PG_RES = res_eff_sh
    sh_P, _, _ = E.power(R)
    res_eff_sp = (logic_w * resid_spine + E.SERDES_W * 0.10) / E.LAYER_DIE_W
    E.PG_RES = res_eff_sp
    sp_P, _, _ = E.power(R)
    E.PG_RES = 0.10
    keys = ("ar_b1_icg", "ar_b1_pg", "mtp_as_built_b1_pg", "mtp_l1_fused_b1_pg", "ar_sat_pg")
    reprice = {c: {k: dict(assumed_10pct=dict(J_per_token=base_P[c]["rom"][k]["J_per_token"],
                                               tok_s_per_kW=base_P[c]["rom"][k]["tok_s_per_kW"],
                                               static_w=base_P[c]["rom"][k]["static_w"]),
                           measured=dict(J_per_token=meas_P[c]["rom"][k]["J_per_token"],
                                         tok_s_per_kW=meas_P[c]["rom"][k]["tok_s_per_kW"],
                                         static_w=meas_P[c]["rom"][k]["static_w"]),
                           measured_controller_shared=dict(J_per_token=sh_P[c]["rom"][k]["J_per_token"],
                                                           tok_s_per_kW=sh_P[c]["rom"][k]["tok_s_per_kW"],
                                                           static_w=sh_P[c]["rom"][k]["static_w"]),
                           spine_gated_assumed=dict(J_per_token=sp_P[c]["rom"][k]["J_per_token"],
                                                    tok_s_per_kW=sp_P[c]["rom"][k]["tok_s_per_kW"],
                                                    static_w=sp_P[c]["rom"][k]["static_w"]))
                   for k in keys} for c in E.CTX}
    # absolute cross-check: the ledger's per-pair ICG-idle logic (10% clock residual + leakage) vs this element
    import uarch_model as u
    pp = u.pair_power(u.A._env()["clock"])
    out = dict(
        schema="opentallas.rtl.rom_stage_pg_verdict.v1",
        element="S81 pair element core ot_v41_rom_elem_w10 (BF16 0, NB 2, MTP, EARLY, FAST, PP; 4 x ot_rom_4096x274_m8) "
                "as one power domain: ot_v41_rom_elem_q_pg_w10 PG = 1, routed in the q-frame C (510.84 x 126.9 um)",
        exactness=dict(pass_=ex["verdict"]["exact_with_gating"], mutants_detected=ex["verdict"]["mutants_detected"],
                       tail=[r["tail"][-4:] for r in ex["runs"] if r["mutant"] is None][0]),
        power_w=dict(active=st["active"], cg_idle=st["cg_idle"], pg_idle_route=st["pg_idle"],
                     leakage_element_route=leak_full, leakage_ao_route=leak_ao, leakage_domain=leak_dom,
                     header_cells=n_sw, header_area_um2=round(n_sw * SW_AREA_UM2, 1),
                     header_area_frac=round(n_sw * SW_AREA_UM2 / ELEM_AREA_UM2, 4),
                     header_off_leak_w=sw_leak, pg_idle=p_pg, cg_idle_total=p_cg, residual=round(resid, 5),
                     by_class=cls, sched_ctrl_pg_idle_w=ctl, pg_idle_controller_shared=p_pg_shared,
                     residual_controller_shared=round(resid_shared, 5), root_clock_pg_idle_w=rc,
                     pg_idle_spine_gated=p_pg_spine, residual_spine_gated=round(resid_spine, 5)),
        wake=dict(rtl_req_to_ready_cycles_max=wmax, rtl_restore_cycles_max=rmax, domain_cap_pf=round(c_f * 1e12, 1),
                  rush_limit_a=round(i_busy, 4), charge_ns=round(t_charge_ns, 3), wake_cycles=wake_cycles,
                  wake_ns=round(wake_cycles * CLK_NS, 2), wake_energy_nj=round(e_wake * 1e9, 4),
                  break_even_us=round(t_be_us, 4)),
        windows=windows,
        ledger_cross_check=dict(ledger_pair_icg_idle_w=round(0.10 * pp["clock"] + pp["leak"], 6),
                                measured_pair_cg_idle_w=p_cg, measured_pair_pg_idle_w=p_pg),
        reprice=dict(logic_residual_measured=round(resid, 5), serdes_residual_assumed=0.10,
                     effective_PG_RES=round(res_eff, 5), effective_PG_RES_controller_shared=round(res_eff_sh, 5),
                     effective_PG_RES_spine_gated=round(res_eff_sp, 5),
                     rows=reprice),
        assumptions=[
            "header switch = ASAP7 INVx4 pull-up (W18 SWITCH_CELL, R_on 912.5 ohm; no characterised ASAP7 switch cell); "
            "off leakage = Liberty INVx4 (A=1) leakage; ring sized for 10 mV at the W18 busy-pair current",
            "wake rush current limited to the busy current (wake di/dt within the normal-operation envelope); ring "
            "segment ack modelled in RTL as 8 cycles (cfg_step 16) and stretched to the charge time when longer",
            "domain capacitance: cell-internal/diffusion = input-pin total (ASSUMED); ROM arrays from the compiler model",
            "SerDes lane-gating residual 10% stays ASSUMED (not measured here)"])
    (d / "verdict.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("power_w", "wake", "windows")}, indent=1))
    print(json.dumps(out["reprice"]["rows"]["1M"], indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cap")
    p.add_argument("--routed", required=True)
    p.add_argument("--out", required=True)
    q = sub.add_parser("verdict")
    q.add_argument("--dir", default=str(ROOT / "results/rtl/rom_stage_power_gating_20261004"))
    a = ap.parse_args()
    return cap(a) if a.cmd == "cap" else verdict(a)


if __name__ == "__main__":
    raise SystemExit(main())
