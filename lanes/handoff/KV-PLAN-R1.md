# KV-PLAN-R1 handoff (KV plan + hg owner; successor of KV-D23-COMPOSE, FABLE-FIX-KV-HG, OPUS hg lane, Codex)

Written 2026-11-20 09:5x PST. Posts: lanes/posts/KV-PLAN-R1.md. Lane dirs: epyc8 /srv/opentallas-scratch2/claude/kv-plan-r1
(wt = proposal-3 clone, wt_rls, wt_pv = lane clones), intel2 same path (kR_copy, kR_rb, wait_r3.sh), hub logs intel2 ~/tmp/kvplanr1.

## Live (update 11:3x)
- 15:0x MOVED: epyc8 R3b waiter (waited 3h20, never started) cancelled; R3b relaunched on epyc7 --priority plan --mem 56 --threads 3,
  same dir (inputs + D25f2 tree copied to epyc7, TREE_RC 0). intel2 client pid 1918181, log ~/tmp/kvplanr1/d26_r3b_e7_gate.log.
  Lines below about epyc8 PID 1927491 are superseded.
- R3 first launch ran 10:4x and exited 3 before compose: the runtime check could not see the new rt sha in the unfetched warm repo.
  Relaunched as run_gate_r3b.sh (fetches first; candidate source_gate_r3b, outputs normal_g0_r3b / normal_gates_r3b), intel2 launcher
  PID 1927491, log ~/tmp/kvplanr1/d26_r3b_gate.log, proof priority epyc8. source_gate_r3 (copy only, never gated) is FREE FOR CLEANUP.
- compose_r3.sh now also: 5. d26r3_cil/krsp_rt26.py (32 p2p slg_*.krsp lanes 5 -> 6 fixed cycles) and 6. gen.py latency --inplace.
  Cause (COORD hourly GEN_LINT on 8 hg types): D25e2 fall rows + D25e3 ROWS-KV-ECTL-RT-FIX took every ECTL rq lane -1, bind
  kv_regen RESPONSE_LAT 25 / QK 36 (krq [6,7] krs [10,11]); hardened ectlk q0..q3 views are 26 / 37, so qkd_ectl3_kiss_st_cols
  elaborates g_param_mismatch. krs +1 restores RT 26 (D25e value). Verify after R3b bind: param_regen.json ectl RESPONSE_LAT 26.
  Alternative if a cycle matters: re-harden ectlk q0..q3 at -GQK_ISSUE_AGE=36 -GRESPONSE_LAT=25 and set CORE_QK/CORE_RL.
- kit_wave hold (kit_wave_edit 35d9003a96b): dies.qwen_kvsys.hold_items kv3_hg, hg_v1, hg_v1p2..v1p6, hg_v3. Lift (delete keys) when D26 applies.
- R3 lockup list also has the 16 head-core rst_n pins (40 ports).
- D26 R2 dc02d274deb3 (reset-only baseline): queued epyc8, intel2 client 2895973, log ~/tmp/kvd23c/d26_typed_r2_gate.log.
- D26 R3 = R2 + rows: epyc8 kv-d23-compose8/d26_raw/d26_contracts/run_gate_r3.sh (R2 script + compose_r3.sh + runtime check
  b699b5b678 / 8899ba10e9 / c6ab8bd7be). Launched by intel2 waiter wait_r3.sh (proof priority, epyc8), log ~/tmp/kvplanr1/d26_r3_gate.log.
  compose_r3.sh is read when the gate runs (edit before admission = in R3):
  1. d26r3_cil/apply_cil.py: clock.core_input_lockup kv3_head_eighth_e0/e2/e6 fronts + u_kt kp/kpv/gf + 16 rst_n pins (40 ports),
     19 hg/hgi types, 0 cycles; clock.core_link_pipe ot_qkh_head_score4_native.pack_fault D=1 (+1 status cycle).
  2. d26r3_rows/n3_rows.py: hgi_v1 x2 section N at <= 300 um (max 299), eN/tN +2 cycles each, aligned at hst_g; check eN pad name u_pd4 after bind.
  3. d26r3_rows/pv_station300.py: budgets.r_dly_spread_station_um kv3_pv 405 -> 300 (16 types, 0 cycles).
  4. d26r3_cil/apply_p3rows.py p3_rows.json: CLKSITE-SPLIT reserved rows, 56 types, 17,031 rects, walls 0 (tree die-level-1119/e3 d25e3_pvsnake3).
  Dry compose on D25f2 plan: schema VALID. Apply at the 20:00 PST cut if strict + G0 + LATCHECK green.
- k13i / k13ci containers on intel2 still run (ot-run --cancel removed clients only); h1/h2 (krsp) on intel2, waiter wait5h.sh -> ~/tmp/opuskvhg/h_grt5.txt.

## Decided
- Proposal 3 on main b699b5b678. krsp: keep h1 (COORD 09:5x, FABLE-PD-KV-0945); h2 not used.
- kR: TT is 1 real path (pack_fault, fixed by row 1); the -310 repair figure is hold-driven (5,105 rls copy -> head-core ends to -277.6,
  fixed by core_input_lockup; reg_leaf_split sees through u_lk_nk since 8899ba10e9). Stop list: no kR late-repair retry; v8j not a latch proof.
- pv trunk inverter: generic dly_spread repeater anchor c6ab8bd7be (main).
- FAIL-ROUTE 50e22a9d11 (hub_Wi SRAM row) and ae70c86fe1 (reset identity) answered: fixed by D26.

## D27 (ranked, FABLE-PD-KV-0945)
1. astk setup: register sc_v at the memory pin (h1 -577 on u_ep.sc_v -> u_sc0 WE), stage eo_q -> owner.fault, seat the bin rank.
2. astk tap rows: split taps 565-588 um wide with 1,200 sinks (1,862 cross-tap ends to -195).
3. pv over-core traffic: 67% of pv_v8 overflow = ft + pad nets crossing pv_pair core boxes; route around or channels in core; read v8k at GRT it5.
4. classify the first pc GRT.
5. hg/hgi superset class (FABLE-SUPERSET 01:59: union links), hgi residual clk_c8 + rst_n relay inside u_head2_e0 at DRT.
6. (FABLE-PD-KV-1500) efault / monitor-fault collection staged with 300 um relays: hub_Wo -1040 from ot_dp_efault reducing ~2,700 um
   in one cycle; ot_dp_efault in 29/56 types.
7. sys_c lane L356 (-987, ~3 mm, no station): 9-10 stations or move it to the E side.
8. reset relay reach on sys_c and hub_Wo.
9. confirm KV-SYSC-1119 station rows are bound.
Stop list add: no route/repair of hub_Wo / sys_c; no route of D25e3 hgi kits. hgi v3-v8 -315..-353 = cland port path with ideal
clock (clk group >= -5 ps); their blocker is head-core hold = D26 lockups.
