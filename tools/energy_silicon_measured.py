#!/usr/bin/env python3
"""Energy and equal-silicon comparison for BOTH targets, rebuilt on the measured scoreboard (owner, 2026-10-04).

Supersedes results/uarch/ds_energy_silicon_authoritative_20261004 (INVALID: it used the old 2,466-2,532 tok/s DS ROM
rate and an ASSUMED 10% power-gating residual; measured are 1,386 AR / 2,744 MTP and a 35.4% residual).

Regenerable: every per-user rate is read from results/arch/measured_scoreboard/scoreboard.json at run time, the ROM
element power from the gate-level records (results/rtl/rom_stage_power_gating_20261004/verdict.json, and the gated
stage clock spine results/rtl/rom_stage_spine_gate_20261004/verdict.json when present), third-party figures from
results/external/registry.json.  Re-run whenever the scoreboard or those records change:

    python3 tools/energy_silicon_measured.py            # writes results/arch/energy_silicon_measured/{energy_silicon.json,README.md}
    python3 tools/energy_silicon_measured.py --check    # fails if the committed outputs are stale

Comparisons (per-user decode at the target context: DeepSeek-V4.1 1M, Qwen3-8B 8K):
  DS:   DS ROM (S81) vs DS HBM accelerator (Tomahawk Ultra protocol), 8x B200 as the GPU reference row
  Qwen: Qwen ROM (TP4, 4 reticle dies) vs Qwen HBM accelerator (TP4 iso-silicon and TP2 same-silicon) vs H100 / B200,
        each die a single reticle; equal total silicon counts HBM DRAM on both sides.
Every term carries a status: measured / composed_from_measured / partial / published / modelled / assumed.  A row's
status is its weakest term; the terms that keep a row from being measured are listed under `unvalidated`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/energy_silicon_measured"
SB_PATH = "results/arch/measured_scoreboard/scoreboard.json"
PG_PATH = "results/rtl/rom_stage_power_gating_20261004/verdict.json"
SPINE_PATH = "results/rtl/rom_stage_spine_gate_20261004/verdict.json"         # rejected (no CDC), history
CDC_PATH = "results/rtl/rom_stage_spine_cdc_20261004/verdict.json"            # successor: synchronised crossings
REG_PATH = "results/external/registry.json"
INTEG_PATH = "results/uarch/hbm_accelerator_integration_20261004/model.json"
RECHECK_PATH = "results/uarch/dsrom_c_recheck_20261004/model.json"
# adopted system (CLAUDE DS-RACK 2026-10-06; DS-RACK85 2026-10-06): the rack record packs the adopted element frame
# (default QELEM, QX 10 at f183.60: 85 stages, 340 layer dies, 2,304 pairs a layer die) + 12 head + 36 Engram table
# + 52 DP1-EP5 draft dies; HBM stacks sized to need (scenario C rule).  The recheck's S81 (324 layer, 368 dies / 452
# stacks at 8 head dies) is history; only its priced die area is still read (via the scoreboard)
RACK_PATH = "results/arch/dsrom_s81_rack_20261006/rack.json"
ECON_PATH = "results/uarch/economics.json"
COMPOSE_PATH = "results/arch/three_machine_compose/compose.json"
DS_COMPOSITION = "results/rtl/dsrom_recovery_20261004/composition.json"     # info.r8_reprice: the headline's stage count
QHBM_P8191 = "results/rtl/qwen_hbmacc_p8191_20261004/measured_composition.json"
RANK = ["measured", "composed_from_measured", "published", "partial", "off_target_context", "modelled", "assumed",
        "unvalidated", "pending"]


def load(p):
    return json.loads((ROOT / p).read_text())


def worst(*st):
    return max(st, key=RANK.index)


class Term:
    """A number with its status and source."""
    def __init__(self, value, status, src, note=""):
        self.value, self.status, self.src, self.note = value, status, src, note

    def d(self):
        return dict(value=self.value, status=self.status, src=self.src, **({"note": self.note} if self.note else {}))


def sb():
    f = load(SB_PATH)["figures"]

    def get(key):
        v = f[key]
        return Term(v["value"], v["status"], f"{SB_PATH} figures['{key}'] <- {v.get('path')} ({v.get('pointer')})",
                    v.get("note", ""))
    return f, get


def registry():
    return {e["id"]: e for e in load(REG_PATH)["entries"]}


# ---------------------------------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------------------------------
def element_power():
    """Per element pair (S81 element core, routed q-frame, OpenSTA TT, routed SPEF + gate-level SAIF) at 1.2 GHz."""
    v = load(PG_PATH)
    pw = v["power_w"]
    out = dict(active=Term(pw["active"]["total"], "measured", f"{PG_PATH} power_w.active.total"),
               cg_idle=Term(pw["cg_idle_total"], "measured", f"{PG_PATH} power_w.cg_idle_total"),
               pg_idle=Term(pw["pg_idle"], "measured", f"{PG_PATH} power_w.pg_idle (header ring off-leakage modelled: INVx4)"),
               residual=Term(pw["residual"], "measured", f"{PG_PATH} power_w.residual"),
               wake_ns=Term(v["wake"]["wake_ns"], "measured", f"{PG_PATH} wake.wake_ns"),
               exact=v["exactness"]["pass_"])
    cp = ROOT / CDC_PATH
    sp = ROOT / SPINE_PATH
    if cp.exists():
        c = json.loads(cp.read_text())
        ok = c.get("verdict", "").startswith("ADOPT")
        st = "measured" if ok else "unvalidated"
        k1 = c["power_w"]["stage_k1"]
        n = c["power_w"]["decomposition"]["per_element_at_n"]["2417"]
        out["spine"] = dict(
            pg_idle=Term(k1["pg_idle"], st, f"{CDC_PATH} power_w.stage_k1.pg_idle (one-element stage, routed, gate level)"),
            residual=Term(k1["residual"], st, f"{CDC_PATH} power_w.stage_k1.residual"),
            pg_idle_ctl_shared=Term(n["pg_idle_w"], st, f"{CDC_PATH} power_w.decomposition.per_element_at_n['2417'].pg_idle_w",
                                    "per element of a 2,417-element stage from the measured 1- and 4-element stages"),
            residual_ctl_shared=Term(n["residual"], st, f"{CDC_PATH} power_w.decomposition.per_element_at_n['2417'].residual"),
            pg_idle_ctl_aon_shared=Term(None, st, "superseded by the measured stage decomposition"),
            residual_ctl_aon_shared=Term(None, st, "superseded by the measured stage decomposition"),
            wake_ns=Term(c["wake"]["wake_ns"], st, f"{CDC_PATH} wake.wake_ns"),
            verdict=c.get("verdict"))
    elif sp.exists():
        s = json.loads(sp.read_text())
        ok = s.get("verdict", "").startswith("ADOPT")
        st = "measured" if ok else "unvalidated"
        out["spine"] = dict(
            pg_idle=Term(s["power_w"]["pg_idle_spine_gated"], st, f"{SPINE_PATH} power_w.pg_idle_spine_gated"),
            residual=Term(s["power_w"]["residual_spine_gated_measured"], st, f"{SPINE_PATH} power_w.residual_spine_gated_measured"),
            pg_idle_ctl_shared=Term(s["power_w"].get("pg_idle_spine_gated_controller_shared"), worst(st, "modelled"),
                                    f"{SPINE_PATH} power_w.pg_idle_spine_gated_controller_shared",
                                    "measured controller power divided over the stage's elements (one controller per stage)"),
            residual_ctl_shared=Term(s["power_w"].get("residual_spine_gated_controller_shared"), worst(st, "modelled"),
                                     f"{SPINE_PATH} power_w.residual_spine_gated_controller_shared"),
            pg_idle_ctl_aon_shared=Term(s["power_w"].get("pg_idle_spine_gated_controller_and_aon_shared"),
                                        worst(st, "modelled"),
                                        f"{SPINE_PATH} power_w.pg_idle_spine_gated_controller_and_aon_shared",
                                        "controller AND its always-on clock branch divided over the stage's elements"),
            residual_ctl_aon_shared=Term(s["power_w"].get("residual_spine_gated_controller_and_aon_shared"),
                                         worst(st, "modelled"),
                                         f"{SPINE_PATH} power_w.residual_spine_gated_controller_and_aon_shared"),
            wake_ns=Term(s["wake"]["wake_ns"], st, f"{SPINE_PATH} wake.wake_ns"),
            verdict=s.get("verdict"))
    else:
        out["spine"] = None
    return out


def dram_mm2():
    f = load(INTEG_PATH)["fairness"]["DRAM_mm2_per_stack_sourced"]
    return Term(f["bound_8hi"], "published", f"{INTEG_PATH} fairness.DRAM_mm2_per_stack_sourced.bound_8hi", f["source"])


# ---------------------------------------------------------------------------------------------------------------------
# row arithmetic
# ---------------------------------------------------------------------------------------------------------------------
def silicon(logic_dies, die_mm2, stacks, dram, switches=0, switch_mm2=None):
    logic = logic_dies * die_mm2.value
    sw = switches * (switch_mm2.value if switch_mm2 else 0.0)
    terms = [die_mm2, dram] + ([switch_mm2] if switches else [])
    return dict(logic_dies=logic_dies, die_mm2=die_mm2.d(), logic_mm2=round(logic, 1), stacks=stacks,
                dram_mm2=round(stacks * dram.value, 1), switch_chips=switches, switch_mm2=round(sw, 1),
                total_mm2=round(logic + stacks * dram.value + sw, 1), status=worst(*(t.status for t in terms)))


def energy_row(rate: Term, static_w: float, static_status: str, dyn_j: Term, unvalidated: list, note=""):
    p = static_w + dyn_j.value * rate.value
    st = worst(rate.status, static_status, dyn_j.status)
    return dict(tok_s=round(rate.value, 1), rate_status=rate.status, static_w=round(static_w, 1),
                dynamic_w=round(dyn_j.value * rate.value, 1), system_w=round(p, 1), J_per_token=round(p / rate.value, 4),
                tok_s_per_kW=round(rate.value / p * 1e3, 2), status=st, unvalidated=unvalidated, note=note)


# ---------------------------------------------------------------------------------------------------------------------
# DeepSeek-V4.1 (1M)
# ---------------------------------------------------------------------------------------------------------------------
def ds(get, reg, el, dram):
    rk = load(RACK_PATH)
    cnt, geo = rk["counts"], rk["geometry"]
    S = cnt["stages"]
    r8 = load(DS_COMPOSITION)["info"]["r8_reprice"]
    assert cnt["layer"] == 4 * S == geo["layer_dies"], (cnt, geo)
    assert S == r8["stages"] and cnt["layer"] == r8["layer_dies"] and geo["field_geom"] == r8["geom"], \
        f"rack record packs {S} stages / {cnt['layer']} layer dies, the headline composition {r8['stages']} / {r8['layer_dies']}"
    layer_dies, draft_dies, stacks = cnt["layer"], cnt["draft"], rk["stacks"]["total"]
    total_dies = cnt["dies"]
    pairs = geo["pairs_per_layer_die"]                         # adopted q-element frame (S81: 2,417)
    sys.path.insert(0, str(ROOT / "tools"))
    import dsrom_return_storage_hbm as R                       # the C1 ledger constants (isopower history 8bb540cd1)
    C1 = R.C1
    serdes_w = R.LAYER_SERDES_W
    ledger_logic_w = C1["die_static_excl_hbm_w"] - serdes_w     # 19.596 W: hub + field leak, ICG-only
    import uarch_model as u
    ledger_field_leak = u.PAIR_W["placed_pairs"] * u.PAIR_W["idle_icg"]
    hub_w = ledger_logic_w - ledger_field_leak                  # the non-field logic the ledger charges (modelled)
    stack_idle = 2.8                                            # configs/hardware/power_scenarios.json (ASSUMED band)
    ar, mtp, ar_us = get("ds_rom.ar_tok_s_1m"), get("ds_rom.mtp_tok_s_1m"), get("ds_rom.ar_us_1m")
    tau = get("ds_rom.tau")
    dyn_ar = Term(0.1186, "modelled", "C1 model dynamic J/token at 1M (isopower history 8bb540cd1; dsrom_return_storage_hbm)")
    dyn_mtp = Term(round(0.1704 * 3.649 / tau.value, 4), "modelled",
                   "C1 MTP dynamic 170.4 mJ/token at tau 3.649 x 3.649 / tau (work per step schedule-invariant)")
    ht_die_w = (C1["head_w"] + C1["table_w"]) / 44            # C1 ledger: one W a head or table die (8 + 36 there)
    head_w, table_w = round(cnt["head"] * ht_die_w, 1), round(cnt["table"] * ht_die_w, 1)

    def static(pg: bool, f: float, pair_pg_w: float, hub_res: float):
        """System static W: layer dies (field measured per pair, hub modelled, SerDes modelled) + head + table + stacks."""
        field_cg = pairs * el["cg_idle"].value
        if not pg:
            layer = field_cg + hub_w + serdes_w
        else:
            layer = (pairs * (f * el["cg_idle"].value + (1 - f) * pair_pg_w) + hub_w * (f + (1 - f) * hub_res)
                     + serdes_w * (f + (1 - f) * 0.10))
        return (layer_dies + draft_dies) * layer + head_w + table_w + stacks * stack_idle, dict(
            layer_die_w=round(layer, 3), field_w=round(pairs * (el["cg_idle"].value if not pg else
                                                                 f * el["cg_idle"].value + (1 - f) * pair_pg_w), 3),
            hub_w=round(hub_w if not pg else hub_w * (f + (1 - f) * hub_res), 3),
            serdes_w=round(serdes_w if not pg else serdes_w * (f + (1 - f) * 0.10), 3),
            head_w=head_w, table_w=table_w, stacks_idle_w=round(stacks * stack_idle, 1),
            draft_dies_w=round(draft_dies * layer, 1))

    t_ar_us = ar_us.value
    wake_us = el["wake_ns"].value * 1e-3
    f_ar = min(1.0, 1.0 / S + wake_us / t_ar_us)
    f_mtp = min(1.0, 7.0 / S)
    unv_common = ["hub/scan/control logic static per layer die (ledger 19.6 W less its field leakage, modelled)",
                  "SerDes 30.6 W per layer die and its 10% lane-gating residual (ASSUMED)",
                  f"head dies {head_w} W and Engram table dies {table_w} W, never gated (modelled)",
                  f"HBM stack idle 2.8 W x {stacks} stacks (ASSUMED band 1.2-6.4 W; scenario C rule: 4 on 32 scan "
                  f"+ 12 head dies, 1 on the other {layer_dies - rk['stacks']['scan_dies']} layer dies, 0 on table and draft dies, {RACK_PATH})",
                  f"element power of the S81 pair (gate level) charged to each of the {pairs:,} q-element frame pairs a "
                  f"layer die (QX 10 element idle power not measured; ASSUMED transfer)",
                  f"{draft_dies} DP1-EP5 draft dies charged a layer die's static and gated like one (ASSUMED)",
                  "dynamic energy per token (C1 model)"]
    rows, ledgers = {}, {}
    st_icg, lg = static(False, 1.0, 0.0, 1.0)
    ledgers["icg"] = lg
    rows["ar_b1_icg"] = energy_row(ar, st_icg, "modelled", dyn_ar, unv_common, "per-pair ICG only (measured clock-gated idle pair)")
    rows["mtp_b1_icg"] = energy_row(mtp, st_icg, "modelled", dyn_mtp, unv_common)
    variants = [("pg_measured", el["pg_idle"], el["residual"], el["wake_ns"])]
    if el["spine"]:
        variants.append(("pg_spine", el["spine"]["pg_idle"], el["spine"]["residual"], el["spine"]["wake_ns"]))
        if el["spine"]["pg_idle_ctl_shared"].value is not None:
            variants.append(("pg_spine_ctl_shared", el["spine"]["pg_idle_ctl_shared"], el["spine"]["residual_ctl_shared"],
                             el["spine"]["wake_ns"]))
        if el["spine"]["pg_idle_ctl_aon_shared"].value is not None:
            variants.append(("pg_spine_ctl_aon_shared", el["spine"]["pg_idle_ctl_aon_shared"],
                             el["spine"]["residual_ctl_aon_shared"], el["spine"]["wake_ns"]))
    for name, ppg, res, wk in variants:
        fa = min(1.0, 1.0 / S + wk.value * 1e-3 / t_ar_us)
        unv = unv_common + [f"element residual {res.value:.4f} applied to the hub logic (ASSUMED transfer)",
                            f"MTP wavefront keeps 7 of {S} stages powered (ASSUMED)"]
        s_ar, lg = static(True, fa, ppg.value, res.value)
        ledgers[f"{name}_ar_b1"] = dict(lg, active_fraction=round(fa, 5))
        rows[f"ar_b1_{name}"] = energy_row(ar, s_ar, worst("modelled", ppg.status), dyn_ar, unv,
                                           f"stage power gating, active fraction 1/S + wake/T = {fa:.4f}; pair PG idle "
                                           f"{ppg.value * 1e3:.3f} mW ({ppg.status})")
        s_m, lg = static(True, f_mtp, ppg.value, res.value)
        ledgers[f"{name}_mtp_b1"] = dict(lg, active_fraction=round(f_mtp, 5))
        rows[f"mtp_b1_{name}"] = energy_row(mtp, s_m, worst("modelled", ppg.status), dyn_mtp, unv, "f = 7/S")
    sil = silicon(total_dies, get("ds_rom.die_mm2"), stacks, dram)
    rom = dict(design=f"DS ROM S{S}, q-element frame {geo['field_geom']} ({layer_dies} layer + {cnt['head']} head + {cnt['table']} Engram table + {draft_dies} "
                      f"draft dies, 2 dies a package; {stacks} HBM3E stacks)", stages=S, layer_dies=layer_dies,
               head_dies=cnt["head"], table_dies=cnt["table"], draft_dies=draft_dies, stacks=stacks,
               total_dies=total_dies, pairs_per_layer_die=pairs,
               geometry=dict(field_geom=geo["field_geom"], src=f"{RACK_PATH} geometry ({geo['src']}); {DS_COMPOSITION} "
                                                               f"info.r8_reprice stages / layer_dies agree"), rates=dict(ar=ar.d(), mtp=mtp.d(), ar_us=ar_us.d()),
               silicon=sil, power=rows, static_ledgers=ledgers,
               element=dict(active_w=el["active"].d(), cg_idle_w=el["cg_idle"].d(), pg_idle_w=el["pg_idle"].d(),
                            residual=el["residual"].d(), wake_ns=el["wake_ns"].d(),
                            spine=None if not el["spine"] else {k: (v.d() if isinstance(v, Term) else v)
                                                                 for k, v in el["spine"].items()}),
               idle_window_1m=dict(token_us=round(t_ar_us, 3), stage_window_us=round(t_ar_us / S, 3),
                                   idle_us=round(t_ar_us * (1 - 1 / S), 3), wake_us=round(wake_us, 4),
                                   wake_fits=wake_us < t_ar_us * (1 - 1 / S)))
    # ---- DS HBM accelerator (Tomahawk Ultra + our protocol)
    integ = load(INTEG_PATH)["fairness"]
    acc = next(e for e in integ["ds_system_counts"] if e["id"] == "ds_1")["study_point"]
    ipb = integ["iso_power_average_bounds"][0]
    h_static = Term(ipb["static_w"], "modelled", f"{INTEG_PATH} fairness.iso_power_average_bounds[0].static_w (gated, transferred)")
    h_dyn = Term(ipb["dynamic_J_per_token"], "modelled", f"{INTEG_PATH} fairness.iso_power_average_bounds[0].dynamic_J_per_token")
    import ds_energy_silicon_authoritative as E                # HBM MTP step energy from the consolidation sweep (JSON only)
    hs = E.hbm_sweep()
    h_dyn_mtp = Term(round(hs["mtp_step_b1_J"] / tau.value, 4), "modelled",
                     "results/uarch/consolidation.json hbm.v41_sweep TP-96 x4 MTP batch-1 gated step energy / tau")
    tsw = reg["new:tomahawk5_power"]
    sw_w = Term(500.0, "assumed", f"{REG_PATH} new:tomahawk5_power ('{tsw['quote']}'), charged always-on as an upper bound")
    sw_n = 8
    sw_mm2 = Term(800.0, "assumed", "Tomahawk Ultra die area unpublished; reticle-class 800 mm2 (ASSUMED)")
    h_ar, h_mtp = get("hbm_ds.ar_tok_s"), get("hbm_ds.mtp_tok_s")
    unv_h = ["gated static 5,367.7 W and dynamic J/token are the study's transferred constants (no gate-level power of "
             "any HBM-accelerator block)", f"{sw_n} switch chips x 500 W (ASSUMED upper bound, registry new:tomahawk5_power)",
             "HBM-accelerator rate is partial (vendor-budget collectives modelled)"]
    hrows = dict(ar_b1=energy_row(h_ar, h_static.value + sw_n * sw_w.value, "assumed", h_dyn, unv_h),
                 ar_b1_no_switch=energy_row(h_ar, h_static.value, "modelled", h_dyn, unv_h[:1] + unv_h[2:],
                                            "switch chips not charged (sensitivity)"),
                 mtp_b1=energy_row(h_mtp, h_static.value + sw_n * sw_w.value, "assumed", h_dyn_mtp, unv_h))
    hbm = dict(design="DS HBM accelerator (96 dies TP-96, 4 stacks a die, Tomahawk Ultra tier + our protocol)",
               rates=dict(ar=h_ar.d(), mtp=h_mtp.d()),
               silicon=silicon(96, Term(acc["logic_mm2"] / 96, "modelled", f"{INTEG_PATH} ds_system_counts[ds_1].logic_mm2 / 96"),
                               acc["stacks"], dram, sw_n, sw_mm2),
               power=hrows, terms=dict(static=h_static.d(), dyn_ar=h_dyn.d(), dyn_mtp=h_dyn_mtp.d(), switch_w=sw_w.d()))
    # ---- 8x B200 reference row (modelled tier-2 rate; measured-cited decode draw)
    b_ar, b_mtp = get("gpu_ds.b200x8_tier2_ar_1m"), get("gpu_ds.b200x8_tier2_mtp_1m")
    draw = reg["roofline:b200_decode_draw_w"]
    g_w = 8 * draw["value"] + 2 * sw_w.value
    zero = Term(0.0, "measured", "whole-board decode draw includes dynamic")
    gpu = dict(design="8x B200 (DeepSeek-V4.1-Flash, tier-2 model rate)", rates=dict(ar=b_ar.d(), mtp=b_mtp.d()),
               silicon=silicon(16, Term(800.0, "assumed", f"{REG_PATH} sct:r-dgxb200 (two reticle-limited dies a GPU); "
                                                         "800 mm2 a die ASSUMED"), 64, dram, 2, sw_mm2),
               power=dict(ar_b1=energy_row(b_ar, g_w, "published", zero,
                                           ["8 x 689 W measured decode draw (registry roofline:b200_decode_draw_w) + 2 "
                                            "NVSwitch x 500 W (ASSUMED)", "B200 V4.1 rate is a tier-2 model"]),
                          mtp_b1=energy_row(b_mtp, g_w, "published", zero, ["as ar_b1; MTP 1.94x sensitivity"])))
    return dict(rom=rom, hbm_accel=hbm, b200x8=gpu)


# ---------------------------------------------------------------------------------------------------------------------
# Qwen3-8B (8K)
# ---------------------------------------------------------------------------------------------------------------------
def qwen(F, get, reg, dram):
    econ = load(ECON_PATH)["qwen_rom"]["energy"]
    # Qwen ROM AR = the committed three-machine composition (measured full36+head token + adopted levers), read through
    # the scoreboard figure that points at it; the pointer is resolved here so a stale scoreboard cannot pass silently.
    q_ar, q_ds = get("qwen_rom.ar_tok_s_8k_composed"), get("qwen_rom.dspark_tok_s_8k_stream4")
    q_fig = F["qwen_rom.ar_tok_s_8k_composed"]
    assert q_fig["path"] == COMPOSE_PATH, q_fig["path"]
    q_rec = load(COMPOSE_PATH)
    for k in q_fig["pointer"].split("."):
        q_rec = q_rec[k]
    assert q_rec == q_ar.value, f"scoreboard qwen_rom.ar_tok_s_8k_composed {q_ar.value} != {COMPOSE_PATH} {q_fig['pointer']} {q_rec}"
    q_static = Term(econ["static_w_total"], "modelled", f"{ECON_PATH} qwen_rom.energy.static_w_total (4 dies; ungated clock)")
    q_dyn = Term(round(econ["dynamic_mJ_per_token"] * 1e-3, 5), "modelled", f"{ECON_PATH} qwen_rom.energy.dynamic_mJ_per_token")
    integ = load(INTEG_PATH)["fairness"]
    qc = integ["qwen_ROM_option_C_area"]["central"]
    unv_q = ["Qwen ROM static 200 W and dynamic 76.6 mJ/token are the uarch model (no gate-level power of the Qwen ROM "
             "tile; the DS element measurement does not transfer: KV SRAM slice + split-tree node)",
             "AR rate is the composed record (measured full36+head P8191 token + adopted levers, "
             f"{COMPOSE_PATH} qwen_rom.AR_tok_s); power is modelled, evaluated at that rate",
             "Operating mode is plain AR; DSpark rows are off-mode sensitivity, not the selected operating mode"]
    rom = dict(design="Qwen3-8B ROM, TP4: 4 reticle dies, 4 HBM stacks a die (KV)",
               rates=dict(ar=q_ar.d(), dspark=q_ds.d()),
               silicon=silicon(4, get("qwen_rom.die_area_mm2"), qc["stacks"], dram),
               silicon_with_dspark_drafter=silicon(4, get("qwen_rom.dspark_die_mm2_model"), qc["stacks"], dram),
               power=dict(ar=energy_row(q_ar, q_static.value, q_static.status, q_dyn, unv_q),
                          dspark=energy_row(q_ds, q_static.value, q_static.status, q_dyn,
                                            unv_q + ["DSpark dynamic per accepted token taken = AR dynamic (ASSUMED; KV "
                                                     "bytes shared across a step's positions)", "tau not measured in RTL"])),
               terms=dict(static=q_static.d(), dyn=q_dyn.d()))
    # ---- Qwen HBM accelerator at P8191 (scoreboard if it carries the P8191 figure, else the committed record)
    def qhbm(key_sb, ptr):
        if key_sb in F:
            return get(key_sb)
        d = load(QHBM_P8191)
        v = d
        for k in ptr:
            v = v[k]
        return Term(v, "composed_from_measured", f"{QHBM_P8191} {'.'.join(ptr)} (not yet on the scoreboard)")
    h4 = qhbm("hbm_qwen.ar_tok_s_p8191_tp4", ["b_TP4_iso_silicon", "w224_adopted", "ar_tok_s"])
    h2 = qhbm("hbm_qwen.ar_tok_s_p8191_tp2", ["a_TP2_same_silicon", "w224_adopted", "ar_tok_s"])
    hs = get("hbm_qwen.spec_dflash_model")
    out = {}
    for name, rate, blk, dies in (("tp4_iso_silicon", h4, integ["qwen_area"]["iso_total_silicon_with_rom"], 4),
                                  ("tp2_same_silicon", h2, integ["qwen_area"]["same_silicon_as_ablation"], 2)):
        pm = blk["ar_power_model"]
        model_rate = pm["system_w"] / pm["J_per_token"]
        dyn = Term(round((pm["system_w"] - pm["static_w"]) / model_rate, 5), "modelled",
                   f"{INTEG_PATH} qwen_area ar_power_model (system - static) / model rate")
        a = blk["area_sensitivities"]["central"]
        unv = ["HBM accelerator power is the integration model (no gate-level power)",
               "vehicle area/route/SS-FF not qualified (sram_macro_fit_and_routes_qualified = false)"]
        out[name] = dict(design=f"Qwen HBM accelerator {name.split('_')[0].upper()} ({dies} reticle dies, {a['stacks']} stacks)",
                         rates=dict(ar=rate.d()),
                         silicon=silicon(dies, Term(a["logic_mm2"] / dies, "modelled", f"{INTEG_PATH} qwen_area logic_mm2 / dies"),
                                         a["stacks"], dram),
                         power=dict(ar=energy_row(rate, pm["static_w"], "modelled", dyn, unv)),
                         terms=dict(static_w=pm["static_w"], dyn=dyn.d()))
    pm = integ["qwen_area"]["same_silicon_as_ablation"]["dflash_power_model"]
    out["tp2_same_silicon"]["rates"]["spec_dflash_model"] = hs.d()
    out["tp2_same_silicon"]["power"]["spec_dflash_model"] = energy_row(
        hs, pm["static_w"], "modelled", Term(round((pm["system_w"] - pm["static_w"]) / hs.value, 5), "modelled",
                                             f"{INTEG_PATH} dflash_power_model"), ["DFlash rate and power are models"])
    # ---- GPUs (single-reticle H100; B200 = two reticle dies)
    h1, h8 = get("gpu_qwen.h100_tp1_fp8_decode_8k"), get("gpu_qwen.h100_tp8_fp8_decode_8k")
    r200 = reg["sct:r-h200"]
    tdp = Term(700.0, "published", f"{REG_PATH} sct:r-h200 (GH100 SXM board 'Up to 700W'; H100 decode draw not measured: "
                                   "TDP is an upper bound)")
    idle = Term(71.8, "published", f"{REG_PATH} sct:r-h100-idle (bare idle 71.8 W; a lower bound)")
    die = Term(814.0, "published", f"{REG_PATH} sct:r-h200 ('a die size of 814 mm 2')")
    zero = Term(0.0, "measured", "board power includes dynamic")
    gpu = dict(
        h100_tp1=dict(design="1x H100 SXM FP8 (vLLM, measured 8K)", rates=dict(ar=h1.d()),
                      silicon=silicon(1, die, 5, dram) | dict(stacks_note="5 HBM3 stacks (80 GB) ASSUMED"),
                      power=dict(ar_tdp=energy_row(h1, tdp.value, tdp.status, zero, ["board power at TDP (upper bound)"]),
                                 ar_idle_floor=energy_row(h1, idle.value, idle.status, zero, ["bare idle (lower bound)"]))),
        h100_tp8=dict(design="8x H100 SXM FP8 TP8 (vLLM, measured 8K)", rates=dict(ar=h8.d()),
                      silicon=silicon(8, die, 40, dram),
                      power=dict(ar_tdp=energy_row(h8, 8 * tdp.value, tdp.status, zero, ["8 boards at TDP (upper bound)"]))))
    b_df = get("gpu_qwen.b200_sglang_dflash_math500")
    b_w = Term(reg["roofline:b200_decode_draw_w"]["value"], "published", f"{REG_PATH} roofline:b200_decode_draw_w")
    gpu["b200_dflash"] = dict(design="1x B200 SGLang DFlash (published, MATH-500, not 8K)", rates=dict(spec=b_df.d()),
                              silicon=silicon(2, Term(800.0, "assumed", "B200 two reticle-limited dies (sct:r-dgxb200), "
                                                                        "800 mm2 a die ASSUMED"), 8, dram),
                              power=dict(spec=energy_row(b_df, b_w.value, b_w.status, zero,
                                                         ["689 W measured decode draw (cited)", "published DFlash rate at short context"])))
    return dict(rom=rom, hbm_accel=out, gpu=gpu)


# ---------------------------------------------------------------------------------------------------------------------
# equal silicon
# ---------------------------------------------------------------------------------------------------------------------
def iso(ref_name, ref_total, designs):
    """Every design replicated to the reference's total silicon (logic + DRAM + switches): batch-1 per-user rate is
    unchanged, concurrent batch-1 users = replicas. This is an independent batch-1 replication lower bound,
    not a saturated large-batch throughput result; per-user tok/s per 1,000 mm2 and per logic reticle."""
    out = {}
    for name, (sil, rate, label) in designs.items():
        rep = ref_total / sil["total_mm2"]
        out[name] = dict(rate_label=label, per_user_tok_s=rate, total_mm2=sil["total_mm2"], logic_dies=sil["logic_dies"],
                         per_user_tok_s_per_1000mm2=round(rate / sil["total_mm2"] * 1e3, 4),
                         replicas_at_ref_silicon=round(rep, 3), batch1_users_at_ref_silicon=round(rep, 2),
                         aggregate_b1_tok_s_integer_replicas=round(int(rep) * rate, 1),
                         aggregate_b1_tok_s_fractional=round(rep * rate, 1))
    return dict(reference=ref_name, reference_total_mm2=ref_total,
                aggregate_scope="Independent batch-1 replication lower bound; not saturated large-batch throughput",
                rows=out)


def ledger_fix():
    """Part (2): the uarch_model ledger's clock-gated idle ROM pair, before (10% ASSUMED residual of the ungated pair
    clock) and after (the measured residual clock, PAIR_CG_IDLE), at the ledger clock and at 1.2 GHz."""
    sys.path.insert(0, str(ROOT / "tools"))
    import uarch_model as u
    out = {}
    for name, clk in (("ledger_clock", u.A._env()["clock"]), ("1.2GHz", 1.2e9)):
        pp = u.pair_power(clk)
        out[name] = dict(clock_hz=clk, before_w=round(u.PG["cg_residual"] * pp["clock"] + pp["leak"], 6),
                         after_w=round(u.field_cg_residual(clk) * pp["clock"] + pp["leak"], 6),
                         field_cg_residual_after=round(u.field_cg_residual(clk), 5))
    out["measured_w"] = u.PAIR_CG_IDLE["total_w"]
    out["src"] = u.PAIR_CG_IDLE["src"]
    out["where"] = ("tools/uarch_model.py _die_energy (v41_static_power policies 1-3) and cons_v41_rom (the ICG die static "
                    "keeps the measured residual clock of every idle pair instead of leakage only)")
    return out


def build():
    F, get = sb()
    reg = registry()
    el = element_power()
    dram = dram_mm2()
    D = ds(get, reg, el, dram)
    Q = qwen(F, get, reg, dram)
    r, h, g = D["rom"], D["hbm_accel"], D["b200x8"]
    sp_ok = bool(el["spine"]) and str(el["spine"]["verdict"]).startswith("ADOPT")
    best = "ar_b1_pg_measured"
    for k in ("ar_b1_pg_spine", "ar_b1_pg_spine_ctl_shared", "ar_b1_pg_spine_ctl_aon_shared"):
        if sp_ok and k in r["power"]:
            best = k                                      # only an adopted spine may determine the energy verdict
    bestm = best.replace("ar_b1", "mtp_b1")
    ds_cmp = dict(
        per_user_ar_rom_over_hbm=round(r["rates"]["ar"]["value"] / h["rates"]["ar"]["value"], 4),
        per_user_mtp_rom_over_hbm=round(r["rates"]["mtp"]["value"] / h["rates"]["mtp"]["value"], 4),
        J_per_token_ar_hbm_over_rom=dict((k, round(h["power"]["ar_b1"]["J_per_token"] / r["power"][k]["J_per_token"], 4))
                                         for k in r["power"] if k.startswith("ar_b1")),
        J_per_token_mtp_hbm_over_rom=dict((k, round(h["power"]["mtp_b1"]["J_per_token"] / r["power"][k]["J_per_token"], 4))
                                          for k in r["power"] if k.startswith("mtp_b1")),
        J_per_token_ar_hbm_no_switch_over_rom=dict(
            (k, round(h["power"]["ar_b1_no_switch"]["J_per_token"] / r["power"][k]["J_per_token"], 4))
            for k in r["power"] if k.startswith("ar_b1")),
        best_rom_policy=best, spine_adopted=sp_ok,
        iso_silicon=iso("DS ROM", r["silicon"]["total_mm2"], dict(
            rom_ar=(r["silicon"], r["rates"]["ar"]["value"], "AR"), rom_mtp=(r["silicon"], r["rates"]["mtp"]["value"], "MTP"),
            hbm_ar=(h["silicon"], h["rates"]["ar"]["value"], "AR"), hbm_mtp=(h["silicon"], h["rates"]["mtp"]["value"], "MTP"),
            b200x8_ar=(g["silicon"], g["rates"]["ar"]["value"], "AR"), b200x8_mtp=(g["silicon"], g["rates"]["mtp"]["value"], "MTP"))))
    qr, qh, qg = Q["rom"], Q["hbm_accel"], Q["gpu"]
    q_cmp = dict(
        per_user_ar_rom_over_hbm_tp4=round(qr["rates"]["ar"]["value"] / qh["tp4_iso_silicon"]["rates"]["ar"]["value"], 4),
        per_user_ar_rom_over_h100_tp1=round(qr["rates"]["ar"]["value"] / qg["h100_tp1"]["rates"]["ar"]["value"], 4),
        per_user_ar_rom_over_h100_tp8=round(qr["rates"]["ar"]["value"] / qg["h100_tp8"]["rates"]["ar"]["value"], 4),
        J_per_token_ar=dict(rom=qr["power"]["ar"]["J_per_token"], hbm_tp4=qh["tp4_iso_silicon"]["power"]["ar"]["J_per_token"],
                            hbm_tp2=qh["tp2_same_silicon"]["power"]["ar"]["J_per_token"],
                            h100_tp1_tdp=qg["h100_tp1"]["power"]["ar_tdp"]["J_per_token"],
                            h100_tp1_idle_floor=qg["h100_tp1"]["power"]["ar_idle_floor"]["J_per_token"],
                            h100_tp8_tdp=qg["h100_tp8"]["power"]["ar_tdp"]["J_per_token"]),
        iso_silicon=iso("Qwen ROM (4 reticle dies + 16 stacks)", qr["silicon"]["total_mm2"], dict(
            rom_ar=(qr["silicon"], qr["rates"]["ar"]["value"], "AR"),
            rom_dspark=(qr["silicon"], qr["rates"]["dspark"]["value"], "DSpark"),
            hbm_tp4_ar=(qh["tp4_iso_silicon"]["silicon"], qh["tp4_iso_silicon"]["rates"]["ar"]["value"], "AR"),
            hbm_tp2_ar=(qh["tp2_same_silicon"]["silicon"], qh["tp2_same_silicon"]["rates"]["ar"]["value"], "AR"),
            h100_tp1_ar=(qg["h100_tp1"]["silicon"], qg["h100_tp1"]["rates"]["ar"]["value"], "AR"),
            h100_tp8_ar=(qg["h100_tp8"]["silicon"], qg["h100_tp8"]["rates"]["ar"]["value"], "AR"),
            b200_dflash=(qg["b200_dflash"]["silicon"], qg["b200_dflash"]["rates"]["spec"]["value"], "DFlash (published)"))))
    failure_path = "results/rtl/rom_stage_spine_cdc_20261004/failure_E1/terminal.json"
    current_spine = dict(status="pending", residual=None, energy_win_claim=False)
    if (ROOT / failure_path).exists() and not (ROOT / CDC_PATH).exists():
        current_spine.update(status="unknown: E1 global route failed; no final ODB or measured power",
                             source=failure_path)
    elif (ROOT / CDC_PATH).exists():
        current_spine.update(status="adopted" if sp_ok else "unvalidated", source=CDC_PATH)
    return dict(schema="opentallas.arch.energy_silicon_measured.v1",
                current_spine_measurement=current_spine,
                supersedes="results/uarch/ds_energy_silicon_authoritative_20261004 (INVALID: old 2,466-2,532 tok/s DS ROM "
                           "rate, ASSUMED 10% power-gating residual)",
                inputs=dict(scoreboard=SB_PATH, scoreboard_commit=load(SB_PATH).get("generated_from_commit"),
                            element_power=PG_PATH, spine=CDC_PATH if (ROOT / CDC_PATH).exists() else
                            (SPINE_PATH if (ROOT / SPINE_PATH).exists() else "pending"),
                            registry=REG_PATH, integration=INTEG_PATH, recheck=RECHECK_PATH, economics=ECON_PATH,
                            rack=RACK_PATH, ds_composition=DS_COMPOSITION),
                status_rank=RANK, ledger_fix=ledger_fix(), deepseek_1m=D, deepseek_compare=ds_cmp, qwen_8k=Q, qwen_compare=q_cmp)


# ---------------------------------------------------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------------------------------------------------
def fmt(x, n=1):
    return f"{x:,.{n}f}"


def readme(d):
    D, Q, dc, qc = d["deepseek_1m"], d["qwen_8k"], d["deepseek_compare"], d["qwen_compare"]
    r, h, g = D["rom"], D["hbm_accel"], D["b200x8"]
    el = r["element"]
    L = ["# Energy and equal silicon, both targets, on measured inputs (2026-10-04)", "",
         f"Generated by `tools/energy_silicon_measured.py` from `{d['inputs']['scoreboard']}` (scoreboard commit "
         f"`{d['inputs']['scoreboard_commit']}`), the gate-level element power `{d['inputs']['element_power']}`, the "
         f"spine record `{d['inputs']['spine']}` and `{d['inputs']['registry']}`. Re-run it whenever the scoreboard "
         "or those records change; `--check` fails if this record is stale.", "",
         f"**Supersedes** {d['supersedes']}. Its \"ROM wins energy 1.6-2.3x\" verdict is withdrawn.", "",
         "**Current spine PG:** " + d["current_spine_measurement"]["status"] +
         ". No measured residual or energy-win credit is assigned to failed E1. Earlier PG/spine rows retain their historical provenance.", "",
         "Status of every row = its weakest term (measured < composed_from_measured < published < partial < modelled < "
         "assumed). The `unvalidated` list in the JSON names the terms that are not measured.", "",
         "**Scope (2026-10-07):** every rate here is a candidate composition, not a closed rate. The DS ROM rows are on the "
         "historical 85-stage full-rate-BF geometry; the actual 1,792-pair half-rate-BF mapping has 98 or 120 stages and "
         "392 or 480 layer dies, and is not priced here. Qwen ROM physical closure was reopened on 2026-10-07. The HBM rows "
         "carry no die closure cost. See `results/arch/unified_composition_20261007/ledger.json`.", "",
         "## DeepSeek-V4.1 at 1M (batch 1)", "",
         "| Design | Per-user tok/s | Rate status | Static W | Dynamic W | System W | J/token | tok/s per kW | Row status |",
         "|---|---:|---|---:|---:|---:|---:|---:|---|"]
    for name, blk in (("DS ROM", r), ("DS HBM accelerator", h), ("8x B200", g)):
        for k, row in blk["power"].items():
            L.append(f"| {name} {k} | {fmt(row['tok_s'])} | {row['rate_status']} | {fmt(row['static_w'])} | "
                     f"{fmt(row['dynamic_w'])} | {fmt(row['system_w'])} | {row['J_per_token']:.3f} | "
                     f"{fmt(row['tok_s_per_kW'])} | {row['status']} |")
    sp = el["spine"]
    L += ["", "ROM element (S81 pair, gate level, TT, 1.2 GHz): active "
          f"{el['active_w']['value'] * 1e3:.1f} mW, clock-gated idle {el['cg_idle_w']['value'] * 1e3:.3f} mW, power-gated "
          f"idle {el['pg_idle_w']['value'] * 1e3:.3f} mW (residual {el['residual']['value'] * 100:.1f}%), wake "
          f"{el['wake_ns']['value']:.1f} ns." + (
              f" Gated spine: PG idle {sp['pg_idle']['value'] * 1e3:.3f} mW, residual {sp['residual']['value'] * 100:.2f}% "
              f"({sp['residual']['status']}; verdict {sp['verdict']})" + (
                  f"; per element of a 2,417-element stage sharing one controller {sp['residual_ctl_shared']['value'] * 100:.2f}% "
                  f"({sp['residual_ctl_shared']['src']})"
                  if sp.get('residual_ctl_shared') and sp['residual_ctl_shared']['value'] is not None else "") + "."
              if sp else " Gated spine: pending (results/rtl/rom_stage_spine_gate_20261004)."),
          f"Idle window at 1M: token {fmt(r['idle_window_1m']['token_us'], 1)} us, stage window "
          f"{r['idle_window_1m']['stage_window_us']:.2f} us, wake {r['idle_window_1m']['wake_us'] * 1e3:.1f} ns "
          f"(fits: {r['idle_window_1m']['wake_fits']}).", "",
          f"Per-user: ROM / HBM = {dc['per_user_ar_rom_over_hbm']:.3f} (AR), {dc['per_user_mtp_rom_over_hbm']:.3f} (MTP).", "",
          "HBM J/token over ROM J/token (>1 = ROM better):", ""]
    for k, v in dc["J_per_token_ar_hbm_over_rom"].items():
        L.append(f"- AR, ROM {k}: {v:.3f} (switch not charged: {dc['J_per_token_ar_hbm_no_switch_over_rom'][k]:.3f})")
    for k, v in dc["J_per_token_mtp_hbm_over_rom"].items():
        L.append(f"- MTP, ROM {k}: {v:.3f}")
    L += ["", "### Equal total silicon (logic + HBM DRAM at 1,089 mm2 a stack + switch chips), DS ROM as reference", "",
          dc["iso_silicon"]["aggregate_scope"] + ".", "",
          "| Design | Rate | Per-user tok/s | Total mm2 | Per-user tok/s per 1,000 mm2 | Replicas at ROM silicon | Batch-1 aggregate (integer replicas) |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for k, v in dc["iso_silicon"]["rows"].items():
        L.append(f"| {k} | {v['rate_label']} | {fmt(v['per_user_tok_s'])} | {fmt(v['total_mm2'], 0)} | "
                 f"{v['per_user_tok_s_per_1000mm2']:.3f} | {v['replicas_at_ref_silicon']:.2f} | "
                 f"{fmt(v['aggregate_b1_tok_s_integer_replicas'])} |")
    qr, qh, qg = Q["rom"], Q["hbm_accel"], Q["gpu"]
    L += ["", "## Qwen3-8B at 8K (batch 1; every logic die one reticle)", "",
          "| Design | Rate | Per-user tok/s | Rate status | Logic dies | Total mm2 | System W | J/token | tok/s per kW | Row status |",
          "|---|---|---:|---|---:|---:|---:|---:|---:|---|"]
    def qrow(name, blk):
        for k, row in blk["power"].items():
            L.append(f"| {name} | {k} | {fmt(row['tok_s'])} | {row['rate_status']} | {blk['silicon']['logic_dies']} | "
                     f"{fmt(blk['silicon']['total_mm2'], 0)} | {fmt(row['system_w'])} | {row['J_per_token']:.3f} | "
                     f"{fmt(row['tok_s_per_kW'])} | {row['status']} |")
    qrow("Qwen ROM TP4", qr)
    qrow("Qwen HBM accel TP4 (iso silicon)", qh["tp4_iso_silicon"])
    qrow("Qwen HBM accel TP2 (same silicon)", qh["tp2_same_silicon"])
    qrow("1x H100", qg["h100_tp1"])
    qrow("8x H100 TP8", qg["h100_tp8"])
    qrow("1x B200 DFlash", qg["b200_dflash"])
    L += ["", f"Per-user AR: ROM / HBM TP4 = {qc['per_user_ar_rom_over_hbm_tp4']:.3f}; ROM / 1x H100 = "
          f"{qc['per_user_ar_rom_over_h100_tp1']:.2f}; ROM / 8x H100 TP8 = {qc['per_user_ar_rom_over_h100_tp8']:.2f}.", "",
          "### Equal total silicon, Qwen ROM as reference", "",
          qc["iso_silicon"]["aggregate_scope"] + ".", "",
          "| Design | Rate | Per-user tok/s | Logic dies (reticles) | Total mm2 | Per-user tok/s per 1,000 mm2 | Replicas at ROM silicon | Batch-1 aggregate (integer replicas) |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for k, v in qc["iso_silicon"]["rows"].items():
        L.append(f"| {k} | {v['rate_label']} | {fmt(v['per_user_tok_s'])} | {v['logic_dies']} | {fmt(v['total_mm2'], 0)} | "
                 f"{v['per_user_tok_s_per_1000mm2']:.3f} | {v['replicas_at_ref_silicon']:.2f} | "
                 f"{fmt(v['aggregate_b1_tok_s_integer_replicas'])} |")
    lf = d["ledger_fix"]
    L += ["", "## Ledger fix (tools/uarch_model.py)", "",
          f"Clock-gated idle ROM pair: the ledger charged {lf['ledger_clock']['before_w'] * 1e3:.2f} mW (10% ASSUMED residual "
          f"of the ungated pair clock + leakage) at {lf['ledger_clock']['clock_hz'] / 1e9:.3f} GHz; measured "
          f"{lf['measured_w'] * 1e3:.3f} mW at 1.2 GHz ({lf['src']}). The ledger now charges "
          f"{lf['ledger_clock']['after_w'] * 1e3:.2f} mW at its clock and {lf['1.2GHz']['after_w'] * 1e3:.2f} mW at 1.2 GHz "
          f"(was {lf['1.2GHz']['before_w'] * 1e3:.2f}): {lf['where']}."]
    L += ["", "## Verdict (regenerated with the numbers above)", ""]
    L += verdict_lines(d)
    L += ["", "## Still modelled (why rows are not `measured`)", "",
          "- DS ROM: hub/scan/control static, SerDes and its lane-gating residual, head and Engram table dies, stack idle, "
          "dynamic energy (C1 model); the element's measured residual is transferred to the hub logic.",
          "- DS HBM accelerator: every power term (study constants; no gate-level power), switch chips (ASSUMED 500 W, "
          "800 mm2); rate partial (vendor-budget collectives).",
          "- Qwen ROM: static and dynamic power are the uarch model (no Qwen tile gate-level power).",
          "- Qwen HBM accelerator: power from the integration model; area/route not qualified.",
          "- GPUs: H100 power is a TDP upper bound / idle lower bound (decode draw not measured); B200 rows use the "
          "cited 689 W decode draw; the DS B200 rate is a tier-2 model.", ""]
    return "\n".join(L)


def verdict_lines(d):
    dc, qc = d["deepseek_compare"], d["qwen_compare"]
    r, h = d["deepseek_1m"]["rom"], d["deepseek_1m"]["hbm_accel"]
    out = []
    pm = r["power"].get("ar_b1_pg_measured")
    best = dc["best_rom_policy"]
    rb = r["power"][best]
    ratio_m = dc["J_per_token_ar_hbm_over_rom"]["ar_b1_pg_measured"]
    ratio_b = dc["J_per_token_ar_hbm_over_rom"][best]
    fa = "the ROM is faster" if dc["per_user_ar_rom_over_hbm"] > 1 else "the HBM accelerator is faster"
    out.append(f"- **DS, per user:** {fa} (AR): ROM/HBM {dc['per_user_ar_rom_over_hbm']:.2f}x AR, "
               f"{dc['per_user_mtp_rom_over_hbm']:.2f}x MTP.")
    win = lambda x: "ROM better" if x > 1 else "HBM better"
    out.append(f"- **DS, energy at batch 1 (AR):** ROM with the measured {r['element']['residual']['value'] * 100:.1f}% residual {pm['J_per_token']:.2f} J/token "
               f"against HBM {h['power']['ar_b1']['J_per_token']:.2f} (switch charged): HBM/ROM = {ratio_m:.2f} ({win(ratio_m)})"
               + ("" if best == "ar_b1_pg_measured" else
                  f"; with the gated spine ({best}, " + ("ADOPTED" if dc["spine_adopted"] else "UNVALIDATED: spine REJECTED physically")
                  + f") ROM {rb['J_per_token']:.2f} J/token, HBM/ROM = {ratio_b:.2f} ({win(ratio_b)})")
               + f". Without the switch charge HBM/ROM = {dc['J_per_token_ar_hbm_no_switch_over_rom']['ar_b1_pg_measured']:.2f}.")
    out.append(f"- **DS, energy MTP:** HBM/ROM = {dc['J_per_token_mtp_hbm_over_rom']['mtp_b1_pg_measured']:.2f} (measured "
               "residual)" + ("" if best == "ar_b1_pg_measured" else
                              f", {dc['J_per_token_mtp_hbm_over_rom'][best.replace('ar_b1', 'mtp_b1')]:.2f} (gated spine)") + ".")
    iso = dc["iso_silicon"]["rows"]
    out.append(f"- **DS, equal silicon:** per-user AR per 1,000 mm2 ROM {iso['rom_ar']['per_user_tok_s_per_1000mm2']:.2f} "
               f"vs HBM {iso['hbm_ar']['per_user_tok_s_per_1000mm2']:.2f}; at the ROM's silicon the HBM accelerator fits "
               f"{iso['hbm_ar']['replicas_at_ref_silicon']:.2f} replicas.")
    qi = qc["iso_silicon"]["rows"]
    qj = qc["J_per_token_ar"]
    out.append(f"- **Qwen, per user (AR):** ROM {qi['rom_ar']['per_user_tok_s']:,.0f} vs HBM TP4 "
               f"{qi['hbm_tp4_ar']['per_user_tok_s']:,.0f} ({qc['per_user_ar_rom_over_hbm_tp4']:.2f}x) vs 1x H100 "
               f"{qi['h100_tp1_ar']['per_user_tok_s']:,.0f} ({qc['per_user_ar_rom_over_h100_tp1']:.1f}x).")
    out.append(f"- **Qwen, energy (AR, modelled power):** ROM {qj['rom']:.3f} J/token, HBM TP4 {qj['hbm_tp4']:.3f}, "
               f"1x H100 {qj['h100_tp1_idle_floor']:.2f}-{qj['h100_tp1_tdp']:.2f} (idle floor - TDP bound).")
    out.append(f"- **Qwen, equal silicon:** per-user AR per 1,000 mm2 ROM {qi['rom_ar']['per_user_tok_s_per_1000mm2']:.3f}, "
               f"HBM TP4 {qi['hbm_tp4_ar']['per_user_tok_s_per_1000mm2']:.3f}, HBM TP2 "
               f"{qi['hbm_tp2_ar']['per_user_tok_s_per_1000mm2']:.3f}, 1x H100 {qi['h100_tp1_ar']['per_user_tok_s_per_1000mm2']:.3f}.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = build()
    js = json.dumps(d, indent=1) + "\n"
    md = readme(d) + "\n"
    if a.check:
        ok = (OUT / "energy_silicon.json").exists() and (OUT / "energy_silicon.json").read_text() == js \
            and (OUT / "README.md").read_text() == md
        print("energy_silicon_measured: " + ("current" if ok else "STALE: re-run tools/energy_silicon_measured.py"))
        return 0 if ok else 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "energy_silicon.json").write_text(js)
    (OUT / "README.md").write_text(md)
    print("\n".join(verdict_lines(d)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
