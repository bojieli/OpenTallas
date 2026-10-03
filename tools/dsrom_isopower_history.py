#!/usr/bin/env python3
"""DS-ROM iso-power / iso-silicon / multi-column-verify study (model only, read-only on tools/uarch_model.py).

Stage 1 (`run`): executes the unified model and writes raw.json:
  * ROM S58 graph (cons_v41_rom with the S58 selection's settings, as tools/dsrom_4096_partition_token_options.py)
    at 1M and 200K, with the verify pass re-timed for m MAC columns per ROM word (m = 1..6): every field (ROM
    element) node of a P-position pass issues ceil(P/m) word-times instead of P;
  * the per-die static decomposition and dynamic energy categories of that run;
  * the V4.1 HBM comparator TP-96 x 4 stacks (v41_hbm_n, the consolidation's equal-power instance) at 1M and 200K;
  * the Qwen ROM / Qwen HBM economics rows.
Stage 2 (`compose`): arithmetic on raw.json + committed records -> model.json (see REPLAY.md)."""
import copy, json, math, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "results/uarch/dsrom_isopower_history_20261003"
CTXS = (1048576, 200000)
MS = (1, 2, 3, 4, 5, 6)


def run():
    import uarch_model as u
    cap = json.loads((ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json").read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    S = 58
    state = dict(m=1)
    orig_adjust = u._cons_adjust

    def adjust(g, P, *a, **k):
        fin = orig_adjust(g, P, *a, **k)
        m = state["m"]
        if P > 1 and m > 1:
            f = math.ceil(P / m) / P
            for nd in g.nodes.values():
                if nd.get("_uarch"):
                    nd["issue"] *= f
            fin = g.solve(True)
            return fin[[n for n in g.nodes if n.endswith("token.return")][0]]
        return fin
    cap_cool = {}
    orig_cool = u._cons_cooling

    def cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot):
        cap_cool.update(die_static=die_static, die_static_ungated=die_static_ungated, cats=dict(cats), sat=sat,
                        tot={str(k): v for k, v in tot.items()})
        return orig_cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot)
    cap_parts = {}
    orig_parts = u.v41_die_static_parts

    def parts(d):
        p = orig_parts(d)
        cap_parts.update(copy.deepcopy(p))
        return p
    u._cons_adjust, u._cons_cooling, u.v41_die_static_parts = adjust, cool, parts
    saved = copy.deepcopy(u.PRESETS["proposal"])
    rom = {}
    try:
        for ctx in CTXS:
            for m in MS:
                state["m"] = m
                t0 = time.time()
                u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[S]["BF16_pairs_per_die"]
                with u._cons_ctx(ctx):
                    p = u.cons_v41_rom(S, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                                       field_concurrency=u.FIELD_CONCURRENCY,
                                       added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                                       dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                                       ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                                       vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
                u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(copy.deepcopy(saved))
                T1 = 1.0 / p["ar_tokens_s_b1"]
                step1 = u.V41_TAU / p["mtp_tokens_s_b1"]
                Td = u.V41_DRAFT_FRACTION * T1
                rom[f"{ctx}/m{m}"] = dict(
                    ctx=ctx, m=m, ar_tokens_s=p["ar_tokens_s_b1"], ar_us=T1 * 1e6, mtp_tokens_s_model=p["mtp_tokens_s_b1"],
                    verify_us=(step1 - Td) * 1e6, model_draft_us=Td * 1e6, tau_model=u.V41_TAU,
                    ar_sat=p["ar_saturated_tokens_s"], mtp_sat=p["mtp_saturated_tokens_s"], busiest=p["busiest_stage"],
                    busiest_us=p["busiest_stage_us"], capacity_users=p["capacity_users_1m"], energy=p["energy"],
                    static_w_icg=p["static_w_ungated"], cooling=p["cooling"], stage_hops=p["stage_hops"],
                    pipeline_hops_us=p["pipeline_hops_us"],
                    die_static_w=cap_cool["die_static"], cats_J=cap_cool["cats"], tot_occ_s=cap_cool["tot"],
                    die_static_parts=cap_parts, wall_s=round(time.time() - t0, 1))
                print(ctx, m, rom[f"{ctx}/m{m}"]["ar_tokens_s"], round(rom[f"{ctx}/m{m}"]["verify_us"], 2), flush=True)
    finally:
        u._cons_adjust, u._cons_cooling, u.v41_die_static_parts = orig_adjust, orig_cool, orig_parts
        u.PRESETS["proposal"].clear(); u.PRESETS["proposal"].update(saved)
    ec = u.economics()
    lv = u.economics_levers(ec)
    gr = lv["gated_alike"]["rows"]
    hbm = {}
    for ctx in CTXS:
        with u._cons_ctx(ctx):
            hbm[str(ctx)] = u.v41_hbm_n(96, 4, ec, gr, clock_hz=u.PRODUCT_CLOCK_HZ)
    hbm_die = u.right_size_hbm_die("v41", 4)
    q = dict(rom=ec.get("qwen_rom"), hbm=ec.get("qwen_hbm"), keys=list(ec.keys()))
    qwen_area = dict(rom_die_mm2_parts=u.QWEN_ROM_AREA_DIE, rom_die_mm2=sum(u.QWEN_ROM_AREA_DIE.values()),
                     product=u.QWEN_ROM_PRODUCT)
    consts = dict(E_HBM_B=u.E_HBM_B, E_HBM_IF_B=u.E_HBM_IF_B, HBM_IDLE_W_STACK=u.HBM_IDLE_W_STACK, V41_TAU=u.V41_TAU,
                  V41_POSITIONS=u.V41_POSITIONS, V41_DRAFT_FRACTION=u.V41_DRAFT_FRACTION, FAB=u.FAB, COST=u.COST,
                  MASK=u.MASK, HBM_STACK_B=u.HBM_STACK_B)
    (OUT / "raw.json").write_text(json.dumps(dict(rom=rom, hbm=hbm, hbm_die=hbm_die, qwen=q, qwen_area=qwen_area,
                                                  consts=consts), indent=1, default=str))




# ------------------------------------------------------------------------------------------------ stage 2: compose
C1 = {  # claude/dsrom-parallelism-20261003 @ abd77c4e1 results/uarch/dsrom_parallelism_20261003/model.json, C1 rows
    "src": "abd77c4e1:results/uarch/dsrom_parallelism_20261003/model.json candidates[id=C1_PP58_TP4_PAR2rows]",
    "1048576": dict(ar=2347.4, mtp=3539.3, ar_sat=80833.5, mtp_sat=35262.3, users=866),
    "200000": dict(ar=2445.0, mtp=3854.2, ar_sat=80833.5, mtp_sat=35702.4, users=4516),
    "rtl_measured_collectives_ar_1m": 2356.8,   # memory note hub-to-edge-wire-stages (claude/dsrom-c5hc-adopt @ 4ec2eef0e)
    "layer_dies": 464, "head_dies": 8, "table_dies": 36, "dies": 508, "packages": 254, "stacks": 960,
    "die_screen_mm2_reframed": 786.23, "reticle_mm2": 858.0, "fixed_replicated_mm2": 418.27 + 47.21,
    "hop_us": 23.2 / 57, "par2_ucie_need_Bps_per_package": 914.55e9, "layer_packages": 232,
}
HBM_DSPARK = {  # d2aff19ef results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json
    "src": "d2aff19ef:results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json",
    "1048576": dict(ar_us=442.14, verify_p6_us=700.85, mtp_tok_s_tau3649=4847.7),
    "200000": dict(ar_us=441.3, verify_p6_us=699.21, mtp_tok_s_tau3649=4858.3),
    "draft_us": 51.88, "draft_over_ar": 0.1173, "union_p6": 23.904,
}
HBM_SILICON = dict(
    core_die_mm2=121.0, core_die_basis="Samsung HBM3E 24 Gb core die 121.0 mm2 (2024), as reported in public teardown "
    "coverage (search result, FMS 2025 DRAM-301-1 / TechInsights-class figure; secondary source, not in the repo)",
    base_die_mm2=121.0, base_die_basis="ASSUMED equal to the 11 x 11 mm HBM3E stack footprint (technology.json "
    "hbm.hbm3e.stack_beachfront_mm note: '11 mm x 11 mm HBM3E package', Micron product brief); no repo or public base-die "
    "area found",
    high=8, high_basis="technology.json hbm.hbm3e stack_capacity 22.5 GB = 24 GB class = 8-high of 24 Gb dies (Micron: "
    "24 GB at 8-high, 36 GB at 12-high)")
HBM_SILICON["stack_mm2"] = HBM_SILICON["high"] * HBM_SILICON["core_die_mm2"] + HBM_SILICON["base_die_mm2"]
E_HBM_PS = 13.64e-12 * 8   # configs/hardware/power_scenarios.json memory.hbm_path_total (MI250X, SC'25) J/B
QWEN = {  # results/uarch/consolidation.json headline_table.qwen rows (pinned main)
    "rom": dict(design="Qwen ROM option C at 1.2 GHz SS", ar=8460.4, sat=23841.9, mJ_b1=120.1, mJ_sat=107.2, dies=4,
                stacks=16, users_8k=536, capex=29113),
    "hbm2x4": dict(design="Qwen HBM 2 right-sized dies x 4 stacks (265.8 mm2)", ar=880.5, dflash=2296.3, sat=7104.5,
                   mJ_b1=355.8, mJ_sat=128.1, dies=2, die_mm2=265.8, stacks=8, users_8k=255, capex=20104),
    "hbm1x6": dict(design="Qwen HBM 1 right-sized die x 6 stacks (388.9 mm2)", ar=660.4, dflash=1722.2, sat=5328.4,
                   mJ_b1=355.8, mJ_sat=128.1, dies=1, die_mm2=388.9, stacks=6, users_8k=188, capex=19003),
}


def compose():
    import uarch_model as u
    raw = json.loads((OUT / "raw.json").read_text())
    out = dict(schema="opentallas.dsrom.isopower-history.v1", scope="model only; arithmetic on committed records and "
               "the unified model executed read-only; no RTL, P&R or model inference", inputs=dict(
                   c1=C1["src"], hbm_dspark=HBM_DSPARK["src"], hbm_silicon=HBM_SILICON, qwen="results/uarch/consolidation.json"))
    q2, q3 = {}, {}
    for ctx in ("1048576", "200000"):
        m1 = raw["rom"][f"{ctx}/m1"]
        e = m1["energy"]
        c1 = C1[ctx]
        # ---- ROM dynamic energy per token (all ranks), the model's (TP-4 S58 graph; PAR2 does not change totals)
        dyn_ar = e["ar_b1"]["gated_mJ"] * 1e-3 - e["ar_b1"]["gated_static_w"] / e["ar_b1"]["tokens_s"]
        dyn_mtp = e["mtp_b1"]["gated_mJ"] * 1e-3 - e["mtp_b1"]["gated_static_w"] / e["mtp_b1"]["tokens_s"]
        cats = m1["cats_J"]
        hbm_B_tok = (cats["hbm_if"] + cats["stack"]) / u.E_HBM_B
        hbm_reprice = hbm_B_tok * (E_HBM_PS - u.E_HBM_B)
        par2_link_w = C1["layer_packages"] * C1["par2_ucie_need_Bps_per_package"] * 8 * u.E_LINK["ucie"]  # upper bound
        parts = m1["die_static_parts"]
        die_nohbm = m1["die_static_w"] - parts["hbm_if"]
        static = dict(layer_dies_excl_hbm=C1["layer_dies"] * die_nohbm, hbm_stacks_idle=C1["stacks"] * u.HBM_IDLE_W_STACK,
                      head_dies=m1["static_w_icg"]["head_dies"], table_dies=m1["static_w_icg"]["table_dies"],
                      par2_ucie_traffic_upper=par2_link_w)
        P_icg = sum(static.values())
        always_on = static["hbm_stacks_idle"] + static["par2_ucie_traffic_upper"]
        gate_ratio = {k: e[k]["gated_static_w"] / e[k]["ungated_static_w"] for k in e}

        def rom_point(rate, dyn, key, policy):
            gated = P_icg - always_on
            st = (gated * gate_ratio[key] if policy == "stage_pg" else gated) + always_on
            P = st + (dyn + hbm_reprice) * rate
            return dict(tokens_s=round(rate, 1), static_w=round(st, 0), dynamic_mJ=round((dyn + hbm_reprice) * 1e3, 1),
                        system_w=round(P, 0), mJ_per_token=round(P / rate * 1e3, 1),
                        tok_s_per_kw=round(rate / P * 1e3, 2))
        # ---- HBM comparator (TP-96 x 4 stacks = consolidation's equal-power instance) at W19 / DSpark rates
        h = raw["hbm"][ctx]
        Ph = h["static_w_ungated"]
        h_stack_w = h["dies"] * h["stacks_per_die"] * u.HBM_IDLE_W_STACK

        def hbm_dyn(row):
            return row["ungated_mJ"] * 1e-3 - Ph / row["aggregate_tokens_s"]

        def hbm_ratio(row):
            return (row["gated_mJ"] * 1e-3 - hbm_dyn(row)) * row["aggregate_tokens_s"] / Ph

        def hbm_point(rate, row, policy, reprice_frac):
            dyn = hbm_dyn(row) * (1 + reprice_frac)
            g = hbm_ratio(row) if policy == "stage_pg" else 1.0
            st = (Ph - h_stack_w) * g + h_stack_w
            P = st + dyn * rate
            return dict(tokens_s=round(rate, 1), static_w=round(st, 0), dynamic_mJ=round(dyn * 1e3, 1),
                        system_w=round(P, 0), mJ_per_token=round(P / rate * 1e3, 1), tok_s_per_kw=round(rate / P * 1e3, 2))
        hb = HBM_DSPARK[ctx]
        hbm_ar = 1e6 / hb["ar_us"]
        hbm_mtp = HBM_DSPARK["1048576" if ctx == "1048576" else "200000"]["mtp_tok_s_tau3649"]
        # HBM byte share of HBM dynamic: weight bytes of one token at E_HBM_B over the model's dynamic (b1)
        with u._cons_ctx(int(ctx)):
            wb1 = u._v41_weight_bytes(1)
            tot, *_ = u._v41_weight_split()
        kvb = tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]
        frac_b1 = (wb1 + kvb) * (E_HBM_PS - u.E_HBM_B) / hbm_dyn(h["ar"]["batch1"])
        sat_row = h["ar"]["saturated"]
        wbs = u._v41_weight_bytes(sat_row["batch"])
        frac_sat = (wbs / sat_row["batch"] + kvb) * (E_HBM_PS - u.E_HBM_B) / hbm_dyn(sat_row)
        res = {}
        for pol in ("icg_only", "stage_pg"):
            res[pol] = dict(
                rom_c1=dict(ar_b1=rom_point(c1["ar"], dyn_ar, "ar_b1", pol), ar_sat=rom_point(c1["ar_sat"], dyn_ar, "ar_sat", pol),
                            mtp_b1=rom_point(c1["mtp"], dyn_mtp, "mtp_b1", pol),
                            mtp_sat=rom_point(c1["mtp_sat"], dyn_mtp, "mtp_sat", pol)),
                hbm_tp96x4=dict(ar_b1=hbm_point(hbm_ar, h["ar"]["batch1"], pol, frac_b1),
                                ar_sat=hbm_point(sat_row["aggregate_tokens_s"], sat_row, pol, frac_sat),
                                mtp_b1=hbm_point(hbm_mtp, h["mtp"]["batch1"], pol, frac_b1),
                                mtp_sat=hbm_point(h["mtp"]["saturated"]["aggregate_tokens_s"], h["mtp"]["saturated"], pol, frac_b1)))
            r, hh = res[pol]["rom_c1"], res[pol]["hbm_tp96x4"]
            res[pol]["ratios_rom_over_hbm"] = dict(
                per_user_ar=round(r["ar_b1"]["tokens_s"] / hh["ar_b1"]["tokens_s"], 3),
                per_user_mtp=round(r["mtp_b1"]["tokens_s"] / hh["mtp_b1"]["tokens_s"], 3),
                b1_ar_tok_s_per_kw=round(r["ar_b1"]["tok_s_per_kw"] / hh["ar_b1"]["tok_s_per_kw"], 3),
                best_batch_tok_s_per_kw=round(max(r["ar_sat"]["tok_s_per_kw"], r["mtp_sat"]["tok_s_per_kw"])
                                              / max(hh["ar_sat"]["tok_s_per_kw"], hh["mtp_sat"]["tok_s_per_kw"]), 3),
                hbm_instances_at_rom_b1_power=round(r["ar_b1"]["system_w"] / hh["ar_b1"]["system_w"], 2),
                hbm_instances_at_rom_sat_power=round(r["ar_sat"]["system_w"] / hh["ar_sat"]["system_w"], 2))
        res["energy_attribution_mJ_per_token_ar"] = dict(
            rom_dynamic_categories={k: round(v * 1e3, 2) for k, v in cats.items()},
            rom_hbm_bytes_per_token=round(hbm_B_tok), rom_hbm_mJ_at_13p64=round(hbm_B_tok * E_HBM_PS * 1e3, 2),
            hbm_weight_bytes_b1=round(wb1), hbm_kv_idx_bytes_per_user=round(kvb),
            hbm_weight_mJ_b1_at_13p64=round(wb1 * E_HBM_PS * 1e3, 1),
            hbm_weight_mJ_per_token_sat_at_13p64=round(wbs / sat_row["batch"] * E_HBM_PS * 1e3, 1),
            hbm_sat_batch=sat_row["batch"])
        res["static_ledger_rom_c1_icg_w"] = {k: round(v, 0) for k, v in static.items()}
        res["static_ledger_rom_c1_icg_w"]["total"] = round(P_icg, 0)
        res["static_ledger_hbm_w"] = dict(total_ungated=Ph, of_which_stack_idle=h_stack_w)
        res["capacity_users"] = dict(rom_c1=c1["users"], hbm_tp96x4=h["capacity_users_1m"])
        q2[ctx] = res
        # ---- Q3: m columns per ROM word, tau = 4
        ar_m0 = m1["ar_us"]
        par2_ar = 1e6 / c1["ar"] - ar_m0
        Td_model = u.V41_DRAFT_FRACTION
        v_c1 = u.V41_TAU / c1["mtp"] * 1e6 - Td_model * 1e6 / c1["ar"]
        par2_verify = v_c1 - m1["verify_us"]
        ar_c1 = 1e6 / c1["ar"]
        draft = HBM_DSPARK["draft_over_ar"] * ar_c1
        hbm_step = hb["verify_p6_us"] + HBM_DSPARK["draft_us"]
        hbm_tau4 = 4e6 / hbm_step
        F = C1["die_screen_mm2_reframed"] - C1["fixed_replicated_mm2"]
        q_cells = 1686 * (24298.0 - 1096 * 0.37908 / 0.5) / 1e6
        bf_cells = 362 * (63609.0 - 1096 * 0.37908 / 0.5) / 1e6
        rows = []
        for m in MS:
            rm = raw["rom"][f"{ctx}/m{m}"]
            for bound, frac in (("lower_mac_tree_0p6", 0.6), ("upper_whole_element", 1.0)):
                d_col = frac * (q_cells + bf_cells) / 0.60
                screen = C1["die_screen_mm2_reframed"] + (m - 1) * d_col
                fits = screen <= C1["reticle_mm2"]
                field_m = F + (m - 1) * d_col
                S_keep = 58 if screen <= C1["die_screen_mm2_reframed"] + 1e-9 else math.ceil(58 * field_m / F)
                S_ret = 58 if fits else math.ceil(58 * field_m / (C1["reticle_mm2"] - C1["fixed_replicated_mm2"]))
                for plan, S_ in (("reticle_full", S_ret), ("keep_91.6pct_screen", S_keep)):
                    extra = S_ - 58
                    for hop_name, hop_us in (("model_hop_0.407us", C1["hop_us"]), ("board_link_only_0.130us", 0.130)):
                        ar_us = ar_c1 + extra * hop_us
                        ver = rm["verify_us"] + par2_verify + extra * hop_us
                        step = ver + draft
                        rows.append(dict(m=m, area_bound=bound, plan=plan, stages=S_, dies=8 * S_ + 44,
                                         die_screen_mm2=round(min(screen, C1["reticle_mm2"]) if plan == "reticle_full" and fits
                                                              else (screen if S_ == 58 else
                                                                    (C1["reticle_mm2"] if plan == "reticle_full" else C1["die_screen_mm2_reframed"])), 1),
                                         added_mm2_per_die_at_S58=round((m - 1) * d_col, 1), fits_reticle_at_S58=fits,
                                         hop=hop_name, extra_hops=extra, ar_us=round(ar_us, 1), verify_us=round(ver, 1),
                                         verify_over_ar=round(ver / ar_us, 3), draft_us=round(draft, 1),
                                         ar_tok_s=round(1e6 / ar_us, 1), tau4_tok_s=round(4e6 / step, 1),
                                         tau4_over_hbm=round(4e6 / step / hbm_tau4, 3),
                                         tau3649_tok_s=round(u.V41_TAU * 1e6 / step, 1)))
        q3[ctx] = dict(hbm_tau4_tok_s=round(hbm_tau4, 1), hbm_step_us=round(hbm_step, 2),
                       hbm_verify_over_ar=round(hb["verify_p6_us"] / hb["ar_us"], 3),
                       rom_m1_verify_over_ar_model=round(m1["verify_us"] / ar_m0, 3),
                       rom_c1_verify_over_ar=round(v_c1 / ar_c1, 3),
                       par2_delta_us=dict(ar=round(par2_ar, 2), verify=round(par2_verify, 2)),
                       rom_draft_us=round(draft, 1), rom_draft_basis="0.1173 x C1 AR (HBM DSpark draft/AR structural proxy, "
                       "d2aff19ef rom_note); the model's ASSUMED 3/40 gives %.1f us" % (0.075 * ar_c1),
                       verify_us_by_m_model={str(m): round(raw["rom"][f"{ctx}/m{m}"]["verify_us"], 2) for m in MS},
                       rows=rows)
    out["q2"], out["q3"] = q2, q3
    # ---- iso-silicon (logic + DRAM core + base dies) and cost
    st_mm2 = HBM_SILICON["stack_mm2"]
    iso = {}
    for ctx in ("1048576", "200000"):
        r = q2[ctx]["icg_only"]
        rom_logic_lo = C1["dies"] * C1["die_screen_mm2_reframed"]
        rom_logic_hi = C1["dies"] * C1["reticle_mm2"]
        rom_dram = C1["stacks"] * st_mm2
        h = raw["hbm"][ctx]
        hbm_logic = h["silicon_mm2"]
        hbm_dram = h["dies"] * h["stacks_per_die"] * st_mm2
        rom_tot, hbm_tot = rom_logic_lo + rom_dram, hbm_logic + hbm_dram
        best_r = max(r["rom_c1"]["ar_sat"]["tokens_s"], r["rom_c1"]["mtp_sat"]["tokens_s"])
        best_h = max(r["hbm_tp96x4"]["ar_sat"]["tokens_s"], r["hbm_tp96x4"]["mtp_sat"]["tokens_s"])
        iso[ctx] = dict(
            rom=dict(logic_mm2=rom_logic_lo, logic_mm2_if_full_reticle=rom_logic_hi, dram_mm2=rom_dram, stacks=C1["stacks"],
                     total_mm2=rom_tot, ar_per_user=r["rom_c1"]["ar_b1"]["tokens_s"], best_tok_s=best_r,
                     best_tok_s_per_m2=round(best_r / rom_tot * 1e6, 1)),
            hbm=dict(logic_mm2=hbm_logic, dram_mm2=hbm_dram, stacks=h["dies"] * h["stacks_per_die"], total_mm2=hbm_tot,
                     ar_per_user=r["hbm_tp96x4"]["ar_b1"]["tokens_s"], best_tok_s=best_h,
                     best_tok_s_per_m2=round(best_h / hbm_tot * 1e6, 1)),
            hbm_instances_at_rom_total_silicon=round(rom_tot / hbm_tot, 2),
            hbm_instances_at_rom_logic_only=round(rom_logic_lo / hbm_logic, 2),
            ratio_best_tok_s_per_mm2_rom_over_hbm=round(best_r / rom_tot / (best_h / hbm_tot), 3),
            ratio_logic_only=round(best_r / rom_logic_lo / (best_h / hbm_logic), 3),
            dram_share_of_silicon=dict(rom=round(rom_dram / rom_tot, 3), hbm=round(hbm_dram / hbm_tot, 3)))
    rom_cost = u.mfg_cost([(C1["dies"], C1["die_screen_mm2_reframed"])], [(C1["packages"], "cowos_l_2die")], C1["stacks"],
                          rom_dies=C1["dies"], rom_bases=u.MASK["v41_base_designs"])
    hbm_cost = raw["hbm"]["1048576"]["cost"]
    r1 = q2["1048576"]["icg_only"]
    iso["cost_1m"] = dict(
        basis="tools/uarch_model.py FAB/mfg_cost: logic die cost from wafer $16,988 (CSET 2020 N5 estimate) with a "
              "negative-binomial yield; HBM priced per STACK at ASSUMED $360 (COST.hbm_stack_usd), not per DRAM mm2; "
              "CoWoS-L $1,100 + test $920 a package (analyst estimates); NRE / 1,000 units",
        rom_capex=rom_cost["capex_usd"], hbm_capex=hbm_cost["capex_usd"],
        dram_implied_usd_per_mm2=round(u.COST["hbm_stack_usd"] / st_mm2, 3),
        logic_usd_per_mm2_rom_die=round(u.die_cost(C1["die_screen_mm2_reframed"])["usd"] / C1["die_screen_mm2_reframed"], 3),
        rom_best_tok_s_per_kusd=[round(iso["1048576"]["rom"]["best_tok_s"] / c * 1e3, 2) for c in rom_cost["capex_usd"].values()],
        hbm_best_tok_s_per_kusd=round(iso["1048576"]["hbm"]["best_tok_s"] / hbm_cost["capex_usd"]["low"] * 1e3, 2),
        rom_ar_per_user=r1["rom_c1"]["ar_b1"]["tokens_s"], hbm_ar_per_user=r1["hbm_tp96x4"]["ar_b1"]["tokens_s"])
    qa = raw["qwen_area"]["rom_die_mm2"]
    qw = {}
    for k, v in QWEN.items():
        logic = v["dies"] * (qa if k == "rom" else v["die_mm2"])
        dram = v["stacks"] * st_mm2
        P_b1, P_sat = v["mJ_b1"] * 1e-3 * v["ar"], v["mJ_sat"] * 1e-3 * v["sat"]
        qw[k] = dict(design=v["design"], logic_mm2=round(logic, 1), dram_mm2=dram, total_mm2=round(logic + dram, 1),
                     ar_per_user=v["ar"], dflash_per_user=v.get("dflash"), sat_tok_s=v["sat"],
                     system_w_b1=round(P_b1, 0), system_w_sat=round(P_sat, 0),
                     sat_tok_s_per_kw=round(v["sat"] / P_sat * 1e3, 1), b1_tok_s_per_kw=round(v["ar"] / P_b1 * 1e3, 1),
                     sat_tok_s_per_m2_total=round(v["sat"] / (logic + dram) * 1e6, 1),
                     sat_tok_s_per_m2_logic=round(v["sat"] / logic * 1e6, 1), capex_usd=v["capex"],
                     sat_tok_s_per_kusd=round(v["sat"] / v["capex"] * 1e3, 1))
    for k in ("hbm2x4", "hbm1x6"):
        qw[f"rom_over_{k}"] = dict(
            sat_per_total_mm2=round(qw["rom"]["sat_tok_s_per_m2_total"] / qw[k]["sat_tok_s_per_m2_total"], 3),
            sat_per_logic_mm2=round(qw["rom"]["sat_tok_s_per_m2_logic"] / qw[k]["sat_tok_s_per_m2_logic"], 3),
            sat_per_kw=round(qw["rom"]["sat_tok_s_per_kw"] / qw[k]["sat_tok_s_per_kw"], 3),
            per_user_ar=round(qw["rom"]["ar_per_user"] / qw[k]["ar_per_user"], 2),
            per_user_vs_dflash=round(qw["rom"]["ar_per_user"] / qw[k]["dflash_per_user"], 2),
            sat_per_kusd=round(qw["rom"]["sat_tok_s_per_kusd"] / qw[k]["sat_tok_s_per_kusd"], 3))
    iso["qwen_8k"] = qw
    out["iso_silicon"] = iso
    (OUT / "model.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(q2=q2, iso=iso), indent=1)[:12000])


if __name__ == "__main__":
    {"run": run, "compose": compose}[sys.argv[1]]()
