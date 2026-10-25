# KV-TOK (epyc2)
## PARKED 18:56 PDT 2026-10-24
- Branch claude/kv-tok-1024 @5a351c94dd (pushed). main has efd14deb5c (vehicle + sub-benches + root causes).
- Live jobs: none of mine on epyc2 (old O0 sims killed per COORD; bo1tok runs stopped). Forks B (claude/kv-tok-b-1024)
  and C (claude/kv-tok-c-1024) told to park + push; see fork lines below once reported.
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
