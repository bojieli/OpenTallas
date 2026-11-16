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
