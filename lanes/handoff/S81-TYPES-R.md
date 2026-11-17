# S81-TYPES-R handoff (successor of FABLE-FIX-S81-COLTAP, FABLE-FIX-S81-CONG, S81-IFN0-HALVES; started 11-16 17:1x PST)

Owns S81 col (216), strip leaves, IFN0 halves. Three tracks:
- COL (this file): five pilots under epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s4tapfix1 (current819 / D3).
- IFN0: notes in S81-TYPES-R-IFN0.md (fork worker). he_splitclk1 epyc2, CTS done; hw split form to build.
- STRIP (bg_bare, eight-leaf constructor, t34 VQ +43.2, t43): notes in S81-TYPES-R-STRIP.md (fork worker).

## 17:2x COL state
- GEN client intel2 4018771 / E10 unit oth-ubuntu-1482040-1794876086 still running (4 of 5 kit dirs present, r2 last). No physical launch yet.
- Plan per kit: transport off E10 by ot-run --stage, run to cts (place image in run/layout_review/place + OT_TAP_CORE + an/stage_sta.sh cts), LOOK, then route -> sign-off.
- ROM-read class (r2: rd_out -> s q -57 at sequencer lead 100): kit core_latency.txt u_s1x clk[0] 371.22 -> 311.22 (lead 40, ROM 255) on r2 / r1 / h10_r2 pilots; row core_pin_lead_ps cfg7_seq 100 -> 40 goes to S81-DIE-R when measured.
- Reset-chain class: v5 hook (epyc10 + localhost reset_chain_spread_v5_candidate.tcl; epyc9 copy is stale) = source from gp_noconverge_gate.tcl + export OT_RESET_CHAIN_SPREAD = 1 in config.mk. Staged only; needs post-DPL hop + CTS proof on the current r2 kit, then tools/die_plan integration + gate.

## 17:5x COORD lever 2 (FABLE-CLOSURE-STRATEGY) applied
- GEN exit 0, five kits. Patched on epyc10 (backups *.gen0), then rsynced to epyc8 same path: (1) r2 / r1 / h10_r2: u_s* clk[0] 371.22 -> 311.22 (lead 40) in core_latency.txt, core_latency.json, budget.json; (2) all five: reset_chain_spread.tcl (= v5, sha 30bf01cb) sourced at the end of gp_noconverge_gate.tcl + export OT_RESET_CHAIN_SPREAD = 1.
- Launched to CTS on epyc8 (64 GB / 16 thr): intel2 clients 313858 (r2) 313859 (r1) 313860 (h10_r2) 313861 (h9_r0_p2) 313862 (h10_r0_p1); logs intel2 ~/fable-fix-s81-coltap/pilot5_<fam>_cts.log; kits epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-coltap/countable_F2s4tapfix1/gen/<type>.
- NEXT per kit: 3_4_place_resized.log OT_RESET_V5 / OT_RESET_CHAIN lines; run/layout_review/place PNG LOOK; post-DPL reset hop table (0 over 405 um); an/stage_sta.sh KIT OUT cts (epyc8 fable-fix-s81-coltap/an) + cls2.py classes (go_tag, ef, ROM q/a, reset); then relaunch same command with goal route, GRT read (r310: TT >= -42 on reloaded 5_1_grt, overflow 0), sign-off, export.
- gen_phys integration: epyc7 fable-fix-s81-coltap/repo branch claude/s81-types-r-resetspread-1116 @3f38c8287f1 (commit f3a0695f5b + merge of main), gate log intel2 ~/fable-fix-s81-coltap/gate_3f38c82.log. Post READY when GREEN.
- Row posted to S81-DIE-R: core_pin_lead_ps cfg7_seq 100 -> 40 on 132 types.
- Workers: IFN0 (told: balance the 512 IR sinks to the gated cohort in CTS, no hold buffers; no old-form numbers), STRIP.

## 18:1x CTS reads, three in route
- Gate GREEN 61/61, READY posted: claude/s81-types-r-resetspread-1116 @3f38c8287f1 (awaits COORD approve).
- CTS reads (epyc8 fable-fix-s81-coltap/an/p5_<fam>_cts + .out): r2 -46.8 (1 under -42; reset class gone, ROM q -11.4, a -21.2); r1 -93.4 (9; lpl_r chunk -> t payload 763 um); h10_r2 -204.2 (14; t/so -> ist_frame_int_o 1135 um, y_rt_a -> n/a 712 um). Place images LOOKED PASS (localhost scratchpad col5/).
- Route clients intel2: 687024 (r2) 687025 (r1) 687026 (h10_r2), logs pilot5_<fam>_route.log. Still at cts goal: 313861 (h9_r0_p2), 313862 (h10_r0_p1): LOOK + stage_sta cts, then same route command.
- TODO at GRT: stage_sta.sh KIT OUT grt (r310), GRT overflow, post-DPL reset hop table, FF hold; post col-wave1 / col-wave2 RESULT; then sign-off + export (AGIdock /archive/opentallas-signed-1114 + rtx-pro).

## 18:4x relay regex class (r0 families)
- h9_r0_p2 CTS -1099 / 3,676 under -42: OT_RELAY_MID_RE in config.mk is [.]u_y_ (gen_phys default, budgets.relay_mid_re), r-flattened relays (u_u_r0_u_y_xo*, u_u_y_rt_*) not matched; Codex GEN env [._] is not read by gen. NOT routed.
- Sibling kits epyc8 countable_F2s4tapfix1/gen_rm2/<type> (pristine E10 kit + config.mk regex [._]) for h9_r0_p2, h10_r0_p1, h10_r2 to CTS: intel2 logs pilot5rm2_<fam>_cts.log. Read OT_HOOK_COVERAGE hook=relay_mid + stage_sta cts; if good route rm2 kits (and stop caring about gen/ h9_r0_p2, h10_r0_p1; gen/h10_r2 route continues as comparison).
- If confirmed: gen_phys RELAY_MID_RE default -> [._] (branch, test, gate) + plan budgets row via S81-DIE-R. r2 / r1 placed with the old regex (y_x / y_rt relays unplaced there too; r2 CTS -46.8 anyway).

## 19:1x
- Relay regex [._] confirmed (gen_rm2 h10_r2 CTS: 2 under -42, both t7/so -> ist_frame_int_o0_0, -304.8, 1,181 um). rm2 h10_r2 route client intel2 963708 (log pilot5rm2_col_h10_r2_route.log). rm2 h9_r0_p2 (721642) / h10_r0_p1 (721643) still to CTS.
- gen_rm3/h10_r2 = pristine + regex + istations.tcl per-bit sites (q[382], q[383] of ranks 0..2 at 702.196, 34.56 / 23.04 / 11.52); client 972763, log pilot5rm3_col_h10_r2_cts.log. Read: epyc8 an/stage_sta.sh KIT an/p5rm3_col_h10_r2_cts cts. If good -> route rm3 (it is the candidate to sign), row to S81-DIE-R.
- TODO flow: gen_phys RELAY_MID_RE default [._] on branch (epyc7 repo, new branch from main), test, gate, READY.
- STRIP worker resumed with COORD r392 items (t8 taps, follow six leaves, hosts not pinned). IFN0 worker: balanced halves in GRT.
