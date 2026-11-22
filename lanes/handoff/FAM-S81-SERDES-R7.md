# FAM-S81-SERDES-R7 handoff (started 2026-11-21 19:0x PST, successor of FAM-S81-SERDES-R6)
Read also: lanes/handoff/FAM-S81-SERDES-R6.md, lanes/posts/FAM-S81-SERDES-R7.md. Client logs: intel2 ~/fam-s81-serdes-r7/*.client.log.
Lane dir epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7 ; lane clone epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7-core (main 5aab47bd4b + branch claude/s81-bm-keep-th-1121 b4d98fc16875, NOT pushed yet; untracked copies physical/fam_views/ot_s81_kp4_dchn + physical/ref_tile/s81fam_kp4_decc from epyc7 fam-s81-serdes-core; route_core_r7.sh).

## dec (decoder hard core ot_s81_kp4_dec_lp_core)
- dec_j6c official routed LEC (rt a87de12be91a) = NOT EQUIVALENT 33 pts (d[45][*], gold-only key u_bm.th[11][10]). NOT exported. COORD ruling: keep + rebuild.
- Cause found: th[11][10] is a lec.py-made slang key (not in RTL/gold.map); gold th[45][0..1] missing from keys; gate kept one theta_45 flop named g_pe[45].thq[1] (aliased) matched by name. Posted to COORD + FLOW-OPS-1300.
- Fix: (* keep *) on th in ot_s81_kp4_bm.sv. New synth netlist keeps th[45][0..9] by name.
- dec_r7k rebuild epyc9: intel2 ot-run PID 2907958, unit oth-ubuntu-1620888-1795318810, out epyc9 fam-s81-serdes-r7/build/dec_r7k(.log/.exit). Next: signoff (as dec_j6c: signoff.py name s81fam_kp4_decc, MATCHING TC_LIB_FILES 5 std + 3 macro libs per corner, see R6 14:30 post) -> official routed LEC (lec.py rt current, kit like dec_j6c source_compare/lec_kit) -> EQUIVALENT -> ot-push-main the keep commit -> ref_tile export + AUTO-EXPORT row.
- Early check: official LEC on the dec_r7k SYNTH netlist: intel2 PID 3173474, kit epyc9 fam-s81-serdes-r7/lec_synth_r7k/lec.

## J8 gates (epyc9, plain copy candJ8s of sealed J7eL6, nlink 1, ref_tile excluded)
- gate_j8s.sh = J7eL6 + the 6 handed serdes START ops (R6 full plan also held the dropped t16 writer, so it is NOT the gated plan; plan_j8s.json is). gate_j8p.sh = j8s + PHY/ENG pair delta (fam-s81-misc-r4/phy_eng_window_codex/phy_eng_pair_delta.json, 28 ops) + eng measured view lib delta (+ engrr_vJ_eco1_1108 view files). Chain intel2 PID 1606128; logs ~/fam-s81-serdes-r7/j8s_gate2.client.log, j8p_gate.client.log; gates epyc9 fam-s81-serdes-r7/gates/J8s, J8p.
- Next: post both verdicts to S81-J6-ASSEMBLY-R5 (J8 rows). If J8p passes: private-spec s81 phy__t1 --plan plan_j8p --tree candJ8s --host epyc9 --src-manifest off (proof) for the PHY corner leg.

## PHY corner leg (phy__t1) - now this lane
- No current-event wave row (OWNERS REVIEW, last a6 cancelled superseded). Codex private work intel2 fam-s81-misc-r4/phy_corner (repeater reseat 729->131 um, post-CTS TT -446/FF -305, hold -617) and phy_eng_window_codex (paired PHY/ENG windows, upper-east taps, CBR7 reseat 14 stages): internal setup -270 TT after local taps. Delta = the J8p rows above.

## Others
- t4 unsplit private kit (oth-ubuntu-293099-1795284746, epyc10) DRT; waiter on route stage. If signs: signoff -> LEC -> export; tell S81-J6-ASSEMBLY-R5 to release struct stop bf6905ce91d07.
- t12 a4 / t16 a4 wave running; t14 a5 ENQUEUED. Codex t14 fixes = ODB move chain (t14_a5_geom_only_1415/*_1415/moves.tcl) incl. reset copies (netlist edits) -> not a positions-only overlay; NOT yet converted to a private-spec.
