# OPUS-FIX-S81-BKSEL-R3 (11-20): bk_sel__t2 J6 rows + u_c A3P view

Lane dirs: epyc7 `/srv/opentallas-scratch2/claude/opus-fix-s81-bksel-r3` (all work); hub `~/opus-fix-s81-bksel-r3` (ot-run client logs).
Lane clone: epyc7 lane dir `repo`, branch claude/opus-fix-s81-bksel-r3 (TKR commit 3ba3029de4, pushed as main 40458a43e16).
Predecessor: lanes/handoff/FABLE-FIX-S81-BKSEL-R2.md. J6 consumer: S81-J6-ASSEMBLY.

## u_c (dsdv_bksel_c) A3P view
- Old kit rfda3p (FABLE lane dir ucore/dsdv_bksel_c_rfda3p) CANNOT sign. Its TT -46.64 / 212 ep is NOT on output ports
  (vd ports +103.8). It is internal: u_c.flt[1] -> |flt_new -> take -> lpop -> lq[l][e]. The routed-STA census
  (census/census_tt.txt) shows all 212 come from flt; the next startpoint is ts_r at -12.1. Its run_kit is wedged in
  `docker run` after the container ended (unit oth-ubuntu-2237101-1795198176). Left alone.
- Fix TKR (0 cycles): dsfd_selt_c parameter TKR 1 keeps |(flt & ~flt_rep) in a flop (fblk). dsdv_bksel_c passes TKR;
  dsdv_bk_sel sets .TKR(1) only under OT_BKQ_ECO3 + OT_BKSEL_A3P (literal params). On main as 40458a43e16.
  Proof: proof_tkr/ (yosys sat -tempinduct: invariant SUCCESS; mutant OT_RFD_MUT_TKR FAIL). The bk bench passes eco3/a3p,
  but it has no fault traffic, so the mutant also passes there; the proof is the evidence.
- New kit ucore/dsdv_bksel_c_rfda3pt (recipe recipes_a3pt.json, kit_hash 2d372d08b57505de): unit
  oth-ubuntu-1875375-1795217442 on epyc7, run_kit finish 48 16. LEC EQUIVALENT 31,697/31,697. In GRT at 18:0x.
- Next: read signoff/signoff.json (gate: DRC 0, TT >= -42, FF hold >= 0). Then export the view as
  cores/views/bksel_c_a3pt_1120 (LEF, tt/ff lib, built params incl. TKR 1), archive it like dsdv_bksel_q__fx6_hei3_1116,
  and add the row hard_cores u_bk_sel.u_sel.u_c lef/lib -> that view. If TT still misses, the census shows the next class
  (ts_r -12) is well inside the gate, so it is not expected to.

## bk_sel__t2 rows (type-local; apply on the J6 base)
1. A3P station sites: rows_stn.json (rows_stn.py): relay_sites, 38,852 keys u_core.u_sel.u_stn_{c,s,o,l}.g_r.r[j][b] / .q[b].
   Every stage sits on a grid-routed path around the cores. Designed max hop 318.6 um (q0 t_o detour; < 405); the rest
   are <= 276 um. 0 cycles, no bind change. Proven placed: OT_RELAY_SITES placed 38852 FIRM, 0 unmatched (pilot_r3a).
2. Face-bus / hub rows: rows_face.json (rows_face.py, made by a helper): 3,671 hub relay_sites (u_vm.r/o, u_bin_ca/cb/xtier_i0,
   u_rs, u_rn, vn, fq), 12 bus internal_stations (71 FIRM stations), 12 lanes fixed_cycles 0 -> +1..+11, latency.lanes
   fixed/natural/cycles raised by the same amounts. COMPILER RISK: the six vmux inputs change latency by different amounts,
   so the schedule must be recompiled from the new LAT_* and re-run through the token sim. A variant rows_face_ugmx.json
   (u_g MX) needs a PINBAND/G0 check and recomputed u_stn_l sites, so it is not used.
3. Reset anchors: no plan row needed (FIRM-sited flops take the nearest equal-depth reset tap). The hard-core reset pins
   (rst_n_t22, 1.0-1.65 mm to the quarters) need RTL or bind work.
4. Not fixable by rows; these need RTL: the u_tx.lo -> lp_q -> u_vm loop (~1.2 mm, 1 register), dst/lpe gating (~1.4 mm),
   tx_st[0] -> fault (~740 um), u_g.vo_s -> u_tx.vo (~400 um R0).
Private proof of all rows: tree_r3b plan 7b1686b24b02 (J3 j3src + BK-PLACE/A3P rows + TKR RTL + rows 1-2). Result: ELAB 0,
strict BIND 0 errors (398 partitions, 873 crossings), LATCHECK 873/873 PASS, G0 2 errors (the baseline count), PRE PASS
(build_r3b, hub log build_r3b.otrun.log).

## In flight (epyc7; clients on the hub, logs in ~/opus-fix-s81-bksel-r3)
- ucore_a3pt.otrun.log: u_c kit rfda3pt to sign-off (unit oth-ubuntu-1875375-1795217442).
- geom_r3a.otrun.log: geometry dump + AUTO-GEOM of the relay_sites-only placement (pilot_r3a 3_place.odb), out geom_r3a/.
  Waiting for epyc7 memory.
- gen_r3b.otrun.log: bk_sel__t2 GEN on the full-row bind (pilot_r3b). Waiting for epyc7 memory.
  Next: run pilot_r3b/bk_sel__t2/gen/run_kit.sh <kit> place 48 16, then geom_check.sh, then the hop scan
  (python3 -I /srv/opentallas-scratch2/claude/fable-fix-s81-bksel-r2/r2r.py geom.tsv 300 70), then GRT TT.
- No placed hop maximum is measured yet. The last measured is 2,591 um (R2 form, no sites).

## Next
1. Read geom_r3a (stations sited) and the pilot_r3b placement; post r2r max / count by family.
2. Send rows 1-2 (+ the u_c view row once signed, + main 40458a43e16) to S81-J6-ASSEMBLY as one rows file.
   Flag the LAT_* compile/token-sim requirement of row 2.
3. Stray: epyc7 lane dir stray/ holds 2 tiny .ys files I wrote by mistake into ~ (moved, not deleted).
- Plan inputs that exist only in the snapshot (511 paths: macro LEF/lib/bb, clock sink_bins ...) are absolute paths into the
  sealed snapshot (L/prep/source_plan.json sha f4d3c7da72d8; relative form L/plan/plan_tr2_rel.json).
- GEN PASS on main 3553de9af815 = HEAD tools re-pin proof at gen level (gen log L/gen_tr2.otrun.log). Kit L/tr2/gen/hd_lep0N:
  no OT_GPL_SPARSE_OVERFLOW / GPL -overflow (r14 had 0.25), 0 default [-169.8, 0] tap lines, OT_SIGNOFF_SDC_SHA f96f844aa8bf983b.
- RUNNING: ot-run unit oth-ubuntu-519406-1795227351 on epyc10 (client pid in L/tr2.otrun.pid, log L/tr2.otrun.log),
  run_kit.sh GOAL=route (synth -> sign-off), --priority die --mem 96 --threads 16. epyc7 had ~160 GB free with tr1/tr1b, so epyc10.

## Next
1. ot-wait the unit; read FF hold before repair (expect far fewer than r14's 25.8k ends), pre-GRT hold cells, GRT TT, sign-off.
2. If signed: export to AGIdock + rtx-pro ~/signed-export-1114 (as other HEAD types), post with gen sha 3553de9af815.
3. If it fails on the flop->core class (late lep_pair cores, kit leg ~142 ps + ETM 607 vs 553): the structural fix is die
   delivery of clk_c0..c3 earlier by the kit leg, or the core clock pin at the port; lockups (LOCKUP-STATION-1130) only if a
   large flop-pair class remains.
4. tr1 (GRT) and tr1b (CTS read) in the Fable dir: reads only; neither is a sign-off form.
5. Note: I removed an empty partial L/tr2/rtl with rm -rf once (my own failed output); use ot-delete only.

## UPDATE 11-20 19:3x PST (supersedes "RUNNING" above)
- tr2 (main-tools kit) DIED at FAIL_PREFLOOR kit_preflight: reset_tree_coherence (main gen's reset_tree.tcl keys vs the
  snapshot-staged RTL wrapper, e.g. u_rrl_24 key rst_n_t17 vs RTL q rst_n_t51; u_srl_* q MISSING). Retrying with main's own
  RTL export (L/rtlmain.sh, cone widened with physical/asap7_memory_macros*) fails in main's bootstrap gen:
  "clock landing: hd_ctl.a_tx_o: writer START raw reset rst_rl_22 has no registered wavefront driver".
  => HEAD tools re-pin proof FAILS on the r13r NOMCAP plan: main gen refuses the plan (hd_ctl START reset rule) and its
  reset tree does not match the published r13r RTL. Needs a HEAD plan event (HEAD-R14 / COORD), not a lep0N kit fix.
- tr2s = SIGN-OFF CANDIDATE: same plan L/prep/source_plan.json (f4d3c7da72d8) generated with the SNAPSHOT tools
  (manifest 6d3c0e3e43d9) and OT_GPL_SPARSE_OVERFLOW=0 OT_GPL_OVERFLOW=0 (explicit env = d98908b665 behaviour: no
  sparse exit; config.mk has no sparse/overflow lines). 0 default tap lines; clk_t191..t246 priced.
  OT_SIGNOFF_SDC_SHA b6b795a7245aee53. KIT_PREFLIGHT PASS. RUNNING ot-run unit oth-ubuntu-1990134-1795230761 on epyc10
  (client pid L/tr2s.otrun.pid, log L/tr2s.otrun.log), GOAL=route (synth -> sign-off), die priority, 96 GB / 16 thr.
  OT_LANE=OPUS-FIX-HEAD-LEP0N-R2 set: ot-run posts DONE/DIED.
- Next: read kit L/tr2s/gen/hd_lep0N hold_gate.log / pregrt_ff_hold.log (r14: -388.93 on 25,803 FF ends before repair),
  GRT TT, signoff.json. On SIGNED: autoclean archive ingests to AGIdock (signed_store); rtx-pro copy with
  `signed_store.py stage --host rtx-pro --dest ~/signed-export-1114/head --die s81_head --key hd_lep0N` (or export_view.py
  as KV lanes did). If r14 signs off first, r14 wins; tr2s then is a second sign-off of the same type.

## UPDATE 11-21 01:2x PST
- COORD: HEAD-PLAN-R15 owns the tools re-pin event and the tap-table re-derive. HEAD r16 is applied (snapshot s81_head_r16_s0,
  rt 745c8f11e429) and the wave runs hd_lep0N on r16. Whichever of tr2s or the r16 row signs off first counts; cancel the
  other only after that. This lane and FABLE-FIX-HEAD-SERDES-R2 own the HEAD types.
- tr2s at CTS: FF hold gate PASS -225.84 on 5,948 ends (r14 -388.93 on 25,803). TT after placement-RC repair -454.73 /
  tns -140,389 (r14 -171.65 / -1,364). Stock GPL area +21.13%. Next read: post-GRT TT. If it is still < -300, cancel the
  exact unit with `ot-run --cancel oth-ubuntu-1990134-1795230761` and record the evidence (owner rule).
- FABLE-VISUAL-0030 (sec. 4, hd_lep0N): 420k cells and 49 m cores in a 330 um band, RUDY over 100 %, 6,410 station flops
  in slits under 20 um, 9,376 hops over 300 um. Adopted for the next private iteration (plan delta not written yet):
  m cores in two rows with 40 um streets (use the ~100 um N-S street), stations in the N-S street, band split (422k > 400k).

## UPDATE 11-21 01:5x PST: tr2s cancelled, split iteration
- tr2s CANCELLED on COORD's order (ot-run --cancel oth-ubuntu-1990134-1795230761, exit 143). Recorded result: with the
  56 taps priced, FF hold before repair was -225.84 ps on 5,948 ends, and 1 end (-98.42) after 6,290 hold cells.
  The build failed on setup: TT -454.73 / tns -140,389 with 526,717 instances. Area grew +21.13% with the early
  global-place exit off. The 2 remaining dpkit-hd_lep0N containers on epyc10 belong to wave jobs, not this lane.
- Split scoping, r16 plan 1a7d319a9ba6 (snapshot s81_head_r16_s0):
  - Outline 1892.16 x 1408.32. Pair cores sit at x 69.12-846.72 and x 967.68-1745.28, y 17.28-509.76 and y 846.72-1339.2.
    The band is y 510-847 and the N-S street is x 847-968.
  - The type has one content, u_core (ot_s81hd_lep0N_noidx_core). Inside it are one engine ot_s81hd_lep_idx_nr
    (4 lanes, the 40 tx/rx SRAMs), u_land (5 SRAMs), rst_fan and pipes.
  - type_split.py moves whole contents, so the band split needs an RTL half-engine split first.
- Plan:
  (1) RTL on a lane branch: u_core_w (pp1, pp2, lanes 1/2) and u_core_e (pp0, pp3, lanes 0/3). Cut buses for the
      shared credit/token/collector paths (+cycles); LEC + bench.
  (2) type_split spec with the x cut at 907.2 um.
  (3) The m cores in two rows with 40 um streets, and stations in the N-S street.
  (4) Carry the tr2s tap pricing (L/plan/new56_rows.json; re-derive on the split pieces).
  (5) Gen with HEAD settings only: no OT_GPL_SPARSE_OVERFLOW / GPL -overflow, i.e. main tools or explicit env 0.
  (6) Private bind + LATCHECK, then the kit.

## CODEX 2026-11-21 03:0x PST

- R16 private ten-TX-bank shelf keeps all 251 frozen clock taps, four signed pair shapes and die-facing pins. The older 45-bank proposal collided with the frozen clk_t28 halo and was retired. The ten-bank model reviewed under `results/geom_review/codex-head-prects-1121.md` moves 37 local anchors by at most 21.6 µm. Reset remap keeps 7 edges, 5 exports at identical coordinates and at most 357.87 µm per resulting stage against bound 405. First raw wrapper lacked the proper START driver and was regenerated with a remapped per-type plan.
- GEN and preflight now PASS on private plan 42fd64227556, exact emitted source bundle 34 files. E10 work `/srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r2/shelf1121/reset_remapped_v2`, job `oth-ubuntu-1386343-1795258318`, hub `~/head-plan-r16/lep_shelf_remapped_gen_v2.otrun.log`. Place-only diagnostic before a built-image review. Gather true setup paths and congestion to decide if the larger LEP split is still required. Existing wave runs untouched.
