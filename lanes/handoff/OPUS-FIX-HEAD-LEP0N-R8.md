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
