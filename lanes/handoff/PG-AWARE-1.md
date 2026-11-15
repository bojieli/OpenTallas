# PG-AWARE-1 handoff (2026-11-14, FABLE-WAVE-REVIEW fix 6, DRT-0255 class)
Branch claude/pg-aware-1-1114 @8e7457814f (own clone localhost /home/ubuntu/wt-pg-aware-1, off origin/main 090996d67c), READY to ROOT-MERGE-63.

## Confirmation (read-only probes of 5_1_grt.odb + route.guide, ot-run, 22 builds)
Probe: <host>:/srv/opentallas-scratch2/claude/pg-aware-1/probe/<name>/{pga_probe.tcl,nets.txt,guides.txt,probe.log}; builds list intel2 ~/pg-aware-1/builds.txt.
40 DRT-0255 job logs 11-13 16:40..11-14 18:15 (~25 distinct builds); 22 DBs survive and were probed (incl. t49, t21f, t40f, coll_n form a).
Two PG mechanisms, both measured:
- (a) M7 PIN ON M7 PG TRACK. Root cause in the generator: pdngen measures -offset from CORE_AREA; gen_phys.PDN offsets are type-frame
  values (PART_PG_BANDS / mock_lef / pin_positions put the M7 pair centre at 4.32+8.64k). With the 4.32 core margin M5/M6 land right,
  M7 lands half a pitch off = on the plan's PG-free tracks where face pins go. sle_st_b_v2 x_fw_ctl_p2_i[464] (x 181.536, stripe pair
  centre 181.44), slice_station t49 ft2_i[324], kv3_io_cor o_serdes_W_tx_up_d1[1], kv3_io_cor_v1 strap_ca_k_ft6_i[2].
  186-1696 M5-M7 pin boxes per kit sit on spacing-illegal PG tracks.
- (b) CELL UNDER PG PAIR / CROSSING with the GRT guide forced through the pair's 0..1-legal-track M6 row (or M7 column) to reach it.
  Failing pin cells (repair buffers wire*/place*, output*, hold pads): t69 wire97392 (M5xM6), t25 place61109 (M5xM6), coll_n _25118_ +
  wire35999 (M5xM6), slw_hc2 wire4487 (M5xM6), t21f DFF q[234] (M5xM6); under the M6 pair only: t49 hold89466, kv io_cor output7268,
  stm_v3 wire265661/wire321971, coll_ucie _15096_, t40f wire98990, t21f place103370, t54 wire124856. Base rate: 3.9-5.8 % of cells under
  an M5xM6 crossing. Guides: every failing box has an M6 guide row (or M7 column) overlapping a PG pair (samelayer_pg 2).
- PG-TRACK-TRUTH alone does not clear it: 5 failing kits had it on (t69, t25, t54, kv io_cor_v1_b/c), and TYPE-QCCOLLN form a
  (coll_n, pgtt on, resumed GRT) failed DRT-0255 again on net35749.
- 15 of the 22 kits had OT_PG_TRACK_TRUTH off (stale src, R4) -> the rollout must also put pgtt on.
- Unclear 4: hd_mesh / sle_hc0 / t54 (macro pins, SRAM wd_in / ROM r1 = macro pin access) and hd_spn (net through a box, no pin).
- COORD Q (t40f/t21f, hold cells): the failing access points are NOT hold cells: t40f ft1_o_0 pin = repair buffer wire98990 under an
  M6 pair, ft0_o_3 = M7 guide column on an M7 pair; t21f = place103370 under M6 pair, DFF under M5xM6, two boxes only guide rows
  in M6 pairs (HB4 cells are present in 2 of 4 boxes as density, not the pin). Generator fix = PG (keep-out at crossings + M7 phase);
  no edge-ft keep-out is indicated by the data.

## Fix (both opt-in, gen env)
1. OT_PG_DIE_PHASE=1: gen_phys.pdn_die_phase rewrites the PDN-template stripe offsets to (type-frame offset - core origin) mod pitch;
   at margin 4.32 only M7 changes (4.128 -> 8.448); margin 0 kits byte-identical. No plan/pin change (pins already avoid the plan band).
2. OT_PG_CELL_KEEPOUT=1: pg_cell_keepout.tcl from grt_pre.tcl (before PG-TRACK-TRUTH): dbBlockage over every M5-pair x M6-pair crossing
   over the rows + detailed_placement (moves the few cells under them) before global_route, so GRT repair buffers are legalized off them;
   grt_post.tcl removes them before 5_1_grt.odb. config.mk export from RFLOW (default 0); kit_resume VAR_STAGE grt.
Tests: tools/die_plan/test_pg_aware.py (+ test_rflow_defaults RFLOW set). No new failures in the touched suites (7 pre-existing).

## Proof (ot-run, intel2 proof dirs /srv/opentallas-scratch2/claude/pg-aware-1/proof/<name>, logs intel2 ~/pg-aware-1/proof-logs/)
grt resume + pgtt + keepout: coll_n_pgtt, leaf_t69, leaf_t25, slw_hc2. floorplan resume + phase + pgtt + keepout: kv_io_cor_a, ss_t49.
Scripts intel2 ~/pg-aware-1/{fetch.sh,prep.py,launch_proof.sh}. Status: see RESULT lines below.

## Successor 11-14 19:4x-20:0x (resumed after 19:43 crash)
- Branch claude/pg-aware-1-1114 @288ada0041 (pushed; localhost /home/ubuntu/wt-pg-aware-1): 8e7457814f + f018f64729 (Fable 630-kit pin rule in
  landing_contract via tools/die_plan/pg_access.py, default ON for soft types at plan load; OT_PG_FACE_CUT=1 opt-in parent PG stripe cut 1.5 um
  before macro pin faces, gen_phys.pg_face_cuts/pg_face_cut_tcl) + 288ada0041 (lef_face_pins line scan, regex was 94 s on a 6 MB LEF).
- Proof set 2 (intel2 ~/pg-aware-1: prep2.py, fetch2.sh, proof2.sh, relaunch2.sh, launch_proof64.sh; tmux pga1-proof2), floorplan resume with
  phase + keepout + pgtt + WIDE_SPACING: fw_a/fw_b/fw_c (TYPE-QCCOLLN epyc10 fw forms), cbn_c (cbn_q11 c; tile has no M5-M7 face pins = 0 cuts),
  su_l0 (slw_su_l0__cl1a1c1f8f S3M2 attempt_10 kit, cland_tstart_in 174.9516 -> 167.392, fresh), hd_host_e_ws (HEAD-99 kits21z9 ws + face cut:
  u_epc W M6 421.86-423.36 x 72.39-539.83, S M5/M7). DO NOT run prep.py twice on a kit (pdn_die_phase is not idempotent); prep2 --skip-prep.
- Waiter: tmux pga1-waiter (waiter2.sh) -> ~/pg-aware-1/proof-logs/summary.tsv every 10 min, all 12 forms.
- Launch lesson: ot-run launched with nohup inside a short ssh session died (ssh 255 / systemd scope refused at session end): launch in tmux.
- Finding: wave su_l0 S3M2 kits still have cland_tstart_in at y 174.9516 (DRC 3 site); M7 phase bug puts 76 su_l0 face pins on M7 stripe tracks (1 with phase fix).
- 20:30 final sha 240cf2612f (rule gated to unsigned types + plan M7 phase; plans of record move only hd_host_e raw_0/raw_2); READY posted. Proofs: intel2 ~/pg-aware-1/proof-logs/summary.tsv. Next: RESULT when the first proof routes without DRT-0255.
- 20:55 stopped inline LEC (coll_n_pgtt, slw_hc2) by exact PID: proof copies lack lec_async files -> LEC ran synchronously before GRT. Branch unchanged 240cf2612f (test_bind failures were false, MERGE-QUEUE-1 re-test).
