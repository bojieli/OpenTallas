# KV-PLAN-R2 handoff (KV plan + hg owner; successor of KV-PLAN-R1)

Written 2026-11-20 15:2x PST. Posts: lanes/posts/KV-PLAN-R2.md. Read lanes/handoff/KV-PLAN-R1.md (R3b content, D27 list) and
lanes/FABLE-PD-KV-1500.md (D27 rows 1-4 evidence, stop list). Lane dirs: epyc8 /srv/opentallas-scratch2/claude/kv-plan-r2, intel2 ~/tmp/kvplanr2.

## Live
- D26 R3b gate: epyc7 unit oth-ubuntu-1257077-1795215290 (admitted 15:0x after 556 s), intel2 client pid 1918181,
  log intel2 ~/tmp/kvplanr1/d26_r3b_e7_gate.log. Script epyc7 .../kv-d23-compose8/d26_raw/d26_contracts/run_gate_r3b.sh
  (outputs normal_g0_r3b/gate.out, normal_gates_r3b/gate.out on epyc7). Waiter: intel2 ~/tmp/kvplanr2/wait_r3b.sh (prints log tail on client exit).
  On green: check param_regen.json ectl RESPONSE_LAT 26 (QK 37) and the 40 core_input_lockup ports bound on 19 hg/hgi types;
  apply at 20:00 cut (or as soon as green); kit_wave_edit: delete dies.qwen_kvsys.hold_items kv3_hg, hg_v1, hg_v1p2..v1p6, hg_v3;
  drop qwen_kvsys auto_visual_review_skip ["kv3_hgi*"] once D26 is current.
- source_gate_r3 (epyc8 d26_contracts, 49 GB, copy never gated): ot-delete REFUSED "protected": its parent d26_contracts is a live
  path (R3b client --dir names it). Retry `ot-delete <path>` on epyc8 after the R3b client exits. Do not bypass the guard.
- kv3_hub_Ei a4 (D25e3, kit_wave qwen_kvsys_kv3_hub_Ei_bae9e2c2702a8/a4): gen/lint/preflight PASS, place on intel1 since 12:04;
  3_3_place_gp GPL finished (1284 s), openroad busy (119% CPU) in "Report metrics stage 3" at 15:09, log silent since 14:18. Not hung (CPU). a3 Error 241 not repeated.
- PV (FABLE-FIX-KV-PV-R2): v8m/v8c/v8p at 3_place 15:09; no final result yet. Bring in when RESULT posts.

## D27 findings so far (private, nothing composed yet)
- sys_c L356 (row 2): mechanism found. Plan tap_tree forward serdes_E.tx_up is declared i_serdes_E_tx_up -> o_serdes_E_tx_up with
  5 FIRM stations (internal_stations conn bus:o_serdes_E_tx_up, hop 365 um, y 1003). But the bound RTL (kit a7 rtl/kv3_sys_c_part.sv:51,56)
  packs the forward onto o_dcal_dob[2] (lane L356, 78 cycles: transport_fault, emb_tx_slot, fwd) and o_serdes_E_tx_up carries abort_drained.
  So the stations sit on the wrong bus: the real net has none. Fix options: (a) internal_stations row conn bus:o_dcal_dob launch
  bus i_serdes_E_tx_up at <= 300 um (E face (2160,~1003) -> W face (0,335): ~2,750 um, 9-10 stations); cycles move from the L356 receiver
  pad (78 fixed has room), so no latency change - check bind handles a row that stations one bit of a 3-bit bus (one bus = one latency
  rule: bits 0/1 launch SW); (b) fix the bind packing so the fwd rides L2047 with its declared stations, and re-site those 5 at 300 um (7 needed).
- Check gap: tools/die_plan/fwd_reach.py --reach 300 on D25f2 = PASS 0/358 though many legs need more stations than declared
  (e.g. sys_c serdes_E.tx_up +7 st vs 5 declared at 365 um; hub_Wo boot_go/die_rst_n/hbm_rst_n/host_rst_n _d1 legs +8 st). It accepts any
  declared row without checking its hop. Output epyc8 kv-plan-r2/fwd_reach300_d25f2.{txt,json}. Row: re-site declared forward stations to
  300 um (fwd_reach with hop check) on all KV types; the hub_Wo host.* reset forwards are probably the "reset relay reach" row 3 class too.
- efault (row 1): u_efault is a plan cell (contents[] ot_dp_efault, params N=IN_LANES AGE=REL_AGE; nets from asbuilt.plan_cells cell_conns,
  tools/die_plan/bind_plancells.py). Existing staged forms: bind_intra_stations.py (asbuilt land_intra_stations, leaf->leaf and leaf->bus:out,
  ot_dp_dly_keep per bit at sites, fail-closed on multi-driver loads). Neither stations the eq[] input of a plan cell. Needed: a staged
  efault form (per-rank eq relayed in <= 300 um ot_dp_dly_keep chains, or local partial efault cells + relayed fault OR), with AGE += stage
  depth so the armed check still samples after the eq arrives. Generator change, 29 types; measure on hub_Wo and hgi_v1 collector leg.
- Row 4 checked: KV-SYSC-1119 rows are NOT bound. D25f2 sys_c has only R-REACH-2 rows (405-era): o_dNd_kv_rx_payload 1 st (656 um -> 328 um hops),
  srx 1 (517), svc 1 (435), svc_d1 4 (1519), emb_tx_payload 2 (947); no link_cfg_data row. Needed at 300 um: rx_payload 2+, srx 1, svc 1, svc_d1 5, emb_tx 3, link_cfg_data 2 (re-measure).
- Row 3 (reset relay reach u_rrl_172/u_rrl_16): not started.
- Build all D27 rows as a private G0 proof on the D26 plan once D26 applies (compose_d27.sh like kv-plan-r1/compose_r3.sh), for the 11-21 cut.

## Stop list (unchanged)
No route/repair of hub_Wo / sys_c; no route of D25e3 hgi kits; no kR late-repair retry; no D26 claim for hub_Wo/sys_c/hgi_v1 collector.
