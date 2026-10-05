#!/usr/bin/env python3
"""Writes inventory.json: every HBM-accelerator RTL block on the token path, its measured fmax evidence at
the 1.2 GHz sign-off (0.833 ns, SS setup +60 ps, FF hold +25 ps) and closed / open / never-measured status.
Rows are transcribed from committed records (paths given per row); status is re-derived from the numbers."""
import hashlib, json, pathlib
P = 0.833
def r(module, design, family, status, evidence, ss_r2r=None, ff=None, period=None, kind=None, note="", owner=None):
    d = dict(module=module, design=design, family=family, status=status, evidence=evidence,
             period_ns=period, ss_reg_to_reg_slack_ps=ss_r2r, ff_hold_slack_ps=ff, evidence_kind=kind, note=note)
    if ss_r2r is not None and period:
        d["fmax_mhz_equiv_ss"] = round(1e6 / (period * 1000 - ss_r2r), 1)
    if owner: d["closure_owner"] = owner
    return d
HCL = "results/rtl/hbm_clock_loops_20261004"; RCL = "results/rtl/risk_clock_loops_20261003"; PA = "results/physical_abi3/asap7"
rows = [
 # ---- SM element (DS ot_gpu_sm_v; the per-token sm + barrier terms) ----
 r("ot_gpu_bulk_copy (as built, in ot_gpu_sm_v)", "DS+Q", "sm", "open", f"{RCL}/screens/hbm/bulkcopy_ds_833.json", -863, None, P, "screen",
   "LIMITER of the as-built SM clock: DS 590 MHz (Q 682 MHz); sets 0.59 GHz in results/rtl/dshbm_baseline_measured_20261004 (as_built_bulk_copy_0p590GHz)"),
 r("ot_hbm_accel_bulk_copy ENABLE=1 r12", "DS+Q", "sm", "closed", f"{HCL}/bulk/closure_r12.json", 13.51, 11.43, P, "routed",
   "Q +55.58/+4.97; false-path IO (registered both sides); 0 added cycles", owner="done"),
 r("ot_gpu_issue (as built)", "DS+Q", "sm", "open", f"{RCL}/screens/hbm/issue_ds_833.json", -497, None, P, "screen", "DS 752 / Q 813 MHz"),
 r("ot_hbm_accel_issue ENABLE=1", "DS+Q", "sm", "open_io", f"{HCL}/routes/issue_ds_0833_r4/corner_sta.json", 27.94, 8.40, P, "routed",
   "r2r closes (Q +31.94/+8.97) but output ports -136.7 (DS) / -189.6 (Q) ps: closes_signoff=false until proven in SM context", owner="sm"),
 r("ot_gpu_tc_col", "DS+Q", "sm", "open", f"{PA}/gpu/parent_tc_col_terminal_record_20261001/corners.json", -102.66, -0.91, P, "routed", owner="sm"),
 r("ot_gpu_tc16", "DS", "sm", "open", f"{PA}/gpu/w13_tc16_terminal_20261001T120346Z", -31.06, 5.22, P, "routed", owner="sm"),
 r("ot_gpu_bd_col", "DS", "sm", "closed", f"{PA}/gpu/w13_followup_20261001/terminal_snapshot/ot_gpu_bd_col/corners.json", 14.3, 3.48, P, "routed", owner="done"),
 r("ot_gpu_stack", "DS+Q", "sm", "open", f"{RCL}/screens/hbm/stack_833.json", -126.3, None, P, "screen", "only a TT 0.92 ns route exists", owner="sm"),
 r("ot_gpu_tree / ot_gpu_xstore / ot_v41_bterm(2) / ot_hdc_blockdot / row-scale fmul", "DS+Q", "sm", "never_measured", "none at SS (blockdot TT only)", owner="sm"),
 r("ot_gpu_fadd = ot_hdc_fp32_add_lat LAT7", "DS+Q", "sm", "closed_unit", f"{PA}/hdc/w11_fp/nm_fadd7/physical.json", 40.1, 7.1, P, "routed", "standalone only; must hold in context (ABC re-ripple)", owner="sm"),
 r("ot_hdc_fp32_mul_lat LAT6", "DS+Q", "sm", "closed_unit", f"{PA}/hdc/w11_fp/w11_fp_latency_sweep.json", 11.4, None, P, "routed", "LAT3-5 fail, LAT7 -17.8"),
 r("ot_gpu_sm_v element (whole)", "DS", "sm", "never_measured", f"{PA}/gpu/w13_followup_20261001/modeled_queue.json (queued only)", owner="sm"),
 r("ot_gpu_sm_q / ot_hbm_accel_sm_q element", "Q (ablation)", "sm", "never_measured", "not on the HA8 Qwen accelerator vehicle (W12 datapath) - sm agent to confirm", owner="sm"),
 # ---- serial unit and attention (DS local term, 0.9 GHz serial clock as built) ----
 r("ot_hdc_v41x_vec N1024/M256 (SU) as measured MLAT4/ALAT3", "DS", "su", "open", f"{PA}/hdc/v41x/w11_serial/summary.json (sc_l3 light lane)", -109.3, 3.3, 1.111, "routed",
   "the measured SU build does not even close 0.9 GHz (819.5 MHz); never routed at 0.833; the full SU has no valid number (ds05_vec_bbdp screen openroad_rc=1)", owner="su"),
 r("ot_hdc_v41x_vec_light1024r MLAT5/ALAT4", "DS", "su", "closed_0p9_only", f"{PA}/hdc/v41x/w11_serial/summary.json (sc_l5b)", 34.6, 2.5, 1.111, "routed", "929 MHz; 1.2 GHz needs deeper FP units", owner="su"),
 r("ot_hdc_v41x_vec_red1024 (reducer)", "DS", "su", "never_measured", "sc_r5/sc_r6 yosys OOM", owner="su"),
 r("ot_hdc_v41x side/SFU (softplus_s, fsqrt, fdiv, exp/sigmoid/rsqrt)", "DS", "su", "open", f"{PA}/hdc/w11_softplus_short/", -2.5, None, 1.111, "routed", "softplus_s fails even at 1.111; fdiv TT only", owner="su"),
 r("ot_hdc_v41x_vec_kr KR_DEPTH=40 (local-chains lever)", "DS", "su", "open", f"{PA}/hdc/w11_recovery_20261001/fz_l8,fz_l20", None, None, 1.111, "routed", "GRT congestion failure", owner="su"),
 r("ot_hdc_fastfp LAT3 add/mul (SU + attention as built)", "DS", "su", "open", f"{PA}/hdc/w11_fp/ (nm_fadd3, nm_fmul3)", -192.7, None, P, "routed", "975 / 881 MHz at SS", owner="su"),
 r("ot_hdc_v41x_attn_tile (T=128 225 cyc / T=640 609 cyc, FPL=FML=QL=3)", "DS", "attn", "open", "results/rtl/v41_full_attention_numeric/result.json; w11_stream_summary.json", None, None, P, "none",
   "as-built build uses fastfp LAT3 (fails SS); 1.2 GHz needs FPL7/FML6 (+39 cyc); no tile route", owner="attn"),
 r("ot_hdc_v41x_attn engine control (verify)", "DS", "attn", "open", f"{PA}/chip/w11_attn_eng_ctl/wc833_cts", -1204.62, None, P, "cts", owner="attn"),
 # ---- memory controller front end / HBM service ----
 r("ot_hbm_r14_stream_pc/stack r8b (WR_EN=0)", "DS+Q", "svc", "closed", f"{HCL}/stream/corner_sta-r8b-0833.json", 6.28, 5.11, P, "routed", owner="done"),
 r("Qwen HBM_STREAM merged stream_stack WR_EN=1 WQ=4", "Q", "svc", "open", "results/rtl/qwen_rom_hbm_stream_realmem_20261004/merge_r8/physical-ss-wr1-1024-PASS.json + corner_sta re-run 2026-10-04 (SS 25.57/FF 3.86 at 1.024 ns)",
   25.57, 3.86, 1.024, "routed", "record header says TT (the tool's synth descriptor); corner_sta on the kept route confirms SS/FF at 1.024 ns only (977 MHz); WR_EN=0 at 0.833: SS +8.31/FF +5.01", owner="svc"),
 r("ot_hbm_accel_kv_lifecycle k10", "DS+Q", "svc", "closed", f"{HCL}/kv/kv_closure_record.json", 10.36, 7.73, P, "routed", owner="done"),
 r("ot_hbm_accel_dskv_wb / stream_pc_wb / stream_pc / index_stack / return_fifo / cdc_fifo / owned_crossing / causal_command_provider", "DS", "svc", "never_measured", "none", owner="svc"),
 r("rtl/model_ready_hbm_r14 pc/route/tag_owner/clock_bridge/reader_lease/fifo2/result_producer/sector_completion_store", "DS+Q", "svc", "never_measured", "r14pc screens launched, never committed", owner="svc"),
 r("ot_hbm_accel_expert_fetch_stream(_la/_sram) / expert_stream_pc", "DS", "svc", "in_progress_other", "claude/hbm-accel-r5a-gates-20261004 (floorplan e6 -7.5 ps)", owner="r5a agent"),
 r("ot_gpu_rf_visibility_fence_w6 (SECDED)", "DS+Q", "ctl", "in_progress_other", f"{RCL}/screens/hbm/fence_w6_833.json", -1498, None, P, "screen", "429 MHz; HA1 says not on the base-system path", owner="fence agent"),
 # ---- SM-side service / control / DSpark ----
 r("ot_gpu_router_topk", "DS", "ctl", "open", f"{RCL}/screens/hbm/topk_833.json", -776, None, P, "screen", "621 MHz; top-6 is model-priced in the baseline", owner="ctl"),
 r("ot_gpu_barrier_node", "DS+Q", "ctl", "screen_pass", f"{RCL}/screens/hbm/barrier_833.json", 601.5, None, P, "screen", "TT 0.92 route only", owner="ctl"),
 r("ot_gpu_scratch_service", "DS+Q", "ctl", "open", f"{RCL}/screens/hbm/scratch_833.json", -130.1, None, P, "screen", "SRAM clk->Q 707 ps", owner="ctl"),
 r("ot_gpu_rf_service / ot_gpu_full_sm_service / hbm_rf_shared_context / payload_assemble", "DS+Q", "ctl", "never_measured", "rfsvc_ack/fullsm_ack screens openroad_rc=1", owner="ctl"),
 r("DS MTP accept guarded (SECDED slot state)", "DS", "ctl", "open", f"{RCL}/screens/hbm/mtp_1111.json", None, None, 1.111, "screen", "444 MHz", owner="ctl"),
 r("rtl/gpu/dshbm/* (accept_port, argmax, dspark_ctl, dspark_top, expert_union, spec_state)", "DS", "ctl", "never_measured", "none", owner="ctl"),
 # ---- collectives / NoC ----
 r("W15 NVLS switch ot_link_nvls_switch", "DS", "noc", "never_measured", f"{RCL}/jobs/hbm_jobs.sh (nvls_833/967 launched, never committed)", owner="noc"),
 r("gpu_sys coll_endpoint/fabric/mux/xbar/l2_slice/cdc", "DS+Q", "noc", "never_measured", "none", owner="noc"),
 r("HA2 direct-link endpoint rtl/hbm_accel/ha2_ar", "DS", "noc", "never_measured", "results/rtl/hbm_accel_ha2_ar_20261004/terminal.json (G-timing NOT RUN; not adopted)", owner="noc"),
 # ---- Qwen W12 datapath (HA8 vehicle, one 0.833 ns clock) ----
 r("ot_qwen_me_spine_w12 / me_array / w12_matvec (ME)", "Q", "qwen-me", "never_measured", "results/rtl/qwen_rom_w12_runtime/terminal_review_20261001/spine_s833b (yosys 24 h timeout)", owner="qwen-me"),
 r("ot_qwen_rom_tile_logic_w12", "Q", "qwen-me", "never_measured", "none", owner="qwen-me"),
 r("ot_qwen_rom_core (generated sequencer)", "Q", "qwen-core", "never_measured", "core_bb screens never committed", owner="qwen-core"),
 r("ot_hdc_vstream_rt SW64 (Qwen SU/attention)", "Q", "qwen-core", "never_measured", "vstream_sw64 screen never committed", owner="qwen-core"),
 r("ot_qwen_tp_seq_w12 (N=4)", "Q", "qwen-core", "open_io", f"{RCL}/routes/qwen_tp_seq_0833/corner_sta.json", 6.99, 10.6, P, "routed", "output port -73.7 ps; N=2 never routed", owner="qwen-core"),
 r("ot_rom_oneshot_die (Qwen collective endpoint)", "Q", "qwen-core", "open", f"{RCL}/screens/qwen/oneshot_die_d32_833.json", -1208, None, P, "screen", "490 MHz, rp->head mux->pop loop", owner="qwen-core"),
 r("ot_hbmacc_qwen_wstream + engine-side CDC/ME_STALL gating", "Q", "qwen-core", "never_measured", "none", owner="qwen-core"),
]
# Closed source-selected ctl components, independently of blocked spec/topk.
# Baseline rows stay unchanged: a variant is not an automatic clock adoption.
ctl_path = pathlib.Path(__file__).parent / "ctl_takeover_20261005/closure.json"
if ctl_path.exists():
    ctl = json.loads(ctl_path.read_text())
    for item in ctl["rows"]:
        variant = item["module"] + " " + item["label"] + " (source-selected)"
        row = r(variant, "DS", "ctl", "closed_variant",
                "results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/" + item["label"] + "/corner_sta.json",
                item["SS_register_ps"], item["FF_hold_ps"], P, "routed",
                "Full-shape source-selected component only; " + item["cycle_scope"] + "; default off, parent accelerator unqualified",
                owner="Sagan (Codex item 9 ctl)")
        row.update(canonical_module=item["module"], parameters=item["parameters"],
                   ss_worst_slack_ps=item["SS_worst_ps"], cycle_delta=item["cycle_delta"],
                   source_pins=item["source_pins"], complete_accelerator_qualified=False)
        rows.append(row)
    rows.append(r("ot_dshbm_spec_state_f spec_f3 (source-selected)", "DS", "ctl", "blocked_exactness",
                  "results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/sim_spec3_s8/run.log",
                  note="Retained terminal reports 2 mismatches although exit0; positive routed slack does not permit adoption", owner="Claude (exactness escalation)"))


# New source-selected spec successor: historical failed spec_f3 stays blocked.
spec_path = pathlib.Path(__file__).parent / "ctl_spec_token_edge_20261005/closure.json"
if spec_path.exists():
    spec = json.loads(spec_path.read_text())
    row = r(spec["module"] + " " + spec["label"] + " (source-selected)", "DS", "ctl", "closed_variant",
            "results/rtl/hbm_accel_fmax_inventory_20261004/ctl_spec_token_edge_20261005/corner_sta.json",
            spec["SS_register_ps"], spec["FF_hold_ps"], P, "routed",
            spec["cycle_scope"], owner="Sagan (Codex item9 ctl); Pauli semantic source")
    row.update(canonical_module=spec["module"], parameters=spec["parameters"],
               source_pins=spec["source_pins"], ss_worst_slack_ps=spec["SS_worst_ps"],
               cycle_delta=0, complete_accelerator_qualified=False)
    rows.append(row)

# Actual source-selected Qwen tile routes: terminal completion is not sign-off.
# Keep original baseline rows and all historical failures; enroll these variants
# from Nash's committed summary without a new route, replay or source change.
tile_path = pathlib.Path(__file__).parent / "qwen_me/tile_failures_r1.json"
if tile_path.exists():
    tile_book = json.loads(tile_path.read_text())
    evidence = "results/rtl/hbm_accel_fmax_inventory_20261004/qwen_me/tile_failures_r1.json"
    for item in tile_book["records"]:
        row = r("ot_qwen_rom_tile_logic_w12 " + item["case"] + " (source-selected)",
                "Q", "qwen-me", "failed_variant", evidence,
                item["setup_ss"]["worst_register_d_slack_ps"],
                item["hold_ff"]["worst_register_d_slack_ps"], P, "routed",
                "Terminal FAIL/NOADOPT under SS60/FF25; standalone false-path IO, "
                "enclosing boundary unqualified. No new source cut or clock/latency credit. "
                + item["worst_cone_source_semantics"], owner="Claude (source-cone diagnosis); Nash (qme)")
        row.update(canonical_module="ot_qwen_rom_tile_logic_w12", case=item["case"],
                   parameters=item["parameters"], source_pins=item["source_pins"],
                   evidence_sha256=hashlib.sha256(tile_path.read_bytes()).hexdigest(),
                   route_exit=item["process_exit"], corner_exit=item["corner_exit"],
                   closes_signoff=item["closes_signoff"], adopted=False,
                   DRV=item["DRV"], drc=item["drc"], antenna=item["antenna"],
                   mapped_area=item["mapped_area"], context_latency=item["context_latency"],
                   worst_cones=item["worst_cones"], standalone_false_path_io=True,
                   complete_accelerator_qualified=False,
                   correctness_binding="Nash reports tile ot_qwen_w12_bmul, port ot_hdc_fp32_mul_lat; "
                   "neither is suspect ot_hdc_fp32_mul_f12_l6. Correctness hold remains; "
                   "no new dispatch/reproof or confirmed affected owned heavy job.")
        rows.append(row)

limiter = {
 "as_built_sm_clock_ghz": 0.5897,
 "set_by": "ot_gpu_bulk_copy (DS line 1088) consume loop cons_p -> 1024:1 full[cons_p] -> take: screen 590 MHz (-863 ps at 0.833 ns), "
           f"{RCL}/screens/hbm/bulkcopy_ds_833.json; priced in tools/dshbm_baseline_measure.py as the binding SM sub-block",
 "status": "fixed by ot_hbm_accel_bulk_copy r12 (routed SS +13.51/FF +11.43 DS, 0 added cycles); the SM element as a whole is NOT yet shown at 1.2 GHz: next-worst on-SM evidence is ot_gpu_tc_col -102.66 ps (about 1.07 GHz) and the issue output ports",
 "serial_domain": "the SU (local term) runs at 0.9 GHz by design and its measured MLAT4/ALAT3 build closes only 819.5 MHz even there; the owner target is 1.2 GHz everywhere",
}
counts = {}
for x in rows: counts[x["status"]] = counts.get(x["status"], 0) + 1
out = {"schema": "opentallas.hbm_accel.fmax_inventory.v1", "date": "2026-10-04", "signoff": "0.833 ns, SS setup 60 ps, FF hold 25 ps (tools/w18/corner_sta.py)",
       "source_main": "2a987bdc5", "limiter": limiter, "counts": counts, "blocks": rows,
       "families": {"sm": "DS SM element", "su": "DS serial unit", "attn": "DS attention tile/engine", "svc": "memory-controller front end + HBM service",
                    "ctl": "SM-side service/control + DSpark", "noc": "collectives/NoC", "qwen-me": "Qwen W12 ME + tile", "qwen-core": "Qwen core/vstream/tp_seq/collective/wstream"}}
pathlib.Path(__file__).with_name("inventory.json").write_text(json.dumps(out, indent=1) + "\n")
print(counts)
