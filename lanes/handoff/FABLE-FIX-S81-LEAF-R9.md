# FABLE-FIX-S81-LEAF-R9 handoff (Fable; succeeds R8; owns ot_s81sl_leaf__t* + kv_leaf t1 t3 t4)

NOTHING IS SIGNED. COORD 20:4x: no stand-down at 330k; this file is the lane memory. R7 / R8 handoffs stay valid for background.
Lane dir: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r9 (R9): clone/ (tools lane clone), rg68b/ (plan b), g68b/ (gate out), g68b_src/ (real-copy tree), tmp/.

## 1. RG9 G0 fix (40 errors) -- plan b 34f49cfcead7 in gate
- Cause of the 37 tap errors: s81_hi_corridor.move_lanes shifted each lane core tap rigidly with its lane. The J7 taps were already stale (tap to clk pin distance up to 948 um, 470 of 1088 over 25 um). Source rule = early_core_taps.add: tap = schema.tap_clear(core clk pin, clear 4.32).
- Tool fix (PUSHED main 121f83f21219, 21:0x): s81_hi_corridor.retap_lanes + core_clk_pin + core_tap_errors; move_lanes(root=) derives the taps of moved lanes again; leaf_regrid check fails core_taps_bad; new subcommands `retap PLAN --base BASE --root TREE --out` and `nudge PLAN --move TYPE:LANES:DX,DY`. Tests added in test_leaf_regrid.py (41 pass with test_s81_hi_corridor.py).
- Plan b = R7 rg68 plan 4a21da90a576 + retap (all lane taps within 6.5 um of the pin, one at 8.6) + nudges: t32 lanes 14,13,5,4,8,11,3 by (0,-17.28) (cut 10750 through s_3S_L0), t62 lanes 7,6 by (0,-43.2) (cut 20000 through s_6N_L1). 0 cycles, netlist unchanged (6017c662438f). Script R9/r9_mk.sh, reports rg68b/retap.json nudge.json types_changed.json (66 types differ from rg68).
- G0 subset (taps/cores, cuts, pin_sites vs J7 report): R9/mk.otrun.log line "QC errors" (unit oth-ubuntu-556877-1795321785).
- Gate b: unit oth-ubuntu-799195-1795322160 (intel2), script R9/r9_gate68b.sh, client log R9/g68b.otrun.log, ends R9_GATE68B_DONE. G0 runs beside elab / bind. Pass = G68B_ELAB_RC=0, G68B_BIND_RC=0, G68B_LAT {dn_s_1S_L2 14->15, dn_s_6S_L1 10->11, up_s_2N_L1 3->5, up_s_6N_L2 11->13} 873/873, G68B_G0_NEW_ERRORS 0, G68B_PRE_RC=0.
- Green = hand plan b + netlist + the tool commit to FAM-S81-MISC-R4 and S81-J7-HELD-R1 (J8), and report to COORD.
- Old gate oth-ubuntu-875159-1795316235 CANCELLED (COORD 21:0x). Gate b 799195 CANCELLED by me: plan b G0 subset cleared 37 taps + t26 + both cuts but surfaced s_2S_L0 (t22) 0.60 at cut 10750 (a J7 WARN, now the worst segment). Plan c = plan b + t22 lanes 14,13,5,4,8,11,3 by (0,-17.28): unit oth-ubuntu-1991745-1795323204 (R9/mk.otrun.log); on QC new 0 the gate starts by itself, log R9/g68c.otrun.log (same script, markers G68B_ / R9_GATE68B_DONE).

## 2. t39 proof (plan ad13e176f283)
- Bind B oth-ubuntu-3601082-1795320157 (epyc7), log R8/bindB.otrun.log; armed chain (intel2 PID 3546224, log R8/t39spec/chainB.log) runs R8/r8_chainA.sh b1 --ver src_a bind_b on BIND_RC=0. Then read L/lat_b.log (+1 on VER pre-approved), carry the kit to sign-off; if run-item stops at geom: run_kit.sh GOAL=route through ot-run.

## 3. J8 orientation rows (after t39 signs): not written. Census R8/vsw_census.tsv (36 types <= 17.3 um; t3, t43, t12 need a different fix).

## Update 21:2x PST
- Plan c 8c21a4c06257 (plan b + t22 nudge): G0 subset 0 errors in taps/cores, cuts, pin_sites (0 new vs J7, 2 J7 cut errors gone). Gate c running on it: log R9/g68c.otrun.log (unit in its header), markers G68B_* / R9_GATE68B_DONE, tree R9/g68b_src. Plan b / gate b are superseded.
