# FABLE-FIX-QC-CBGLUE handoff (owner of the QC cb / glue family + coll_n)

Updated 2026-11-16 07:3x PST. Predecessor lane: QC-CBGLUE-1116 (Opus; RESULT 04:05, no handoff, clone epyc2 qc-cbglue-1116/wt clean, no commits).

## Root cause (MEASURED)
Class 1 (the large one): cbf_q01, cbf_q01_s2 and glue are the ONLY QC cb / glue types without clock.landing_local_resets
rows. All 16 other cb types have one `start_N` row per FSTART face flop + origin. So their FSTART face flops and count
origin share one START raw reset relay (cbf: u_cland_rst_a00_i, D rst_rl_487 @ (859, 1239), consumers at y = 2.7; glue:
rst_n_t2 = u_rrl_257 @ (697, 49), 32 face flops at y = 1466): 1.7 - 2.1 mm, 20 - 27 buffers, no logic.
glue -492 (GRT), cbf_q01 -1,916, cbf_q01_s2 -3,020 (CTS). Not a tree artefact.

## Fix 1 (DONE, waits for a die bind)
- Tool: tools/die_plan/fstart_reset_delta.py + test (3 tests), branch claude/fable-fix-qc-cbglue-1116 @e354fc3e4f6,
  clone epyc2:/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/repo. Gate GREEN (GATE main=9b911d91de7 pass=1/1, ran on epyc7).
  It uses the EXISTING plan option (landing_local_resets, same form as the other cb types): no generator change, 0 cycles.
- Rows: lanes/handoff/FABLE-FIX-QC-CBGLUE-rows.json (sha a4db996fb071): glue 5 leaves / 33 consumers, cbf_q01 3 / 3,
  cbf_q01_s2 4 / 6; hops relay -> leaf <= 220 um, leaf -> consumer <= 112 um. + reset_tree_anchor per type.
- Delta plans (epyc2 .../fable-fix-qc-cbglue/delta/): zz_s29_qc103_s4q6d_cbg1.json (sha bacd30b263f5) and
  zz_s29_qc103_s4q9b_cbg1.json (sha e3241e146e6d). Only those 3 types differ, only clock.landing_local_resets +
  clock.reset_tree_anchor. The 3 types are byte-equal in S4q6d and S4q9b, so the same rows fit both.
- Checked: the generator's own transform (clock_landings._local_resets) on the S4Q6DBQ bound wrappers accepts all rows:
  leaf depth 11 / 9 / 6 = the old reset depth, added cycles 0, 0 consumers left on the shared reset.
- NOT checked: timing. bind.py kit-rtl takes the wrapper from the bind, so a kit shows the leaves only after a die bind
  with the delta plan (tried: kit-rtl on the delta plan + old bind emits the old wrapper).
- Regenerate on another plan: python3 -I tools/die_plan/fstart_reset_delta.py SRC PLAN BIND_DIR OUT_PLAN REPORT --types cbf_q01,cbf_q01_s2,glue

## Open (design, not started by me)
2. glue sys_face t_go (rtl/qwen_split/qfd_sys_face_lctx3_core.sv line 613: t_go = (e_go || loop_go) && !face_fault;
   face_fault = 12-input OR, line 760): ~170 endpoints (u_cal_t.u_local oh / oh_b / cur / rep / cnt, tcyc[31:0]),
   worst -436, 17 buffers 450 - 480 ps. First measure the load box in the probe ODB. Form A (0 cycles, LEC-equal): kept
   copies of the face_fault OR + AND per consumer group. Form B (+1 cycle on t_go) only with a calendar-offset proof.
3. glue u_mu_dhobs.u_obs.mu_fault -> u_sys_face.obs_fault__ot_q (-330, 1,455 um) and obs_fault__ot_q -> obs_fault_q
   (-129, 1,512 um): one unregistered hop each across the type. Sticky fault: relay stations every <= 405 um (+k cycles, harmless).
4. glue d2d_rom u_end g_dly fk -> wcnt / store, store dq -> dout (-64..-152): 15 - 18 buffers, ~0 logic, wire 242 ps =
   distance inside d2d_rom. Measure the sink box before choosing region rows or a register.
5. cbx_q10 station sx -> 408-bit tap_d select (1.2 ns wire); cbn_q00 relay hop -78: re-read on the v2 tree (tt-keep) first.
6. coll_n: a19 placed clean (47 k cells, GRT 0 overflow), route DRT-0255 = old tree without C3b / die phase; a21 failed
   selfcontained on the pg_pair_cap.tcl comment path (fixed by TOOLS-CONVERGE selfc @5d0757cb716, v3 trees). No design
   change: relaunch on the v2/v3 tree (QC-DRT-1116 / QC-PINACCESS-O proof watch).

## Blockers
- QC event owner is FABLE-FIX-QC-KNEE-HC (S4q9c, epyc9 fable-fix-qc-knee-hc, BQ bind running 07:22). S4q9d = S4q9c + my rows is composed: epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/delta/zz_s29_qc103_s4q9d.json sha 9c0f8e750f07; DELTA posted 07:5x, needs ONE bind (S4q9c derived R8).
  FileNotFoundError sink_bins/hf1c/slw_su_c__cl19bb38ef.json in the scratch3 _q9 tree, last file 02:47). No die bind = no leaves in kits.
- QC v2 tree src_qc_pin_eb1e73448bd0 is on epyc10 only (tree_switch_qwen_compute.json 06:07).

## Next
1. Die owner binds S4q9b + cbg1 rows (or S4q6d + cbg1), LATCHECK unchanged expected (0 cycles); then wave relaunch of
   cbf_q01, cbf_q01_s2, glue on the v2 tree; read post-CTS gate: the rawreset->fstart class must be gone.
2. Then items 2 - 4 on the glue v2 kit numbers (QC-CBGLUE-1116 implements, bench + LEC).
