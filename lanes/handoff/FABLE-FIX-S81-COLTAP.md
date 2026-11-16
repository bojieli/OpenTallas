# FABLE-FIX-S81-COLTAP handoff (owner of S81 col timing closure, 216 types; started 11-16 06:5x PST)

Existing lane S81-COL-O (Opus) keeps its builds and runs the pilots. Read also: lanes/FABLE-PD-S81-F2s.md, FABLE-FIX-S81-COL-SPECS.md, handoff/S81-COL-O.md.

## Root causes (MEASURED on r2 = col_h9_r2__t1__clce45cab5__pv7a260fc0, epyc10 fable-fix-s81-col/f2s2 and s81-col-clk-impl/proof 4_1_cts.log, an/cts_f2s2_wpp)
1. Upper taps 415..542: early core taps of a 450-override type are priced insertion - 450 (r104), and S81-TAPROWS re-declared the element halves 532.99 / 553.18 -> 465.39. Early 15.39 leaves no run from port clk_c<k> to the pin: pin -13, view latency 533 / 553 -> effective 520 / 542. F2r tree (early 215.39, 130-142 ps padded): 460 / 468.
2. Sequencers s11 / s14 sit 150 ps early (effective 299): the ETAP pass hung them on a core-tap port (clk_c8 / clk_c12), after which tap_balance skips them (`string match clk_c*`), so the 3/4 first estimate is never topped up.
3. go_tag / ef (the -185 / -160 residue) is a floorplan fault, not only the IFN half cycle. Only u_w drives ef (sh_free, bank_free); go_tag goes to both halves. In the left tiles (s10, s12) u_w is the FAR half: s -> u_w pin 405 um, loop sum go_tag + ef = -345 (CTS, unrepaired). In the right tiles (s11, s14) u_w is 53 um from s: go_tag far half +173, ef +96 with s 137 early (= +36 / +233 at the nominal s clock). hw and he have the same outline and pins on S / N faces only, so the two origins can be swapped.
4. Reset copies u_d7_6_Y -> _r<k>: -100 (CTS), 780-816 um one-cycle hop. Spec 1 (two-level copy tree), no owner.

## Decisions (final col form)
- Windows: per_port 40 grid / 10 core taps, r2 measured table (already in B6gF2s2 a623deec2d38). The 3 clock rows (etap, src tree, ROM lead 255) are in F2s2.
- clock.core_tap_lead_ps 200 on all 216 col (new key): early = insertion - 450 + 200 = 215.39 / 184.57 / 53.17 TT, FF 158.76 = the F2r numbers. Not "price against die 250" globally: leaf / serdes / bk_sel 450 types keep r104.
- tap_balance: ETAP-hung pins on a core port are topped up.
- Tile rule (col_tile_rows.py): where u_w is > 20 um farther from u_s<k> than u_e, swap the two origins; the two core tap rows keep xy and swap the core name (die clock ports do not move). Then move u_s<k> next to the u_w pin where the site is free. 372 swaps, 282 s moves; r1 / r2 / h10_r2 (132 types) end at near 50-53 / far 318-321 um = the measured right tile.
- Sequencer lead 100 (core_pin_lead_ps cfg7_seq clk[0]) on those 132 types: expected CTS-unrepaired go_tag >= +136, ef >= +133, ROM q -> s about +36.
- r0 families + h10_r1 (84 types): swap only (ROMs block the s move), near 111-243 / far 318-387, no s lead. Estimate thin (go_tag far about +40, ef about +23..+63): second pilot decides (s lead sign, or IFN = 0 halves Spec 3).

## Artifacts
- Branch claude/fable-fix-s81-coltap-1116 @f2091534ae0 (2 commits: 458be3eb2e4 core_tap_lead_ps, f2091534ae0 tap_balance top-up). GATE main=1c567bf29d4 pass=109/109 (intel2 ~/fable-fix-s81-coltap/gate_f209153.log). Lane clone epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/repo.
- epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/: col_tile_rows.py (PLAN OUT [--apply PLAN_OUT]), rows_F2s3.json (216 types: moves, tap_swaps, clock keys, tile distances), F2s3_preview.json (F2s2 + rows, validates with 0 errors), ovl/tools/die_plan (v2 tree die_plan + both commits, private copy for a pilot gen before the tree is rebuilt).
- Commit trailer: the two pushed commits carry Claude Fable 5.2; COORD 07:2x ruled the Opus 5.5 trailer is the session rule, so every later commit uses it (pushed commits are not rewritten: no force-push).

## Open / next
1. MERGE-QUEUE lands f2091534ae0; the S81 build tree must carry it before any col release (v2 eb1e73448bd0 does not).
2. DIE-S81-92: F2s3 = F2s2 + rows_F2s3.json (compose check of the s sites, bind, LATCHECK, G0). Col release on F2s2 = pilots only.
3. S81-COL-O: evidence pilot r2 at CTS now (ovl tools + rows; if kit_topology says BIND_STALE swap the macro origins in the kit), read OT_TAP_CORE (all within 20, s at 350) and an/cts_sta.sh (go_tag, ef, reset copies). Then countable pilots on the F2s3 bind: r2, one r1, one h10_r2, one h9_r0_p2, h10_r0_p1, to sign-off on hosts other than epyc10; export signed records to AGIdock /archive/opentallas-signed-1114 + rtx-pro.
4. Reset copies Spec 1: needs an implementer lane (asked COORD).
5. Read FF hold at pilot sign-off (CTS pre-repair 1,515 endpoints, -55.6 with measured windows).
6. If r0 pilots miss: IFN = 0 halves (Spec 3) is the fallback form (+416 on the input face), needs hw / he core rebuilds.

## 07:3x 11-16: r300
- COORD approved the branch as r300 (merge priority). HOLDGEN moves the 216 col keys to event_adopt:B6gF2s3 with my pilots as proof_items. FABLE-DIE-S81 owns the reset copies.
- Pilot items sent to HOLDGEN. Wave 1: col_h9_r2__t1__clce45cab5__pv7a260fc0, col_h9_r1__t1__cl49d7a23e__pv047ea3b3, col_h10_r2__t1__cl1f5d6c2a__pv0c1de895. Wave 2: col_h9_r0_p2__t1__cl0045af7b__pv622a6f97, col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97.
- I own col through the pilots and the F2s3 adopt to sign-off. Next read: S81-COL-O evidence pilot (r2 CTS), then the F2s3 bind result from DIE-S81-92, then wave 1 sign-off; post RESULT ... PASS per wave for HOLDGEN.

## 07:4x 11-16: early wave release (COORD)
- A wave is released when its pilots show post-CTS TT setup >= -42 on the reloaded 4_cts DB and GRT overflow 0, not at sign-off. Post exactly: `RESULT [FABLE-FIX-S81-COLTAP -> COORD] col-wave1 PASS: <numbers>` (and col-wave2). HOLDGEN keys on result:FABLE-FIX-S81-COLTAP:col-wave1 / col-wave2 (+ event_adopt:B6gF2s3 + lint_clean:s81).
- Still follow every pilot to sign-off; a later-stage failure is posted and COORD re-holds.
- Reset copies alone below -42 after CTS = not a PASS; post the numbers, COORD decides.

## 07:5x 11-16: reset copies (COORD ruling)
- Rule kept: no col-wave PASS while reset copies u_d*_Y -> _r<k> miss -42 after CTS.
- FABLE-DIE-S81 lands reset-copy rows in F2s3 itself (asked 07:5x, numbers + Spec 1 form posted). DIE-S81-92 composes F2s3 once with both row sets. Copy sites must be taken from F2s3_preview.json (my rows move u_s<k> and the halves).
- Each pilot read carries three class lines: go_tag, ef, reset copies.

## 07:5x 11-16: FABLE-CLOSURE-0943 lever B answered
- Swap premise checked on all 12 family geometries (RTL connectivity in col_h9.sv / col_h10.sv + split wrapper; plan JSON distances for every tile). In all 372 swapped tiles u_w was the far half. Rows unchanged after an MX pin-face correction (rows_F2s3.json cc5bd847f1ec, F2s3_preview.json 4b440870a288).
- Timing is measured on r2 only; r1 / h10_r2 share its tile shapes, the 84 r0 / h10_r1 types have no measured tile.
- F2s3: compose + bind now, adopt only after the r2 CTS read on the rows.
- RTL alternative if a swap is ever refused: u_e's sh_free / bank_free are equal to u_w's by construction (split wrapper comment), so ef could be taken from the near half by a wrapper parameter (needs bench + LEC).

## IFN0 brief (lane S81-IFN0-HALVES, asked from COORD 07:5x)
- Goal: signed IFN = 0 views of ot_v41_rom_elem_q_qxpq_w10_gb_hw and _he for the 84 r0 / h10_r1 col types (all 216 can take them later).
- Start: branch claude/s81-gotag-setup-1115 @39e537ae34; kits epyc10 /srv/opentallas-scratch2/claude/s81-gotag-setup-1115/core/hwC, heC (stopped in 5_1_grt, OT_HOLD_STRUCTURAL FF -152.00 / 2,705 and -164.56 / 2,846 endpoints; TT +0.8 / -4.7). Input contract in_min -81.26, in_max 617.61 (go_tag in_max +50).
- Do: copy the kits to a host other than epyc10 (never patch a running kit). (a) input-face flops (first rising-edge flop behind each data input) on a shallow clock branch, insertion 300-370 ps TT (he; hw stays 330-390): pin-register hooks (pin_reg_split.tcl / ot_pin_regs.tcl / pinreg_pad.tcl) or a re-hang of those CK pins on the level-2 clock net before CTS. (b) OT_HOLD_STOP_PS=-1000000, endpoint limit off. (b) alone is not the form (190 ps x 2,800 inputs).
- Accept per half: DRC 0, TT setup >= -42, FF non-port hold >= 0, lib has setup_rising / hold_rising on every data input, tb_qxpq_go_boundary IFN 0 + mutant PASS, LEC. Then rows to DIE-S81-92, post to FABLE-FIX-S81-COLTAP.
- Detail: lanes/FABLE-FIX-S81-COL-SPECS.md Spec 3.

## 08:4x 11-16: after the limit
- S81-COL-O has not posted since 05:40 and ran no pilot: I run the pilots myself until it reports.
- f2091534ae0 is on main (41bb1dcfd10). S81 v3 tree build by TOOLS-CONVERGE (started 07:37) carries it.
- F2s3 plan epyc10 s81-b3-clk/ev/B6gF2s3.json 012db35daaea = F2s2 + my rows (216/216 applied, checked) + FABLE-DIE-S81 reset rows (copy_depth 3 on 216). Rebind started 16:41Z, log s81-b3-clk/log/B6gF2s3.log.
- r2 EVIDENCE pilot RUNNING: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/ev1 (script ev_go.sh; plan F2s3_preview.json = F2s2 + my rows only, bind out F2s2, tools srcx = F2s2 src + both commits). Client log intel2 ~/fable-fix-s81-coltap/ev1_client.log (ot-run from intel2; fleet hosts cannot resolve each other). Read: 4_1_cts.log OT_TAP_CORE lines, then the CTS STA (epyc10 fable-fix-s81-col/an/cts_sta.sh, copy to epyc7).
- Next after the read: post it; on the F2s3 bind PASS generate the 5 countable pilots (ev_go.sh with B=run/b/B6gF2s3, PLAN=ev/B6gF2s3.json, v3 tree, no srcx) to route.

## 08:5x 11-16
- Evidence from the F2s2 bind is not possible: KIT_TOPOLOGY_BIND_STALE on any type change (ev1, ev2 on epyc7 are dead dirs, deletable). r2 comes from the real F2s3 bind: when epyc10 s81-b3-clk/log/B6gF2s3.log shows BIND_RC=0, replicate run/b/B6gF2s3/{out,src,asbuilt_run.json,sidecar_new.json} + ev/B6gF2s3.json to a non-epyc10 host (DIE-S81-92 replicates to epyc7/8/9) and run ev_go.sh with B=.../run/b/B6gF2s3, PLAN=ev/B6gF2s3.json, SRC=$B/src (check tap_balance.tcl has the tb_hung top-up line; else use srcx-style overlay).
- FABLE-PD-S81-F2s3 ADOPT-OK notes answered: 0.576 um tap offset is pre-existing (hw +0.108 / he +0.684 in F2s2), no row fix. Per pilot report: s arrival (lead 100 unmeasured), reset-copy hop um + slack, OT_CLOCK_TAPS lines.
- S81-IFN0-HALVES live (epyc7 s81-ifn0-halves/hw0, he0).

## 09:0x 11-16: COORD ruling on adoption
- F2s3 is adopted as soon as DIE-S81-92's gates pass; it does NOT wait for my r2 read (my 07:5x / 08:5x "adopt after the read" asks are withdrawn). Col stays held by result:FABLE-FIX-S81-COLTAP:col-wave1 / col-wave2, so nothing col launches before my PASS.
- A bad read is posted and fixed by the next delta, not by blocking the adopt.

## 09:2x 11-16: r310
- PASS test now: TT setup >= -42 on the GRT-stage read (reloaded 5_1_grt DB, die RC 1.00) + GRT overflow 0, every pilot of the wave, incl reset copies; or post-CTS >= +45 while GRT is not read. Post-CTS placement RC under-reads by 51-86 ps.
- r0 / h10_r1 (84): MAIN = IFN = 0 halves (lane S81-IFN0-HALVES, epyc7 s81-ifn0-halves/hw0, he0), fallback swap-only. Wave 2 pilots run on F2s3 (fallback read) and again on the IFN = 0 delta. I write that delta's rows (views, core tap insertion from the new core latency, .IFN(0)) when the lane posts signed halves.
- Reset chain hops > 405 um on a pilot -> hop table to FABLE-DIE-S81, site rows in the same next delta.
- F2s3 bind restarted 17:1x UTC by DIE-S81-92 (bk_sel overlay ovl_F2s3, 26 files; plan 012db35daaea). Pilot gen needs out + src + ovl; ask DIE-S81-92 for the replica paths if not posted.

## 13:3x 11-16: after the second limit
- F2s3 012db35daaea: BIND_RC 0, LATCHECK 873/873, lint 395/395, hard_core_param 0, ADOPTED (r331). Col keys stay held on col-wave1 / col-wave2.
- While I was limited Codex (covering DIE-S81-92 and this lane) started a GEN-ONLY job for the five pilots on epyc10: /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s3/gen/<type> (script gen_five_prepared_f2s3_codex.sh, client log intel2 ~/fable-fix-s81-coltap/gen_five_prepared_f2s3_codex.log, tools tools-converge/s81/gen_e37_D2_exec, src kw45/src_s81_pin_3c913dbdfb23_f2s3_mainref_pg_d2). 4 kits done at 21:19Z, r2 last. No route was started by it.
- Kit check (col_h9_r1 pilot): core_taps early 215.39 / 184.57 / 53.17, sequencers 371.22 (lead 100), window 40, ETAP + SRC tree, tap_balance top-up line present, OT_TT_SETUP_REPAIR both.
- NEXT (mine): when gen ends, rsync countable_F2s3/gen to the SAME path on epyc7 and epyc8 (epyc10 can ssh them), then from intel2 per kit: ot-run --mem 64 --threads 16 --hosts epyc7,epyc8 --dir <gen> -- bash <gen>/run_kit.sh <gen>/<type> route 64 16. Reads per r310: 4_1_cts.log OT_TAP_CORE, then STA on the reloaded 5_1_grt DB (die RC 1.00) + GRT overflow; post col-wave1 / col-wave2 RESULT; follow to sign-off; export signed records to AGIdock /archive/opentallas-signed-1114 + rtx-pro.
- S81-IFN0-HALVES: hw1p / he1p clean GRT, TT +2.9 / +0.3 on the GRT DB, FF hold -25 / -13 pre-DRT, face CK 394-398 TT; both in route on epyc7.

## 13:4x 11-16: FIVE PILOTS RUNNING to route (launched 13:4x PST by me)
- Kits: /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s3/gen/<type> on epyc7 and epyc8 (rsync of the epyc10 gen; run_kit.sh in the same dir). F2s3 bind, D2 tree.
- epyc7: col_h9_r2__t1__clce45cab5__pv7a260fc0, col_h10_r2__t1__cl1f5d6c2a__pv0c1de895, col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97. epyc8: col_h9_r1__t1__cl49d7a23e__pv047ea3b3, col_h9_r0_p2__t1__cl0045af7b__pv622a6f97. ot-run 64 GB / 16 thr, goal route.
- Client logs intel2 ~/fable-fix-s81-coltap/pilot_col_*.log; kit logs <kit>/run/logs/asap7/*/base/.
- r2 kit check: u_e10.u_w placed at 285.228 (swapped), clk_c6 -> e10_u_e, clk_c7 -> e10_u_w, early 215.39, s10..s14 371.22.
- Reads to do: (1) 4_1_cts.log OT_TAP_CORE / OT_TAP_BALANCE done; (2) STA on reloaded 5_1_grt.odb, die RC 1.00 (adapt epyc10 fable-fix-s81-col/an/cts_sta.sh: FX_ODB=5_1_grt.odb, estimate_parasitics -global_routing), classes go_tag / ef / ROM q->s / reset chain hops (um); (3) GRT overflow; then RESULT col-wave1 / col-wave2 per r310; (4) sign-off + export.

## 14:0x 11-16: ROW BUG found on the pilots (mine)
- F2s3 swapped pairs overlap 1.116 um (pitch 267.84, half 268.38, kit offsets hw +0.108 / he +0.684). MPL-0041 at 2_2_floorplan_macro on every swapped col type. My earlier "0.576 um is harmless" answer was wrong (checked pins, not outlines).
- Fix rows: epyc10 fable-fix-s81-coltap/rows_F2s4_colfix.json 1f35a4225f75 (copies on epyc7/8): 366 pairs one half +-4.32 um, 6 pairs (col_h10_r0_p4) unswapped. Asked DIE-S81-92 to fold into the next col event + rebind; col holds must be re-keyed to it.
- Evidence reruns: kit_colfix.py ROWS KIT patches macro_place.tcl of a STOPPED kit (backup macro_place.tcl.f2s3). r2 + col_h10_r2 relaunched on epyc7 (logs pilot_col_h9_r2_.log, pilot_col_h10_r2_.log; first tries *.try1.log). TODO: when col_h9_r1 / col_h9_r0_p2 (epyc8) and col_h10_r0_p1 (epyc7) stop with MPL-0041: patch + relaunch the same way.
- These runs are evidence only. PASS needs kits generated on the corrected bind (regenerate the five then).

## 14:2x 11-16
- All five evidence pilots relaunched with the corrected halves (kit_colfix.py); r2 + col_h10_r2 in 4_1_cts (epyc7), col_h10_r0_p1 (epyc7), col_h9_r1 + col_h9_r0_p2 (epyc8) behind.
- DIE-S81-92 folded rows_F2s4_colfix into B6gF2s4 (sha256 28a6fe4fec53254f, epyc10 s81-b3-clk/ev/B6gF2s4.json); bind queued; col holds key on event_adopt:B6gF2s4.
- Checked B6gF2s4: 954 plan-outline overlaps all clear at kit offsets (498 hw|he gap 0.036; 456 col3_c|bf16_half MY gap 0.000). Kit offsets: hw +0.108, he +0.684, bf16_half MY +0.996, everything else +0.108 (cfg7_seq MY -0.108).
- NEXT: CTS read r2 / h10_r2; GRT-stage STA; when the F2s4 bind passes regenerate the five kits on it (countable) on the D2-successor tree and rerun; PASS only from those.

## 14:4x 11-16: r2 CTS read (evidence kit)
- tap means 367..468 (was 415..542), 5/79 core pins outside 20. Halves 460 / 468 (was 520 / 542). s10 / s12 452, s11 / s14 421 / 422 (-29), s13 445. ROMs c12_6 +25, c13_2 +32, c13_6 +43. Low taps clk_t10 365, clk_t23 381; clk_t13 max 513.
- TODO on r2: re-measure per-port windows on this 4_cts DB (tap_window_measure.py --log 4_1_cts.log); GRT-stage STA when 5_1_grt.odb exists.

## 15:0x 11-16: r2 CTS TIMING read (evidence kit, lead 100)
- an/stage_sta.sh KIT OUT cts|grt (epyc7 fable-fix-s81-coltap/an; cls2.py classifies setup_paths.tsv). r2_cts: 161 endpoints, 40 below -42, WNS -180.8.
- go_tag +109..+137, ef +118..+151 (were -186 / -160): tile fix MEASURED.
- ROM rd_out -> s q: -57.0, 14 below -42: sequencer lead 100 is too much (my estimate was wrong). Triangle q / go_tag / ef has about +50 total. Variant var_b (epyc7 fable-fix-s81-coltap/var_b/<r2>, s 311.22 = lead 40, ROM lead 285) running to CTS, client log intel2 pilot_r2_varb.log; then stage_sta.sh on it -> choose leads -> row change (core_pin_lead_ps only) to DIE-S81-92.
- Reset chains (copy_depth 3): hop 1 common flop (989,167) -> _s0 836..1,174 um, -181, 26 below -42. Posted hop table + site ask to FABLE-DIE-S81.
- TODO: FF hold read (an/ffh.sh needs core_taps_ff.sdc of the kit), col_h10_r2 breakdown, GRT reads.

## 15:4x 11-16: COORD four points
- (1) reset chains: no plan row exists (no site key; reset_replicate copy_depth assumes GPL spreads the chain, measured false). Fix = flow hook reset_chain_spread.tcl (PRE_RESIZE, env OT_RESET_CHAIN_SPREAD=1; file on epyc7/8 fable-fix-s81-coltap/ and localhost scratchpad ct/). Proof kit var_c (r2 copy up to 3_3 + hook appended to gp_noconverge_gate.tcl + lead 40 / ROM 285). TODO: when proven, put the tcl into tools/die_plan (gen_phys: emit + source it from the PRE_RESIZE hook when the type has reset_replicate copy_depth > 1 or env), test, branch claude/fable-fix-s81-coltap-1116b (trailer Opus 5.5), gate, READY; then item_env row for 216 col.
- (2) IFN = 0 halves = col form for ALL 216 (COORD). Halves not signed (he FF -24.18 removal class, ECO failed; hw FF -68.88). Worker agent started on S81-IFN0-HALVES (reports to me). Then rows for F2s4b: views, .IFN(0), core tap insertion, sequencer lead 0 (drop the cfg7_seq entry of core_pin_lead_ps).
- (3) var_b (lead 40 / ROM 285) CTS done; timing read to rerun on epyc8. (4) FF hold read: an/stage_ffh.sh KIT OUT cts|grt + clsh.py.
- epyc7 thread cap full (184/96): run reads / variants on epyc8 (var_b, var_c, an copied there).

## 16:0x 11-16: variant reads
- var_b (lead 40, ROM 285) CTS: go_tag +64..70, ef +184..194, q +9, a -42 (s14). Rule: a + q per sequencer is independent of both leads (s14 +44, s12 +64). Fallback = sequencer lead 40, ROM lead 255. Main (IFN0): sequencer lead 0, ROM lead about 200 (inference).
- FF hold at CTS pre-repair: 654 non-port endpoints, -175 (300 are reset removal). hold script prints slack x 1e12 (divide). Read again on the GRT DB.
- var_c (reset spread + lead 40 / ROM 285) relaunched on epyc8 after a RESYNTH-GUARD stop (config.mk mtime; touch -r oldest 1_*.v). Client log intel2 pilot_r2_varc.log. Look for OT_RESET_CHAIN lines in 3_4_place_resized.log, then an/stage_sta.sh ... r2c_cts cts.
