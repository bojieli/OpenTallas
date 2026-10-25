# KV-TOK (epyc2)
## PARKED 18:56 PDT 2026-10-24
- Branch claude/kv-tok-1024 @5a351c94dd (pushed). main has efd14deb5c (vehicle + sub-benches + root causes).
- Live jobs: none of mine on epyc2 (old O0 sims killed per COORD; bo1tok runs stopped). Forks B (claude/kv-tok-b-1024, ~/wt/kv-tok-b)
  and C (claude/kv-tok-c-1024, ~/wt/kv-tok-c) PARKED @b1131f6fa8 = base: no RTL written yet, no jobs; plans recorded.
- Done: A tool physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py (96 kvpc rst_n -> i_host_hbm_rst_n_q[0]; not yet
  in a build). m2 mutant plusarg +MUT_RL24=<part> in the PHY bench.
- Findings this step: B is bigger than "seal before boot": the calendar only reserves static columns while a layer runs
  (go), and seal is sticky (one image) -> fix must be a controller boot window (static column without reservation +
  raw-return expectation) before the first calendar go (fork B). m4 mutant: re-compiling the boot image from
  die_ages_bound_padded.json + relay_stages_bound.json does NOT reproduce image_kv41 (targets 1/3/11/13 differ) ->
  m4 needs either the original run_rebind.sh inputs or a word patch + re-encode (encoder not yet located). NOT RUN.
- Reset rule: A uses the synchronously delivered HBM lane (rule style); die-wide spine pipelining for KV RTL follows
  KV-G3 kit_rsync (physical) -- functional ot_dp_rsync unchanged in sim. OWNER? whether the bound RTL itself must
  carry the pipelined spine before boot benches.
- Next: collect B/C fork branches -> kv43 = kv42_bo1 + A + B + C(+C1) full hier rebuild (~32 min, 35 GB) -> boot smoke
  nominal + MUT_FRAME, token nominal + m1 (+MUT_CMD_LATE) m2 (+MUT_RL24) m3 (PRELOAD_ARGS --mut-kswap) m4 (image).
- OWNER?: KV bind ownership / bind.py re-run impossible (bound_netlist.json lost); C2 clock plan (sys_SD on core).
## COORD rulings A/B/C1/C2 (received ~19:00) -- IN PROGRESS
- old O0 sims 434532/434535/466382 KILLED (per COORD).
- A: physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py (bind-level edit, bind.py re-run impossible: KV
  bound_netlist.json lost): 96 kvpc instances in 24 pc part types .rst_n -> i_host_hbm_rst_n_q[0] (pipelined synchronous
  HBM reset lane, reset-rule style; slg keeps die reset). DONE (tool), integration pending.
- B (controller boot window, miter+mutant) and C1+C2 (coherent valid/data delay + async FIFOs at HOST adapter, bench PHY
  model CDC) running as KV-TOK forks on branches claude/kv-tok-b-1024 / claude/kv-tok-c-1024.
- Next: kv43 build (kv42_bo1 + A + B + C), boot smoke nominal + frame mutant, token nominal + m1..m4.
## MERGED main efd14deb5c 14:2x (tools + findings; verdicts NOT RUN)
## RESUMED 12:15 PDT 2026-10-24 (after 08:50-12:04 usage limit), adopted from Codex:
- root cause (Codex): legacy boot_go launches D2D admission 76 cycles before the boot config is ready (d2d fault cyc 539);
  BO1 opt-in source on main a2757edd53 (merged into claude/kv-tok-1024 @84d6f885b4).
- kv42_o1_perf / kv42_parallel16_perf collected: both reproduce boot_go 453 / fwd_epoch 463 / dcal_fault 539; speed
  O1 1-thread 4500 cyc / 994 s user (16:34 wall), --threads 16 top 4500 cyc in 4:26 wall (~17 cyc/s).
- kv42_bo1 (epyc2 scratch2 codex-qwen/kv42_bo1): top re-verilated with --threads 16 --hierarchical-threads 16 (1:47),
  single-thread binary kept as Vtb_kvslice.bo1_single. RUNNING 12:14: scratch2/claude/kv-tok/bo1tok/{nominal (FAR=1,
  preload, POST 300000), mut_frame (+MUT_FRAME=100)}.
- old O0 sims boot42/tok42 (pids 434532/434535/466382, root disk) left alive per Codex note.
 — branch claude/kv-tok-1024 (= tokj-kvslice-1023 + main), worktree localhost ~/wt/kv-tok, epyc2 ~/wt/kv-tok
## Status 2026-10-24 08:05 PDT
- ROOT CAUSE of the 10-23 top blow-up: Verilator 5.050 never substitutes a hier_block module that HAS parameters
  (minimal test localhost ~/ot-scratch/kv-tok/hiertest) -> strip_default_params.py (header parameter->localparam, drop the
  71 top #() overrides; all 2,582 overrides == defaults, exact). Committed 885afd56bc.
- PV boot item CLOSED as a record: kv42 = kv41 + PV W request-lane pads (8 ports, 900 flops) = bind/bound_kv42 (bb5ffd5b8):
  post-bind INNER-delay edit (netlist binder2-1023/kv_bound lost -> verify/port-bind NOT RE-RUN); bind_post regen PASS
  OK 17 / WARN 3 (VPORT_DQ WARN -> OK); boot image = image_kv41 by construction (literal prep re-run NOT RUN: rtl6 GEN
  inputs lost).
- BUILD epyc2:/srv/opentallas-scratch/claude/kv-tok/kv42_build (kv42 tree, 79 hier blocks, J=64, started 07:33 PDT): running.
- Token-phase bench written (c890c5d071+): compute-die far end on UCIe (real qfd_d2d_static + cal_seq on the kv41 pair image,
  record codec, KVN transport; RESULT vs gold of checkpoint_service_vectors T=256), post-boot observation, HBM preload
  generator (CONTRACT map v2) + HBM address log for the map self-check. NOT RUN yet.
## Next
- boot replay smoke nominal + frame mutant on kv42_build; POST observation of the die's token-start chain; then FAR=1 token.
## OWNER?
(none)

## 13:40 BO1 boot findings (whole-die bench + flat sub-benches; all NOT a token verdict yet)
- BO1 removes the D2D fault: no dcal/d2d fault in 20k+ cycles (legacy faulted at 539). D2D admission now waits.
- BOOT STALL (independent of BO1, also in legacy runs): HOST accepts 528/7161 frames, boot_pr never changes, no image
  replayed; die_rst_n stays 0. HBM cold boot: boot_go reaches all 4 chain ends at cyc 506, PHY sees only REFPB
  (row op 6), never a WR; at cyc ~20590 all 128 slices report done, ok 0, fault 1 (qkd_hbm_boot_pc TIMEOUT 20000).
- ROOT CAUSE A (proven, flat pc_part sub-bench tools/qwen_layerbench/kv_dieslice/pcpart): the kvpc reset spine
  ri_kvpc0_rst_n is bound to HOST die_rst_n (x_hub_Wi_rs_host_die_rst_n_*), and the slice boot-window face
  qkd_static_kv_pc_es_merge_b (hq[0]/es[0] async reset by rs_q) lives in kvpc => the scratch WR dies at the merge;
  HOST (ot_qwen_sys_rst_seq) releases die_rst_n only after every slice boot_done&ok => deadlock by construction.
- FINDING B: with kvpc on hbm_rst_n (+KVPC_RST_HBM sub-bench / +DIAG_KVPC_RST_HBM whole die) the word reaches the
  controller (es[0] in) but is never issued: qkd_controller_hbm_calendar not sealed (reserved_static_col /
  reserved_write_col 0 in 2800 cycles) -- the calendar comes from the boot image, i.e. after die reset. Same deadlock class.
- ROOT CAUSE C (proven, hub_Wi partition record/replay, tools/qwen_layerbench/kv_dieslice/partrec; replay reproduces
  the whole-die HOST reset/boot_go edges exactly): no boot frame ever reaches the HOST peer link (raw_rx 0); the HOST
  link adapter (ot_qfd_link_adapter in qfd_link_adp512_split) raises f_seq on its first received flit.
  C1 BIND BUG: in kv3_hub_Wi_part the FDI valid (sys_SW rx_v & sys_SE rx_v, kv_phy_slices.sv:197 AND) goes through
     ot_dp_dly D=4 (u_d4_serdes_host_u_sub_and_kv_phy_slices_sv_197_2_Y) but the flit data (i_serdes_*_rx_flit_q, same
     lane word L2048 as rx_v) does not => valid lands on the flit 4 positions later (seq +4 per received flit, observed).
  C2 CLOCKING: the SerDes FDI crosses core-clock partition lanes (sys_SW/SE + hub_Wi ot_dp_st on clk_core 1.2 GHz)
     into the HOST adapter on clk_phy 0.959 GHz with no synchroniser => 1-core-cycle valid pulses are missed.
  C3 BENCH (fixed 0f/tb): board link came up before the die's HOST left reset => board FDI sequence ahead (first rx
     seq 35). tb now raises host_up after die host_rst_n + both SerDes tx_up; first rx is then seq 7 (= C1 skew only).
- OWNER? C1/C2 are bind/clock-plan decisions (bind.py delay balancing on a split valid; sys_SD partition clock).
- Runs stopped: bo1tok nominal/mut_frame (stalled at 528 frames by A/C, 60k cycles, no verdict). Old O0 sims
  434532/434535/466382 left alive per Codex note (also stalled; OWNER? may kill).
- Verdict counts: boot smoke NOT RUN to verdict (blocked by A, B, C1, C2); token tests (nominal + m1..m4) NOT RUN.
- OWNER? boot order of the bound KV die: which reset owns kvpc/es_merge + the HBM calendar during the HBM cold check
  (bind reset_spines assignment vs HOST rst_seq order). Not fixable bench-side without changing the design.
## CODEX notes
- Collected kv42 build: remake2 exit 0; boot nominal/mut_frame and FAR=1 token processes remain live CPU-bound on epyc2:/srv/opentallas-scratch/claude/kv-tok/{boot42,tok42}. No finished verdict yet. Root-disk run dirs are live and cannot be moved; new work will use scratch2. Next collect boot/token verdict, diagnose first fault.

CODEX progress: BO1opt-in source mergedmaina2757edd53, variantdefault0; sixrealbc4modesPASS+fullHOSTclosurelintPASS. ActualHOSTacceptedprogramme eventretainsHBMboot_go. NewdeclaredsourceL643actual35edges=28transport+7pad; wrapper/census/rewirecandidate /srv/opentallas-scratch/claude/codex-qwen/boot_bo1_bound_candidate. CanonicaladoptionHELDfreshrebind/R8/fulltoken/physical. IdenticalO1buildLIVEepyc2scratch2/claude/codex-qwen/kv42_o1 (71+/79hiermodulesdone), old3jobsuntouched.
- 2026-10-24 18:51 PDT FROM ELEM-QK: cleaned epyc2:/srv/opentallas-scratch2/claude/codex-qwen (no process used it): removed obj/ of kv42_o1, kv42_parallel16, kv42_bo1 (Verilator build trees, ~106 GB); kept every binary: <dir>/Vtb_kvslice.obj_final (the obj/ final exe), Vtb_kvslice.boot, kv42_bo1/Vtb_kvslice.{bo1_single,p16_run1}, build scripts/logs, boot_bo1_bound_candidate. A TOP-only rebuild now needs a fresh build (the C1/C2 fixes need one anyway).
## KV-TOK fork B (boot fix B: controller boot window) PARKED 2026-10-24
- branch claude/kv-tok-b-1024 @b1131f6fa8 (= kv-tok-1024 tip, worktree ~/wt/kv-tok-b); NO changes yet, no live jobs.
- Plan (not started): boot window = calendar never started (static_owner never set): allow static column without
  reserved_static_col in ot_qkd_static_kv_timing (via new port, all instantiations tied) and exempt/expect boot reads
  in qkd_ctrl_pc_host_static_core ELASTIC f_raw; prove with lockstep miter (window disabled == original), pcpart
  +KVPC_RST_HBM shows WR+RD + soo=1, mutant (window off) FAILs. Exact staged modules: extra__...static_kv_20261014/
  qkd_ctrl_pc_nc.sv (u_ctrl.u_sched.u_ctl) to be confirmed.
- C2 fork (claude/kv-tok-c-1024 @b1131f6fa8, worktree ~/wt/kv-tok-c) PARKED before any change: no live jobs. Findings so far:
  hub_Wi PHY face = u_host .phy_rx_flit({i_serdes_E_rx_flit_q[520:0], i_serdes_W_rx_flit_q[521:0]}) (core clk lanes),
  .phy_rx_v(d4 of W.rx_v & E.rx_v, ot_dp_dly D=4 -- C1 skew), .phy_tx_* -> u_bout_o_host_fdi (core clk), adapter ck_phy
  = clk_clk_phy; u_host already has ck_phy_rx_w=clk_clk_phy/ck_phy_rx_r=clk (qkd_host_phy_cdc5 sits AFTER the adapter).
  Next: kv_host_fdi_cdc.py inserting async FIFOs (rx clk->clk_clk_phy before .phy_rx_*, tx clk_clk_phy->clk after
  .phy_tx_*; valid+data through one delay), fix kvs_link_phy_models.sv model-level CDC, sub-bench + mutant.

## TOK-QK (steward of KV-TOK/TOK-QW/QC-TOK token side) -- RESUMED 2026-10-24 19:29 PDT
- 2026-10-24 19:29 PDT TOK-QK: forks B/C had NO commits (both @b1131f6fa8). Sub-agents launched: B (controller boot window, claude/kv-tok-b-1024,
  work epyc2 scratch2/claude/kv-tok/B) and C1+C2 (claude/kv-tok-c-1024, epyc2 scratch2/claude/kv-tok/C). C2 DECISION (lane lead):
  ONE CDC per direction at the SerDes boundary = async FIFO (gray pointers + 2-flop syncs, valid+data written together);
  all on-die lanes on core clock; rate/flow absorbed only at the off-die host link (elastic allowed there by owner rule);
  remove the unsynchronised crossings instead of stacking a second CDC. C1 durable fix in bind.py (+test) for lane KV's rebind.
- Next (me): kv43 staged tree = kv42 + BO1 hub_Wi + A (+B +C via kv43/apply_{B,C}.sh), fresh hier build via ot-run on epyc2.

## REQUESTS from TOK-QK to lane KV (KV re-bind from scratch, owner decision 9) -- 2026-10-24 19:34 PDT (will be extended when B/C land)
Vehicle recipe: tools/qwen_layerbench/kv_dieslice/{stage_src.sh BIND_DIR OUT, build.sh STAGED OUT (J=64, ~32 min, ~35-45 GB),
rebuild_top.sh (THREADS=16)} on claude/kv-tok-1024 @adb22f9008; kv43/stage_kv43.sh shows the post-bind deltas the rebind must
make natively. Hand me the new bind dir (bind.f + rtl/) and I stage + build + run boot/token + mutants on it.
- KV-R1 (fix A): u_kvpc<k>.rst_n of every kv3_pc* part (96 inst, 24 types) = the delivered HBM reset (host.hbm_rst_n lane,
  i_host_hbm_rst_n_q[0]), NOT ri_kvpc0 = host.die_rst_n; u_slg keeps die reset. Tool: physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py.
- KV-R2 (BO1): declare the BO1 HOST boot-event source (main a2757edd53, opt-in variant) ON: qkd_host_root_admission_obsx_bo1.sv +
  qkd_d2d_boot_event_bridge.sv (L643, 0 data wires changed). Candidate: epyc2:/srv/opentallas-scratch2/claude/codex-qwen/boot_bo1_bound_candidate.
- KV-R3 (F6): KV d2d u_d2d_kv (qkd_d2d_static*_sfm) parameter OBS1_COMPAT=1 (main 60c21cd01d; 35-layer exchange PASS) -- TOK-QK adopts it.
- KV-R4 (F7): KV dcal compiled image = the matching pair results/rtl/qwen_rom_pair_candidate_1024 (dc11eabc33: period 293,376,
  seam C 0a010308 / K 03030443; full-frame exact + slot mutant caught). TOK-QK adopts this pair for BOTH dies (KV image_kv41
  dcal mu period 249,600 is stale). TXDP_K 03030443 / D2D_KV_TX_LAT 67 unchanged (K1/K2 OK).
- KV-R5 (B, C1, C2): RTL + bind.py changes coming from TOK-QK sub-agents (branches claude/kv-tok-b-1024, claude/kv-tok-c-1024).
## REQUESTS from TOK-QK to lane QC (compute re-bind on the capacity plan)
- QC-R1 (F1): param_regen rule glue.u_d2d_rom TXDP = 32'h0a010308 (regen D2D_TXDP_C [8,3,1,10]; bound_r8 has 0 -> D2D_TXDP_NOT_COMPILED trap).
- QC-R2 (F7): compute sys_face qfd_d2d_cal_seq_ovl_rope images = results/rtl/qwen_rom_pair_candidate_1024/ovl_release_rope (same pair as KV-R4).
- QC-R3 (F5): ot_sram_1r1w_64x137_m1_r2c2_p192 macro name (main b1e16de8f0) must elaborate in the bound glue.
- When the capacity rebind lands: tell TOK-QK the bind dir; I re-run xt1 both (lead 16 + schedule gate + mutants) on it.
- 2026-10-24 20:07 PDT TOK-QK: C1+C2 DONE on claude/kv-tok-c-1024 @db2126db9 (not merged). C2: one async FIFO per direction AT THE PHY (ot_fdi_phy_cdc,
  gray+2-flop, in sys_SW/SE PHY halves); hub_Wi (adapter, pad, cdc5) all on core; TX paced 19/24 core cycles (0.950 GHz < 0.959,
  -0.92% link TX rate, static, no backpressure); ot_fdi_join2 order-join replaces AND + D=4. C1 in bind.py (glue transport absorbed,
  asbuilt.split_bus_join opt-in, r8 bus_join; tests 35/35 PASS). Proof: hub_Wi closed-loop 18/18 PASS raw_rx 7161/7161 in order
  (8 phases x 2 skews + PHY 1.000/1.050 ns), mutants 6/6 FAIL; CDC FIFO unit 30/30 + mutants 9/9 FAIL. Latency RX ~5.6 core cyc,
  TX ~4.7 PHY cyc, join +1-2. Vehicle: kv43/apply_C.sh.
  KV-R6 (rebind): new bind.py + asbuilt.split_bus_join ["ot_qfd_serdes_112g_x12_phy_s2"]; kv_phy_slices s2 model gets clk_phy +
  ot_fdi_phy_cdc + join2 + tx_pace; die_rtl6.v: serdes_host on PHY clock, host ck_pad/ck_phy0-7/ck_phy_rx_w/ck_phy_tx_r -> core;
  clocks_v32: clk_phy taps sys_SW/SE, not hub_Wi.
2026-10-24 20:17 PDT RESET -> TOK-QK: boot cost of the pipelined reset (OWNER RESET RULE): all flops release N+E+1+K clocks after die rst_n deasserts: qwen_compute 78, qwen_kvsys 60 (2-flop root sync included). Benches: hold reset >= that, and count it once in boot cycles (one-time, not per token).
- 2026-10-24 20:38 PDT TOK-QK: B DONE on claude/kv-tok-b-1024 @d08459bf0 (RTL 865fd8826): scheduler boot_win flop (open from reset until the first
  compiled layer go takes static_cmd_owner; never reopens), boot columns checked like reserved ones (expected_sr + per-read boot_raw
  slot), ot_qkd_static_kv_timing.boot_static_col; ~28 flops/PC, 0 mission cycles. Lockstep miter PASS 12+2 runs 0 mismatches,
  never-close mutant FAIL 51,483; pcpart (A+B, HCK_IS_CLK) 4/4 slices done&ok ~179-193 core cyc after boot_go; mutants (orig,
  window off, no observer exp., no boot_raw) all FAIL. Bench fix: HBM PHY model WL=5 (write data alignment).
  NEW FINDING D: kv3_pc_part registers HBM PHY po/pi lanes on core clk (should be clk_hbm) -> with real 0.977 GHz HBM clock PC1/PC3
  see a return twice -> f_raw. Sub-agent D launched (claude/kv-tok-d-1024: bind lane clock by endpoint domain + audit + apply_D).
  KV-R7 (rebind): re-harden kvpc tiles (qkd_kvs_pc* RTL changed by B); HBM reset release must precede boot_go by >= hgo (~118 HBM cyc).
  B legacy qkd_ctrl_pc_host_static_core (not on any die) has boot_window tied 1'b0 -- accepted (not bound).
- 2026-10-24 20:38 PDT TOK-QK: B+C merged into claude/kv-tok-1024 @18ab3575e. kv43abc (A+B+C) staged + building epyc2 (ot-run oth-ubuntu-2298447-1792899484,
  scratch2/claude/kv-tok/kv43abc_build); kv43a (A only) build also running (recipe check). D will need one more build (kv43abcd).

## CODEX notes 2026-10-24 21:08 PDT
- CODEX took over: integrate B+C+D and collect kv43 on codex/token-qk-1024. epyc2 scratch2/claude/kv-tok/kv43abc_build remains live (hg_v1 C++ compile progressing); no terminal build verdict. D port-domain pilot derived kvpc ck/hck successfully; broader pd2 FAIL is tool elaboration of unrelated host crossmodule g_mu.program_fault, not RTL failure. Child kv_d_clock owns scoped elaboration, durable binder and apply_D. Physical kv_bind owns native kv44 (RT32/RL64) and image regen; bridge build precedes final kv44 token. Next: D smallest exact gate, kv43abcd build and boot/token/mutants.

## CODEX notes 2026-10-24 21:10 PDT
- CODEX took over D on codex/kv-d-clock-1024; staged apply_D.py/.sh authored (untested successor), ten HBM PHY face flops per24PC types core->HBM, 0stages. phy partitions already HBM clock. Gate NOT RUN; parked for Claude reset before launching jobs. Existing pd2 FAIL from unrelated HOST crossmodule reference, pd1 head-domain derivation valid.
- 2026-10-24 21:14 PDT TOK-QK: resumed after account switch; D agent resumed (adopts Codex codex/kv-d-clock-1024 @7cf1d726b apply_D); kv43abc build still live epyc2.
- 2026-10-24 21:34 PDT TOK-QK: owner decisions 13/14 applied to token work: D sub-agent re-scoped (kvs_pc controller on die clock -> the one CDC sits at
  the PHY/DFI boundary; pc lanes stay core). Boot/token benches: start on the explicit start broadcast, not the reset edge; datapath
  flops unreset -> next KV vehicle build (on kv44 bound top) uses --x-initial unique + random init (+verilator+rand+reset+2) so no
  bench relies on datapath reset values. kv43abc (pre-13/14 vehicle) kept as diagnostic of A/B/C integration only.
- 2026-10-24 22:21 PDT TOK-QK: D DONE claude/kv-tok-d-1024 @644381b68 (merged into claude/kv-tok-1024 @52f9f945d). Codex apply_D NOT adopted (10 face
  flops only; wrong direction under decision 14). No FIFO on DFI po/pi (fixed RL/WL offsets, ELASTIC=0) -> DFI ratio-locked.
  apply_D default dfi-core (decision 14): 68 clk_clk_hbm_<Q> pins -> clk_core, 0 lane changes; fallback --mode hbm-lanes (327 lane regs
  in 25 types -> clk_hbm, per-partition HBM reset sync, epoch via ot_dp_lsync). bind.py lane_clock "endpoint" (LANE_CDC /
  PORT_DOMAIN_UNDECLARED fail the bind) + port_domains.py + lane_clock_audit.py (kv43abc: 201 type lanes / 81,464 die bits wrong
  clock, no other bare crossings, 251 lanes unresolved = host leaf). pcpart: dfi-core 4/4 done&ok; hbm-lanes 16/16 sweep PASS;
  old binding mutant FAIL 12/16. Reset findings (out of D scope, to RESET/KV): hbm_rst_n core->HBM, kvpc hrst single flop on pll_hbm,
  phy ft chain core reset over HBM stations.
  KV-R8 (rebind, 14a): hck/grp_r2c hck/ctrl_kc.pll_hbm/PHY clk from core PLL; bind.py lane_clock endpoint + port_domains_kv43.json;
  PHY model makes HBM clock from a ratio PLL. DFI-ratio check must recompile calendar constants in 833 ps cycles (1:1 example:
  RL 23->29, WL 5->7, tRCD 19->24, tRP 16->20, tRAS 28->35, tREFI 3808->4679, tRFC 342->421 ...; + BRAW, PHYSICAL_CMD_EDGES, WDONE/CVL).
- 2026-10-24 22:21 PDT TOK-QK: kv43abcd (A+B+C+D dfi-core, XINIT=unique for decision 13) staged + building epyc2 (scratch2/claude/kv-tok/kv43abcd_build,
  epyc1 ~/wt/tok-qw-logs/kv43abcd_build3.otrun.log). kv43abc build still live (diagnostic). Next: run_suite on kv43abcd with
  RUNARGS="+verilator+rand+reset+2"; NOTE the kv43 vehicle still uses the kv41 boot image (calendar constants in HBM edges) -- with
  dfi-core the PHY bench model runs RL/WL in core cycles, so a boot/token PASS of record waits for lane KV's recompiled image on kv44.
