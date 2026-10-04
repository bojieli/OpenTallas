#!/usr/bin/env python3
"""DeepSeek-V4.1 energy, power and equal-silicon comparison on AUTHORITATIVE inputs (owner request 2026-10-04).

Designs: DS ROM (S81 + wavefront verify, measured draft), DS HBM accelerator (Tomahawk Ultra + our protocol,
tools/uarch_model.py defaults), the GPU-organised ablation (measured H100 NVLS), the GPU-faithful R0 row (measured H100
grid.sync + fenced collectives) and the 8x B200 tier-2 model row.  Rates come from uarch_model.hbm_switch_latency_
authoritative() and gpu_tier2(); silicon and power from the committed ledgers named in SRC.  Every constant that is not
a committed record or a sourced figure is in ASSUMED and labelled.  Writes results/uarch/ds_energy_silicon_
authoritative_20261004/model.json.  Usage: python3 tools/ds_energy_silicon_authoritative.py [--check]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as u                                    # noqa: E402
from hbm_accelerator_model import _load_study              # noqa: E402

OUT = ROOT / "results/uarch/ds_energy_silicon_authoritative_20261004/model.json"
CTX = {"1M": "1048576", "200K": "200000"}
TAU = u.TAU_DS        # third-party published DSpark gamma-5 tau (tools/third_party_tau.py); 4.159 self-measured SUPERSEDED

SRC = dict(
    rates="tools/uarch_model.py hbm_switch_latency_authoritative() (record results/uarch/hbm_switch_latency_authoritative_20261004)",
    rom_ar="results/rtl/dsrom_wavefront_verify_20261004/record.json",
    rom_draft="results/rtl/dsrom_dspark_step_slices_20261004/composition.json (MEASURED draft, main dae91947c)",
    rom_l1l2="results/rtl/dsrom_dspark_l1l2_20261004/expected.json (EXPECTED projection, 2a235a9fe)",
    rom_s81="results/uarch/dsrom_c_recheck_20261004/model.json priced.S81_ragged_RD64_replicated",
    rom_power="tools/dsrom_c_recheck.py + tools/dsrom_return_storage_hbm.py C1/scenario_c (isopower history 8bb540cd1)",
    hbm_power="results/uarch/consolidation.json hbm.v41_sweep TP-96 4-stack row (gated); "
              "results/uarch/hbm_accelerator_study_20261003/ladder_model.py DS_HBM_STATIC_GATED_W / DS_HBM_DYN_J",
    hbm_power_crosscheck="results/uarch/economics.json v41_hbm (legacy DAG, ungated static 6,498.5 W)",
    hbm_silicon="results/uarch/hbm_accelerator_integration_20261004/model.json fairness (96 x 340.5 mm2, 384 stacks)",
    dram_mm2="results/uarch/hbm_accelerator_integration_20261004/model.json fairness.DRAM_mm2_per_stack_sourced "
             "(Micron HBM3E 11 x 11 mm cube: 8-Hi 1,089 / 12-Hi 1,573 mm2 core+base bound)",
    dram_power="configs/hardware/power_scenarios.json memory (idle 2.8 W/stack ASSUMED band 1.2-6.4; path 104.88 pJ/B MEASURED A100 SC'25)",
    gpu="tools/uarch_model.py gpu_tier2() / gpu_economics() (8x B200 tier-2 model; 689 W measured decode draw per GPU)",
    h100="results/measured/h100_nvls_20261004/README.md (NVLS collectives, grid.sync 1.097 us; no DS-V4.1 run on H100)")

ASSUMED = dict(
    switch_chip_mm2=dict(value=800.0, range=[500.0, 850.0],
                         basis="ASSUMED: Tomahawk Ultra / NVSwitch die area unpublished; 51.2T 5 nm monolithic "
                               "(Tomahawk 5 class) taken as reticle-class 800 mm2"),
    switch_chip_w=dict(value=500.0, range=[300.0, 500.0],
                       basis="ASSUMED by analogy: Broadcom Tomahawk 5 (51.2T, N5) 'consumes less than 500 W' "
                             "(gazettabyte.com/?p=145716); Tomahawk Ultra / NVSwitch power unpublished; full-load "
                             "figure charged as always-on (upper end)"),
    hbm_tier_switch_chips=dict(value=8, basis="authoritative record: 'about 8 Tomahawk Ultra chips in one tier' "
                                              "(also charged to the NVLS-class ablation, ASSUMED same count)"),
    b200_nvswitch_chips=dict(value=2, basis="ASSUMED: HGX B200 baseboard carries 2 NVLink switch chips"),
    b200_die_mm2=dict(value=800.0, basis="repo record ds_5 (16 dies x 800 mm2, integration fairness) -- ASSUMED die area"),
    rom_mtp_step_energy=dict(basis="ASSUMED: ROM MTP dynamic energy per STEP = C1 170.4 / 164.5 mJ per token x tau 3.649 "
                                   "(work per step is schedule-invariant; the wavefront changes overlap, not work); "
                                   f"divided by tau {TAU:g}"),
    rom_mtp_pg_active=dict(basis="ASSUMED: wavefront MTP keeps 6 positions + 1 pre-woken stage active: f = 7/S"),
    rom_pg_residual=dict(value=0.10, basis="ASSUMED (scenario C): gated logic and gated SerDes keep 10%"),
    rom_mtp_saturation=dict(basis="ASSUMED: saturated MTP step occupancy = C1 non-draft occupancy (tau 3.649 / C1 mtp_sat "
                                  "- 0.1173 x C1 AR) + the MEASURED draft, i.e. the draft serialises on the head"),
    hbm_200k_dyn=dict(basis="ASSUMED: HBM 200K dynamic J/token = 1M value - (ROM 1M - ROM 200K dynamic) = -16.3 mJ "
                            "(same model, same KV/index HBM bytes at the same pJ/B on both designs)"),
    hbm_saturation=dict(basis="consolidation TP-96 sweep saturated rows (GPU-organised resource model); the accelerator's "
                              "batch/union/credit calendar is NOT composed (integration record saturation_gap), so the "
                              "same saturated aggregate is used for accelerator, ablation and R0 -- HISTORICAL MODEL"),
    hbm_200k_mtp_sat=dict(basis="ASSUMED: no 200K MTP saturated row exists; the 1M value is carried (lower bound)"),
    gpu_200k_sat=dict(basis="ASSUMED: B200 200K saturated not modelled; 1M value carried (lower bound)"),
    hbm_endpoint_serdes=dict(basis="endpoint SerDes area inside the 340.5 mm2 die and power inside the ledger's "
                                   "'links' static (33.1 W/die); not separately re-priced"))

LAYER_DIE_W, SERDES_W, HEAD_W, TABLE_W, STACK_IDLE_W, PG_RES = 50.196, 30.6, 738.5, 3324.4, 2.8, 0.10
ROM_DYN_AR = {"1M": 0.1186, "200K": 0.1023}                 # J/token (C1, isopower 8bb540cd1)
ROM_DYN_MTP_C1 = {"1M": 0.1704, "200K": 0.1645}             # J/emitted token at tau 3.649
C1 = dict(tau=3.649, mtp_sat={"1M": 35262.3, "200K": 35702.4}, ar={"1M": 2347.4, "200K": 2445.0}, draft=0.1173)
ROM_AR_SAT = 80833.5                                        # head-bound 12.37 us; 33 users << 216 users/stack capacity
HBM_ST = 5367.717140558499                                  # gated static, 96 dies + 384 stacks (no switch)
HBM_DYN_AR = (10593.0 - 6498.5) / 2801.8                    # 1.4614 J/token
SW = None                                                   # filled from consolidation


def load(p):
    return json.loads((ROOT / p).read_text())


def rates():
    a = u.hbm_switch_latency_authoritative()
    m, _, _, _ = _load_study(u.ROOT)
    rows = {(r["ctx"], r["design"]): r for r in a["rows"] if r["authoritative_default"]}
    abl_tu = {r["ctx"]: r for r in a["rows"] if r["design"] == "accelerator_firm_switch" and r["primary"]
              and r["scenario"] == "tomahawk_ultra_protocol"}
    dft = load("results/rtl/dsrom_dspark_step_slices_20261004/composition.json")["full_shape"]["ctx"]
    n = a["collective_counts"]["w19_pass"]["total"]; nd = a["collective_counts"]["draft_assumed"]
    acc = a["designs"]["accelerator_firm_switch"]["replaced"]
    d1 = u.w19_transport_us(1, "tomahawk_ultra_protocol") - u.w19_transport_us(1, "w15", "kp4")
    d6 = u.w19_transport_us(6, "tomahawk_ultra_protocol") - u.w19_transport_us(6, "w15", "kp4")
    out, checks = {}, {}
    for c, rk in CTX.items():
        k = 1.0 if c == "1M" else m.CTX_200K_RATIO
        rv = a["rom"][c]
        r_acc, r_meas = rows[(c, "accelerator_firm_switch")], rows[(c, "accelerator_measured_composition")]
        r_abl, r_r0 = rows[(c, "ablation_w19")], rows[(c, "gpu_faithful_r0")]
        # second derivation of the accelerator row from its parts
        ar2 = acc["ar"] * k + d1
        st2 = (acc["ver"] + acc["draft"]) * k + d6 + d1 * nd / n
        checks[c] = dict(acc_ar_us=[r_acc["ar_us"], round(ar2, 2)], acc_mtp_step_us=[r_acc["mtp_step_us"], round(st2, 2)])
        draft_comp = acc["draft"] * k + d1 * nd / n
        sens = {}
        for v, key in (("as_built", "as_built_chain"), ("l1_fused", "fused_head")):
            ratio = dft[rk][key]["draft_us"] / dft[rk]["ar_us"]
            step = r_acc["mtp_step_us"] - draft_comp + ratio * r_acc["ar_us"]
            sens[v] = dict(rom_draft_over_ar=round(ratio, 4), hbm_draft_us=round(ratio * r_acc["ar_us"], 2),
                           step_us=round(step, 2), mtp_tok_s=round(TAU * 1e6 / step, 1))
        g = 1.0 / u.gpu_tier2_v41_ctx(int(rk))
        t2 = {x["design"]: x for x in u.gpu_tier2()}["DeepSeek-V4.1-Flash on 8x B200, calibrated"]
        out[c] = dict(
            rom=dict(ar=rv["ar_tok_s"], mtp_as_built=rv["mtp_as_built_tok_s"], mtp_l1_fused=rv["mtp_fused_head_tok_s"],
                     mtp_l1l2_expected=rv["mtp_l1l2_rom_read_k5_tok_s"],
                     draft_us=dict(as_built=dft[rk]["as_built_chain"]["draft_us"], l1_fused=dft[rk]["fused_head"]["draft_us"])),
            hbm_accel=dict(ar=r_acc["ar_tok_s"], mtp_pending_draft=r_acc["mtp_tok_s"], hbm_draft_us_estimate=round(draft_comp, 2),
                           mtp_sens_rom_ratio_as_built=sens["as_built"]["mtp_tok_s"],
                           mtp_sens_rom_ratio_l1_fused=sens["l1_fused"]["mtp_tok_s"], sensitivity=sens),
            hbm_accel_measured_comp=dict(ar=r_meas["ar_tok_s"], mtp_pending_draft=r_meas["mtp_tok_s"]),
            ablation_nvls=dict(ar=r_abl["ar_tok_s"], mtp=r_abl["mtp_tok_s"]),
            gpu_faithful_r0=dict(ar=r_r0["ar_tok_s"], mtp=r_r0["mtp_tok_s"]),
            b200x8=dict(ar=round(g, 1), mtp=round(g * t2["spec_tokens_s"] / t2["tokens_s"], 1),
                        mtp_basis=f"existing 1.94x B200 MTP sensitivity (not DSpark tau {TAU:g})"))
    return out, checks, a


def silicon(dram_mm2=1089.0, rom_stacks=452):
    sw_mm2 = ASSUMED["switch_chip_mm2"]["value"]
    def tot(logic, stacks, switches):
        d = dict(logic_mm2=round(logic, 1), stacks=stacks, dram_mm2=round(stacks * dram_mm2, 1),
                 switch_chips=switches, switch_mm2=switches * sw_mm2)
        d["total_mm2"] = round(d["logic_mm2"] + d["dram_mm2"] + d["switch_mm2"], 1)
        return d
    hbm = tot(96 * 340.5, 384, ASSUMED["hbm_tier_switch_chips"]["value"])
    return dict(rom=tot(368 * 839.24, rom_stacks, 0),
                rom_alt_head_table_786=tot(324 * 839.24 + 44 * 786.23, rom_stacks, 0),
                hbm_accel=hbm, ablation_nvls=hbm, gpu_faithful_r0=hbm,
                b200x8=tot(16 * ASSUMED["b200_die_mm2"]["value"], 64, ASSUMED["b200_nvswitch_chips"]["value"]))


def hbm_sweep():
    r = next(x for x in load("results/uarch/consolidation.json")["hbm"]["v41_sweep"]
             if x["dies"] == 96 and x["stacks_per_die"] == 4)
    tau0 = 3.649
    ar_sat = r["ar"]["saturated"]["aggregate_tokens_s"]
    dyn_sat = (r["ar"]["saturated"]["gated_system_w"] - HBM_ST) / ar_sat
    m_b1 = r["mtp"]["batch1"]
    step_b1 = (m_b1["gated_system_w"] - HBM_ST) / m_b1["aggregate_tokens_s"] * tau0
    m_s = r["mtp"]["saturated"]
    steps_s = m_s["aggregate_tokens_s"] / tau0
    step_sat = (m_s["gated_system_w"] - HBM_ST) / steps_s
    eco = load("results/uarch/economics.json")["v41_hbm"]
    eb = eco["mtp"]["rows"][0]
    step_b1_eco = (eb["system_w"] - eco["energy"]["static_w_total"]) / eb["aggregate_tokens_s"] * eco["mtp"]["tau"]
    es = max(eco["ar"]["rows"], key=lambda x: x["aggregate_tokens_s"])
    dyn_sat_eco = (es["system_w"] - eco["energy"]["static_w_total"]) / es["aggregate_tokens_s"]
    gated_b1_check = (r["ar"]["batch1"]["gated_mJ"] * 1e-3 - HBM_DYN_AR) * r["ar"]["batch1"]["aggregate_tokens_s"]
    return dict(ar_sat_1M=ar_sat, ar_sat_200K=load("results/uarch/dsrom_return_storage_hbm_20261003/model.json")
                ["scenario_bases"]["hbm_comparator"]["200000"]["best"],
                dyn_ar_sat_J=dyn_sat, mtp_step_b1_J=step_b1, mtp_steps_s_sat=steps_s, mtp_step_sat_J=step_sat,
                capacity_users_1m=r["capacity_users_1m"], ar_sat_batch=r["ar"]["saturated"]["batch"],
                ar_sat_per_user=r["ar"]["saturated"]["per_user_tokens_s"], mtp_sat_batch=m_s["batch"],
                mtp_sat_per_user_tau3649=m_s["per_user_tokens_s"],
                crosscheck=dict(mtp_step_b1_J=[round(step_b1, 4), round(step_b1_eco, 4), "consolidation gated vs economics legacy"],
                                dyn_ar_sat_J=[round(dyn_sat, 4), round(dyn_sat_eco, 4), "consolidation gated vs economics legacy"],
                                static_gated_W=[round(HBM_ST, 1), round(gated_b1_check, 1),
                                                "ladder constant vs consolidation gated_mJ x rate - dyn"]))


def power(R):
    sw_w = ASSUMED["switch_chip_w"]["value"]
    hs = hbm_sweep()
    S, layer = 81, 324
    rom_icg = layer * LAYER_DIE_W + HEAD_W + TABLE_W + 452 * STACK_IDLE_W

    def rom_pg(f):
        return rom_icg - layer * LAYER_DIE_W * (1 - f) * (1 - PG_RES)
    tab, chk = {}, {}
    for c in CTX:
        r = R[c]
        dyn_ar = ROM_DYN_AR[c]
        e_step_rom = ROM_DYN_MTP_C1[c] * C1["tau"]
        dyn_mtp = e_step_rom / TAU
        base_occ = C1["tau"] / C1["mtp_sat"][c] * 1e6 - C1["draft"] * 1e6 / C1["ar"][c]
        rom_mtp_sat = {v: TAU * 1e6 / (base_occ + r["rom"]["draft_us"][v]) for v in ("as_built", "l1_fused")}
        f_ar_sat = min(1.0, ROM_AR_SAT / r["rom"]["ar"] / S + 1 / S)
        f_mtp_sat = 1.0          # ASSUMED: saturated MTP keeps every stage active (no gating credit)
        hbm_dyn_ar = HBM_DYN_AR - (ROM_DYN_AR["1M"] - ROM_DYN_AR[c])
        hbm_kvd = ROM_DYN_AR["1M"] - ROM_DYN_AR[c]
        hbm_dyn_mtp_b1 = hs["mtp_step_b1_J"] / TAU - hbm_kvd
        hbm_dyn_ar_sat = hs["dyn_ar_sat_J"] - hbm_kvd
        hbm_dyn_mtp_sat = hs["mtp_step_sat_J"] / TAU - hbm_kvd
        hbm_sw = ASSUMED["hbm_tier_switch_chips"]["value"] * sw_w
        hbm_sat_ar = hs["ar_sat_1M"] if c == "1M" else hs["ar_sat_200K"]
        hbm_sat_mtp = hs["mtp_steps_s_sat"] * TAU
        gpu_w = 8 * 689.0 + ASSUMED["b200_nvswitch_chips"]["value"] * sw_w
        ge = u.gpu_economics()["v41"]

        def row(rate, static, dyn, note="", switch_w=0.0):
            p = static + switch_w + dyn * rate
            return dict(tok_s=round(rate, 1), static_w=round(static + switch_w, 1), switch_w=switch_w,
                        dynamic_w=round(dyn * rate, 1), system_w=round(p, 1), J_per_token=round(p / rate, 4),
                        J_per_token_check=round((static + switch_w) / rate + dyn, 4),
                        tok_s_per_kW=round(rate / p * 1e3, 1), note=note)
        t = {}
        # ---- ROM S81
        t["rom"] = dict(
            ar_b1_icg=row(r["rom"]["ar"], rom_icg, dyn_ar, "ICG only"),
            ar_b1_pg=row(r["rom"]["ar"], rom_pg(2 / S), dyn_ar, "stage power gating, f = 2/S (ASSUMED 10% residual)"),
            mtp_as_built_b1_icg=row(r["rom"]["mtp_as_built"], rom_icg, dyn_mtp),
            mtp_as_built_b1_pg=row(r["rom"]["mtp_as_built"], rom_pg(7 / S), dyn_mtp, "f = 7/S"),
            mtp_l1_fused_b1_pg=row(r["rom"]["mtp_l1_fused"], rom_pg(7 / S), dyn_mtp, "f = 7/S"),
            ar_sat_icg=row(ROM_AR_SAT, rom_icg, dyn_ar, "head-bound 80,833.5 tok/s, ~33 users"),
            ar_sat_pg=row(ROM_AR_SAT, rom_pg(f_ar_sat), dyn_ar, f"f = {f_ar_sat:.3f}"),
            mtp_as_built_sat_icg=row(rom_mtp_sat["as_built"], rom_pg(f_mtp_sat), dyn_mtp, "draft serialised on head (ASSUMED)"),
            mtp_l1_fused_sat_icg=row(rom_mtp_sat["l1_fused"], rom_pg(f_mtp_sat), dyn_mtp, "draft serialised on head (ASSUMED)"))
        # ---- HBM accelerator / ablation / R0 (same silicon and energy ledger, different per-user rate)
        for name, ar, mtp in (("hbm_accel", r["hbm_accel"]["ar"], r["hbm_accel"]["mtp_pending_draft"]),
                              ("ablation_nvls", r["ablation_nvls"]["ar"], r["ablation_nvls"]["mtp"]),
                              ("gpu_faithful_r0", r["gpu_faithful_r0"]["ar"], r["gpu_faithful_r0"]["mtp"])):
            t[name] = dict(
                ar_b1=row(ar, HBM_ST, hbm_dyn_ar, "gated static + 8 switch chips (ASSUMED)", hbm_sw),
                ar_b1_no_switch=row(ar, HBM_ST, hbm_dyn_ar, "switch not charged (as earlier records)"),
                mtp_b1=row(mtp, HBM_ST, hbm_dyn_mtp_b1, "pending measured draft" if name == "hbm_accel" else "", hbm_sw),
                ar_sat=row(hbm_sat_ar, HBM_ST, hbm_dyn_ar_sat, "HISTORICAL saturated aggregate (see ASSUMED.hbm_saturation)", hbm_sw),
                mtp_sat=row(hbm_sat_mtp, HBM_ST, hbm_dyn_mtp_sat, "1M row carried at 200K" if c == "200K" else "", hbm_sw))
        t["hbm_accel"]["mtp_b1_sens_rom_ratio_as_built"] = row(r["hbm_accel"]["mtp_sens_rom_ratio_as_built"], HBM_ST,
                                                               hbm_dyn_mtp_b1, "HBM draft = ROM measured draft/AR", hbm_sw)
        # ---- 8x B200 (whole-board measured decode draw; energy independent of rate split)
        t["b200x8"] = dict(ar_b1=row(r["b200x8"]["ar"], gpu_w, 0.0, "8 x 689 W measured decode draw + 2 NVSwitch (ASSUMED)"),
                           mtp_b1=row(r["b200x8"]["mtp"], gpu_w, 0.0),
                           ar_sat=row(ge["saturated_tokens_s"], gpu_w, 0.0, f"batch {ge['sat_batch']} (1M row carried at 200K)"
                                      if c == "200K" else f"batch {ge['sat_batch']}"),
                           ar_b1_tdp=row(r["b200x8"]["ar"], 8 * 1200.0 + 2 * sw_w, 0.0, "1,200 W TDP sensitivity"))
        tab[c] = t
        chk[c] = dict(rom_static_icg_kW=[round(rom_icg / 1e3, 2), 21.59, "components vs S81 record"],
                      rom_static_pg_b1_kW=[round(rom_pg(2 / S) / 1e3, 2), 7.32, "components vs S81 record"],
                      rom_b1_pg_tok_s_per_kW=[t["rom"]["ar_b1_pg"]["tok_s_per_kW"],
                                              load(SRC["rom_s81"].split()[0])["priced"]["S81_ragged_RD64_replicated"]["system"][CTX[c]]["b1_AR_tok_s_per_kW_pg"]],
                      rom_sat_icg_tok_s_per_kW=[t["rom"]["ar_sat_icg"]["tok_s_per_kW"],
                                                load(SRC["rom_s81"].split()[0])["priced"]["S81_ragged_RD64_replicated"]["system"][CTX[c]]["best_batch_tok_s_per_kW_icg"]],
                      rom_mtp_sat=dict(base_occupancy_us=round(base_occ, 2), **{k: round(v, 1) for k, v in rom_mtp_sat.items()}),
                      rom_mtp_dyn_J=dict(step_J=round(e_step_rom, 4), per_token=round(dyn_mtp, 4)),
                      hbm_dyn=dict(ar_b1=round(hbm_dyn_ar, 4), mtp_b1=round(hbm_dyn_mtp_b1, 4), ar_sat=round(hbm_dyn_ar_sat, 4),
                                   mtp_sat=round(hbm_dyn_mtp_sat, 4)))
    return tab, chk, hs


def per_area_and_iso(R, A, P):
    out = {}
    for c in CTX:
        r, p = R[c], P[c]
        ra = A["rom"]["total_mm2"]
        rows = {}
        for name, ar, mtp, sat in (
                ("rom", r["rom"]["ar"], r["rom"]["mtp_as_built"], p["rom"]["ar_sat_icg"]["tok_s"]),
                ("hbm_accel", r["hbm_accel"]["ar"], r["hbm_accel"]["mtp_pending_draft"], p["hbm_accel"]["ar_sat"]["tok_s"]),
                ("ablation_nvls", r["ablation_nvls"]["ar"], r["ablation_nvls"]["mtp"], p["ablation_nvls"]["ar_sat"]["tok_s"]),
                ("gpu_faithful_r0", r["gpu_faithful_r0"]["ar"], r["gpu_faithful_r0"]["mtp"], p["gpu_faithful_r0"]["ar_sat"]["tok_s"]),
                ("b200x8", r["b200x8"]["ar"], r["b200x8"]["mtp"], p["b200x8"]["ar_sat"]["tok_s"])):
            a = A[name]["total_mm2"]
            rep = ra / a
            rows[name] = dict(total_mm2=a, per_user_ar_per_1000mm2=round(ar / a * 1e3, 4),
                              per_user_mtp_per_1000mm2=round(mtp / a * 1e3, 4),
                              sat_ar_per_1000mm2=round(sat / a * 1e3, 2),
                              iso_rom_silicon=dict(replicas_fractional=round(rep, 3), replicas_integer=int(rep),
                                                   per_user_ar=ar, per_user_mtp=mtp,
                                                   concurrent_b1_users_fractional=round(rep, 2),
                                                   aggregate_b1_ar_tok_s=round(int(rep) * ar, 1),
                                                   aggregate_sat_ar_tok_s_integer=round(int(rep) * sat, 1),
                                                   aggregate_sat_ar_tok_s_fractional=round(rep * sat, 1)))
        # iso-power: budget = ROM saturated ICG system power
        bud = p["rom"]["ar_sat_icg"]["system_w"]
        iso_p = {}
        for name in ("hbm_accel", "ablation_nvls", "b200x8"):
            w = p[name]["ar_sat"]["system_w"]
            iso_p[name] = dict(budget_w=bud, replica_sat_w=w, replicas_fractional=round(bud / w, 3),
                               aggregate_sat_ar_tok_s=round(bud / w * p[name]["ar_sat"]["tok_s"], 1))
        iso_p["rom"] = dict(budget_w=bud, aggregate_sat_ar_tok_s=p["rom"]["ar_sat_icg"]["tok_s"])
        out[c] = dict(per_area=rows, iso_power_at_rom_sat_icg=iso_p)
    return out


def build():
    R, rchk, auth = rates()
    A = silicon()
    A_sens = dict(rom_420_stacks=silicon(rom_stacks=420)["rom"],
                  dram_12hi_1573=dict((k, silicon(dram_mm2=1573.0)[k]) for k in ("rom", "hbm_accel", "b200x8")),
                  dram_assumed_low_900=dict((k, silicon(dram_mm2=900.0)[k]) for k in ("rom", "hbm_accel", "b200x8")))
    P, pchk, hs = power(R)
    ge = u.gpu_economics()["v41"]
    sat = {c: dict(rom_ar=dict(tok_s=ROM_AR_SAT, users=round(ROM_AR_SAT / R[c]["rom"]["ar"], 1), per_user=R[c]["rom"]["ar"],
                               rule="pipeline fill: every user keeps the batch-1 rate until the head binds"),
                   rom_mtp_as_built=dict(tok_s=P[c]["rom"]["mtp_as_built_sat_icg"]["tok_s"],
                                         users=round(P[c]["rom"]["mtp_as_built_sat_icg"]["tok_s"] / R[c]["rom"]["mtp_as_built"], 2),
                                         per_user=R[c]["rom"]["mtp_as_built"]),
                   hbm_ar=dict(tok_s=P[c]["hbm_accel"]["ar_sat"]["tok_s"], users=hs["ar_sat_batch"],
                               per_user=round(P[c]["hbm_accel"]["ar_sat"]["tok_s"] / hs["ar_sat_batch"], 1),
                               rule="column passes: per-user rate falls with batch (HISTORICAL resource model)"),
                   hbm_mtp=dict(tok_s=P[c]["hbm_accel"]["mtp_sat"]["tok_s"], users=hs["mtp_sat_batch"],
                                per_user=round(P[c]["hbm_accel"]["mtp_sat"]["tok_s"] / hs["mtp_sat_batch"], 1)),
                   b200x8_ar=dict(tok_s=ge["saturated_tokens_s"], users=ge["sat_batch"],
                                  per_user=round(ge["saturated_tokens_s"] / ge["sat_batch"], 1)))
           for c in CTX}
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return dict(schema="opentallas.uarch.ds_energy_silicon_authoritative.v1", date="2026-10-04",
                status="MODEL on authoritative/measured inputs; every non-record constant in ASSUMED",
                source_commit=head, tau=TAU, sources=SRC, assumed=ASSUMED,
                rates=R, silicon=A, silicon_sensitivity=A_sens, power=P, per_area_and_iso=per_area_and_iso(R, A, P),
                saturation_points=sat,
                hbm_sweep=hs, cross_checks=dict(rates=rchk, power=pchk, hbm=hs["crosscheck"]),
                h100_measured_anchor=dict(nvls_ar_us=2.244, grid_sync_us=1.097, sys_fenced_ar_us="8.904-9.144",
                                          note="H100 numbers enter as the ablation's NVLS transport and R0's grid.sync; "
                                               "no DeepSeek-V4.1 decode was measured on H100"))


if __name__ == "__main__":
    d = build()
    if "--check" in sys.argv:
        print(json.dumps(d["cross_checks"], indent=1))
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(d, indent=1) + "\n")
        print("wrote", OUT)
