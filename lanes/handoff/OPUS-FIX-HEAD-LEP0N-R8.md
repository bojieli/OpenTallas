# OPUS-FIX-HEAD-LEP0N-R8 (Opus, from 11-21 23:1x PST): HEAD event r17b + hd_lep0N split to sign-off (successor of FABLE-FIX-HEAD-LEP0N-R7)

Predecessor handoffs: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R7.md (split facts, rename map), -R6/-R5/-R4.
Hub dir intel2 ~/opus-fix-head-lep0n-r8/. Lane dir M=/srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r8 (intel2: tmp/, plan/, ev/, planroot_e1b;
epyc10: tmp/). R7 lane dir L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r7 still used (L/src tools tree, L/tmp/recompose_merge.py, L/hc_proof).

## DONE
- HEAD event head_rp21z20NF15f_r17b APPLIED 23:3x (src s81_head_r17b_s0, manifest 67d8b0903f20; e1b START plan 18f3c0c7c0c1 /
  sidecar facc71b93198; in-tree receipt; tools 30b1f11ad5f7). Publish gate PASS c293e888858; marker receipt
  lanes/handoff/s81_head_atomic_apply_1795332633870162806.json (optimistic, holds preserved, review not required).
- ACK FAIL-CLASS 8070467972 posted (hd_host_e DRT-0255; r17b contained tree). Watch the wave hd_host_e relaunch and post RESULT.
- E piece GPL death root cause: yosys kept g_rxm.g_o[*].g_on.g_registered_select.g_bit[k].dm name for merged mrd[k] flops;
  fix tmp/mrdfix.py widens the 4 mrd stage groups. LANDING-BAND-CORE (COORD 23:4x): tmp/bandfix.py slides overlapping stage bands
  (10 on E, 6 on W, max 100 um); landing_band_core --base r16 PASS on both pieces. Both fixes in private tree F (epyc10
  L/trees/s81_head_r7split; plan sha ce3fb5e7ef4d; wave_prepare sha updated; backups in epyc10 M/tmp).
- Cancelled bad-plan kits: oth-ubuntu-371717-1795332613 (E place), oth-ubuntu-231439-1795332206 (W GRT; W CTS setup -875 = landing
  fault/status path coll_i0 -> coll_o2 1.2 mm, no status relays, plus coll_i2 ring -234 in a 13 x 531 um sliver band).
- Split rebased on e1b: tmp/rebase.sh e1 -> M/ev/e1: split + recompose + gen rtl + bind/cohort/LATCHECK 334/334 PASS; G0 14 errors
  (6 faces face_budget_g2, 7 START uses rst_start_raw_0..6, 1 band_capacity reader-start:lepk_i0).

## IN FLIGHT
- Private kits on F (fixed plan, v2-based g9 bind): E spec ~/coord/autopilot/private_specs/OPUS-FIX-HEAD-LEP0N-R8/s81_head_hd_lep0N_1121234406
  (run-item pid 3993424, log ~/opus-fix-head-lep0n-r8/runitem_e7.log); W .../s81_head_hd_lep0N_w_1121234411 (pid 3993434, runitem_w7.log).
- Cut-form LEC (R7 units, epyc10): oth-ubuntu-1452654-1795321534 (CUT_EQUIV_PASS), oth-ubuntu-1610100-1795322008 (CUT_RST_EQUIV_PASS).
- tmp/post2.sh e1 e2 (ot-run pid 4109031 on intel2, log ~/opus-fix-head-lep0n-r8/post2_e2.otrun.log): bandfix + START exports per piece
  (tmp/start_split.py: rows 3, 6 -> lep0N_w, others -> lep0N shifted -820.8; head_reset_exports.py fix picks nearest raw relay) +
  head_sideband_street_rows (status/reader/writer START rows, fixes the W status path) + bind/LATCHECK/G0.

## UPDATE 11-22 18:2x SEALED MERGED TREE + hd_ctl
- HEAD-CTL-R1 hd_ctl wrcap rows (65 tap_offset + 65 tap_window) are already in ev/k1, identical, so no compose was needed.
- Tree epyc9 M/trees/r18jk_merged = ot-tree-fork of Fable s81_head_r18j_pairs + k1 prep files (plan 5e1f38e1530b).
- Kit r8-ctl1 (hd_ctl, seal, goal route, epyc9): unit r8-ctl1-1795371195, spec s81_head_hd_ctl_1122101315, launcher M/tmp/launch_jk.sh (ITEMS=type:tag:host).

## UPDATE 11-22 10:xx MERGED PLAN OF RECORD (COORD)
- Merged = FABLE r18k (trees/s81_head_r18j_pairs, 762441fd7f14) + R8 hd_host_n pg_pin_rule: sha256 5e1f38e1530b8d0d.
  Prep epyc9 M/ev/k1/prep (tmp/post9.sh; tools/RTL root = Fable tree read-only). Gates PASS (bind, cohort 27/27, LATCHECK 334/334,
  receipt, band core); G0 = 6 face_budget_g2 only. Posted.
- W-band rows (r18i) NOT merged (conflict with ring-FF coll_i1/i2); r8-w13 continues as a parallel form.
- E = Fable e1 (r18j_pairs); no R8 E. Live R8 kits: hn3 (r18j, goal route), hn2 (to end), w13 (r18i, goal route).

## UPDATE 11-22 08:3x hd_host_n r18j (COORD accepted)
- hn1 (r18e) routed NOT SIGNED: DRC 3 Rect Only M7 rst_start_raw_0 (510.2,339.2) only; TT +80.3, FF core hold PASS.
- r18j = r18i + partition_types.hd_host_n.pg_pin_rule=true (tmp/fix18j.py, post8 -> ev/j1). Class sweep tmp/pgscan.py on r18i:
  17 soft rule-off types, only hd_host_n fails (pgscan_r18i.json). Posted to FIX-SYNC-KV-HEAD (15bf1284) for KV.
- Next: mk_r18j (mk_r18i with ev/i3->ev/j1, r18i->r18j, report r18j; base r18e) -> sealed hd_host_n kit goal route.
- hn2: let it finish; if it ends with only the same Rect Only DRC, stop spending on it (r18j kit replaces it). Do not cancel early.
- W-band r8-w13 on r18i (unit r8-w13-1795362308, spec s81_head_hd_lep0N_w_1122074508, goal route) running.

## UPDATE 11-22 07:4x
- E r8-e11 FAILED post-place stop -441 (reset tap u_rrl_380 -> u_rg0.u_pair rst_n at pair centre; rgate QN INV on far macro edge).
  COORD ruled option (b): pair rst_n -> S face (core_pins lep_pair_pins_777r, HEAD-96 rp18) + pair view re-sign, owned by FABLE-FIX-HEAD-LEP0N.
  When Fable posts the re-signed pair view: fold it (LEF/libs + pins_file 777r for u_rg0/u_rg3 E and u_rg1/u_rg2 W) into my next tree and launch E (goal route).
- main 8362730c per-type reset.relay_driver_types (opt-in, harmless) stays; NOT usable on HEAD (clock_landings rrelay-only regex,
  install_bound_native_reset refuses drivers). Fork trees/r18e_fix carries it in tools (inert without the row).
- W-band r8-w12 FAILED OT_CLAND fit (r18g coll_i2 band covered stage txread_l2b0). r18i: tmp/fix18i.py (coll_i2 [17.28,545.4,66.96,673.92],
  coll_i1 bottom 676.08, overlap check incl. stage groups + reserved sites, collector_local_sources band rect_um sync). post7c -> ev/i3.
  Next: mk_r18i (from mk_r18g with g1->i3, r18g->r18i, report r18i) then launch W goal route (tmp/launch_r18g.sh with N=r18i).

## UPDATE 11-22 06:0x
- E r8-e11 place PASS (KW_PLACE_RC 0); post-place wns -556 (pre-CTS): u_rrl_380 -> u_rg0.u_pair rst_n driven by an INVx1 over a long
  wire (slew 1242 ps; repair_design should buffer it), coll_i3 wreg fs_q -> u_wen -38, lepk wen -163, u_bout_o_h2r1_p -> port -218,
  arst_n -> u_rst_in -91. Judge at the CTS post-hook report (cancel rule: < -300 after CTS/GRT repair).
- R7 cut-form LEC (e10 form) FAILED 03:47 (3348/3380 unproven); superseded form, posted 524d1a62, not rerun.

## UPDATE 11-22 05:4x W-band r18g (COORD 05:2x/05:4x)
- Split: R8 = E (r8-e11, r18f) + W-band; Fable = W-ringFF (fable-lep0n-w4). Parallel forms, first W to sign counts.
- Tree s81_head_r18g_split_s0 (3bde930bae13, epyc9; plan c6eab9a2e92b; tmp/fix18g.py + post6.sh + mk_r18g.sh; ev/g1):
  W coll_i2 band [17.28,511.92,66.96,656.64] 7190 um2, coll_i1 bottom 658.8 (7446 um2), area_reserve = measured 4382.5.
  AREA CHECK in fix18g.py: band area >= measured reserve / 0.7 for every moved band (unmeasured bands: report only, x1.66 model).
  Gates: plan_gate_pre 0, bind/cohort PASS, LATCHECK 334/334, band core PASS, G0 = 6 face_budget_g2. Receipt ev/g1/receipt.
- LIVE W kit r8-w12 goal ROUTE: unit r8-w12-1795355071, spec s81_head_hd_lep0N_w_1122054431, runitem_w12.log (launcher tmp/launch_r18g.sh on intel2 M).
- E r8-e11 passed the OT_CLAND fit check (E bands left alone). r8-e11 is goal AUTO: if it stops at geom, relaunch with route.
  hn2 is goal finish: if it dies on stage resume, relaunch with route (COORD: finish dies on resume).

## UPDATE 11-22 05:1x
- r8-w11 FAILED place (OT_CLAND coll_i2 band too small: 4382.5 um2 needed vs 2908.5 upper bound in fix18f band [17.28,552.96,64.8,609.12]).
  Not relaunched: Fable fable-lep0n-w4 (its own r18f fork, W ring-FF form) is past place and in CTS = the single W candidate (posted 85c383af).
  If w4 fails: build r18g with the W coll_i2 band >= 47.5 x 100 um (e.g. y 552.96..655), via fix18f.py NEW_I2 + mk_r18f pattern.
- E r8-e11 in place (kwp-d3f1caeda1b3c789505b, place.live.log under private_specs/.../s81_head_hd_lep0N_1122043555).

## UPDATE 11-22 04:5x COORD rulings
- SPLIT posted (hub 23199c88a5d3): R8 owns E r8-e11 + W r8-w11 (r18f tree 2fa83144541824aa). FABLE-FIX-HEAD-LEP0N owns the structural
  analysis + every variant, incl. its own W ring-FF kit (fable-lep0n-w1/w4, own r18f fork plan f23abfbd22780d25). First W to sign counts.
  I start no new hd_lep0N variant.
- Native-reset receipt: proof rerun on r18f sources into epyc9 M/receipt_r18f/proof (run_single*.sh with paths rewritten to the r18f
  tree + lane dir), systemd unit r8-nrproof-1795351270. Then head_native_release_receipt.py --proof-dir that dir. >1 h -> publish gate
  without it (COORD ruling 2). Not a sign-off gate.
  DONE 05:2x: receipt epyc9 M/receipt_r18f/out/native_release_receipt.json (stale in-tree mutants regenerated from r18f ot_pdie_serdes:
  proof/leaf_*.sv, old copies *.stale). G0 with --native-reset-receipt that file: 6 errors = face_budget_g2 only (M/receipt_r18f/g0).
  Publish gate for r18f: pass --native-reset-receipt M/receipt_r18f/out/native_release_receipt.json; face_budget_g2 rows after routed E/W.
- hd_host_n hn1/hn2: geom rc 1 (advisory), past chain_probe.

## UPDATE 11-22 04:4x r18f
- r18e dry place (epyc9 M/r18e/*_dry): E post-place wns -800 (cut-face status u_cland_face_fault_i_coll_i0_p -> u_cland_agg_1,
  unrelayed ~1 mm: face child i_coll_i0_p is an intra (same-region) input, sideband stage tool skips it); W wns -496 (coll_i2
  ring lap, max_delay 416.5, band = 12.96 x 531 um sliver at the W face).
- FIX: clock_landings agg status stages may relay a face input (faced_in), main c293b03e90db (test added).
  Plan rows tmp/fix18f.py: W coll_i2 band -> [17.28,552.96,64.8,609.12], its stages re-chained (same counts); E 4 agg stages on
  i_coll_i0_p (hop 319), consumers joined to nearest local reset copy. ev/f1 on epyc9 (fork trees/r18e_fix): gen/bind/cohort/
  LATCHECK 334/334 PASS, band core PASS, G0 = 6 face_budget_g2 (+receipt: in-tree proof dir lacks single_v2_positive.rc).
- Tree s81_head_r18f_split_s0 (2fa83144541824aa, epyc9 only; tmp/mk_r18f.sh; plan_gate_pre PASS 0 findings).
- LIVE signable kits r18f epyc9 (systemd --user on intel2): E unit r8-e11-1795350956 runitem_e11.log spec s81_head_hd_lep0N_1122043555;
  W unit r8-w11-1795350962 runitem_w11.log spec s81_head_hd_lep0N_w_1122043602.
- hd_host_n: r18e kit runitem_hn1.log pid 1708292 (CTS); H-C06 twin (COORD) plan d229d61b9e49 in M/hc06n prep, spec
  s81_head_hd_host_n_1122040143 unit r8-hn2-1795348903 runitem_hn2.log, goal finish. First to sign counts. hd_host_e: no twin (wave kit live).
- W7 cancelled (GRT NDR-dropped congestion, CTS -1465). E7 cancelled earlier. HEAD NO-LAUNCH = DEFER-RESIGN by design (posted).

## UPDATE 11-22 02:3x COORD: adopt Codex r18e
- Codex sealed s81_head_r18e_split_s0 (b4f489665c04) = r18b + full tools at main 6d2e187f0d65 (contains cf418b03ca7 reset_tree
  site-rule cache fix); plan_gate_pre PASS; bind exact r18e/bind_6d2_exact. Tree only on epyc9. Dir epyc9 M/r18e (apply_r18e.sh).
- r18d is SUPERSEDED (my e10/w10 run-items killed + units oth-ubuntu-968063/968394-1795343007 cancelled before place).
- ADOPTED place-only dry kits on epyc9: E r18e/hd_lep0N_dry unit oth-ubuntu-733791-1795342482, W r18e/hd_lep0N_w_dry unit
  oth-ubuntu-723795-1795342459 (run_kit.sh ... place 48 8). Codex also has r18e/hd_host_e_dry. After clean place -> signable
  run-item kits E/W from r18e (launch pattern tmp/launch_r18d.sh with r18e).
- hd_host_n FAIL-CLASS 7dfd9aa20e (stale reset_tree cache, rr_t11 x1434.72 vs rst_rl_11 x303.9): relaunched on r18e private kit
  spec s81_head_hd_host_n_1122022627, runitem_hn1.log pid 1708292 (intel2), host epyc9.
- host_w START sentinels (stage 255/rank 4/phase off): COORD ruling = sign-off proceeds; functional binding -> token lane strap row later.

## UPDATE 11-22 02:2x (after weekly limit resume)
- r18c kits e9/w9 FAILED kit_rtl: missing physical/common_flow/stn_pin_keepout.tcl (R7 F tree also overlaid 6 common_flow files).
- Tree s81_head_r18d_split_s0 (77e2dbd4209b) = r18c + L/src physical/common_flow (tmp/mk_r18d.sh); replicated epyc9+epyc7.
  F vs r17b differ ONLY in tools/, physical/common_flow, 4 rtl, die_plan lane dirs -> r18d carries all of it.
- LIVE kits r18d on epyc9: E runitem_e10.log pid 879385 spec s81_head_hd_lep0N_1122021804; W runitem_w10.log pid 885611 spec
  s81_head_hd_lep0N_w_1122021812 (launcher tmp/launch_r18d.sh).
- E7 cancelled (F tree, CTS post-hook setup -1007). W7 epyc10 unit oth-ubuntu-1721981-1795335594 kept to GRT as face probe only.
- rt current 59d4d33e92c1 >= floor 6d2e187f0d.

## UPDATE 11-22 01:3x
- r18b tree (9a9a2c0193b3) kits e8/w8 FAILED kit_rtl: tree tools (main 385f61b) only know native_stage_groups v1; split plan is v2.
  R7's F tree = r17a + whole tools/ from L/src. Fix: tree s81_head_r18c_split_s0 = r18b + L/src tools overlay (408 files,
  manifest 45c1f2f8e091; tmp/mk_r18c.sh; replicated epyc9+epyc7; epyc10 replicate returns empty status twice, not needed).
- LIVE kits on r18c (epyc9): E runitem_e9.log pid 3382620 spec s81_head_hd_lep0N_1122011820; W runitem_w9.log pid 3387419 spec
  s81_head_hd_lep0N_w_1122011828. Launcher tmp/launch_r18c.sh (private-spec --tree N --plan N/.../prep/source_plan.json).
- Old F-tree kits: E7 (place since 23:50) keep until e9 passes place; W7 CTS post-hook setup -1465 (coll_i0 fault -> up_coll_o1,
  845 ps unrelayed wire; r18 has the status relays) -> kept only to GRT as face probe, then cancel.

## UPDATE 11-22 00:4x
- ev/e5 = e1 + bandfix + START exports per piece (start_split.py + head_reset_exports fix, check bad 0) + sideband rows (W: writer/reader
  start dropped, fstart/origin consumers filtered = relay piece) + uncut band_fill set aside: bind/cohort/LATCHECK 334/334, landing_band PASS,
  G0 only 6 faces (face_budget_g2 missing; schema: a string naming the G2 probe record).
- ev/e6 = e5 + HEAD-CTL-R1 hd_ctl tap_offset/tap_window rows + wave_prepare native_sink_censuses tree-relative (12, were r4_s0 / r13r
  absolute) + hd_lep0N_w eligible: same verdicts. Tree s81_head_r18a_split_s0 (from e5, 022cd626ba26) superseded by
  s81_head_r18b_split_s0 (from e6; tmp/mk_r18b.sh, log ~/opus-fix-head-lep0n-r8/mk_r18b.log).
- NEXT: private kits E + W from r18b (src_manifest tree -> signable; also the G2 face probe), then cancel E7/W7 (F tree, no status rows);
  after a clean GRT add face_budget_g2 to both pieces -> G0 0 -> publish gate r18 -> marker.

## NEXT (older)
1. e2 G0 to 0 errors: faces need face_budget_g2 (G2 probe = routed private kits of the pieces), band_capacity reader-start:lepk_i0 grow.
2. coll_i2 band on W: channel west of pair 2 is 34.56 - 17.28 = 13 um (pairs at x 34.56). Options: band north of pair 2
   [17.28, 512, 66, 630] (pin hop up to ~407 um) or a different pair x. Decide from W kit result.
3. Split HEAD event r18 on r17b: tree = r17b_s0 + overlay (e2 prep files, published piece wrappers, parts RTL + rgnl sources,
   bind results), src_manifest delta-apply, publish gate, marker; that also clears the uncut LANDING-BAND-CORE overlap.
4. Kits from the r18 manifest tree -> sign-off + export.
