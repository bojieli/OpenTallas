# FIX-RELAYPOLY handoff 2026-11-14 08:51
Branch claude/fix-relaypoly @11a2f6e23c4 (intel1 /srv/opentallas-scratch2/claude/fix-relaypoly/wt), based on origin/main b4c5665391d. Files: tools/die_plan/relay_mid.tcl, test_relay_poly.py (copies in FIX-RELAYPOLY-files/).
Env gate OT_RELAY_POLY=1 (off = old behaviour incl FIT). Auto: if the straight line crosses a macro grown by OT_RELAY_POLY_PAD (6.5 um) a turn-penalised grid path (OT_RELAY_POLY_GRID 8 um) is used, stations even by length. OT_RELAY_POLY_FILE lines "<glob | re:<group_re>> x y x y ..." (um) = plan relay_polylines polyline_um (points between source and sink); a match also makes soft-source heads (lpl_*.u_y_q -> y_rt_20a_5) legal chains. OT_RELAY_MID_DEPTH (default 4).
Proof col_h9_r1 pv47efee8f 4_cts (intel1 .../fix-relaypoly/r1_*): GRT overflow 0 in all forms (poly auto, poly+n20 waypoints, +slot blockage; control straight line also 0 but 400 iterations vs 64). n20 chains hop 227-316 um.
CAVEAT hop median: relay2.py on r1_polyA still shows 45 bundles with median >405 um (control 42), all from non-relay sources (u_d10_6_Y.q, lpl_10_w.e) into relay groups, chains the kit does not place (soft/non-fixed ends); the n20 wall crossing is fixed, family-wide hop <=405 needs R-COL-3 regex (OT_RELAY_MID_RE) + chains with soft heads via relay_polylines.
Deployed (backup relay_mid.tcl.bak-relaypoly-1114): B3x2b/src on epyc7/8/9/intel1/epyc10 (previous file == origin/main). B3v/B3w/B3x untouched.

## CLOSE 2026-11-14 09:43
Final: branch claude/fix-relaypoly tip a314ef848ea (relay_mid.tcl 5eb1efc09a63, gen_phys emitter + tests); deployed B3x2b/src on epyc7/8/9/intel1/epyc10 (backups relay_mid.tcl.bak-relaypoly-1114b); ovl_b3y gen_phys patch in FIX-RELAYPOLY-files/.
r1_b3z (DIE-S81-92 soft-head entries) GRT: overflow 0 at iteration 64. Counting only data (D) pins, hop>405 bundles: control 22, polyline runs 21 (n20 pair 772/735 -> fixed); the earlier 48 included one reset-flop (u_d10_6_Y.q) fanning to RESETN pins - not data hops. Remaining 21 are structural per DIE-S81-92 (advisory 405 um).
Anchor-to-head experiment (r1_anch, uncommitted relay_mid.tcl edit in /tmp only; run killed) dropped per COORD ruling; not on branch.
Proof dirs: intel1 /srv/opentallas-scratch2/claude/fix-relaypoly/{r1_line,r1_poly,r1_polyA,r1_polyslotA,r1_b3z}.
