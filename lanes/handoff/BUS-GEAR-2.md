# BUS-GEAR-2 lane handoff (S81 x feed 2:1 bus gear) -- PARKED 2026-11-12 09:2x PST (owner default 09:15, COORD)

## 1 Scope
S81 x feed 2:1 gear (street lever 4). PARKED: gearing all 72 x lanes clears only 1 of 5 street cuts (s_2N_L1) and 1 of 19
station/macro overlaps (t65 ft4), at -20% AR (cadence-2 BOUND rule, the only form that compiles) or +76.6k um2 banked calendar
ROM + re-sign. Street remainder is DIE-S81-88's (leaf ft-slot re-floor: stations/detours, ready12b).

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/bus-gear-1, branch claude/bus-gear-1-xint-1112 @ 877cfc14f1 (hub), clean, UNMERGED (keep).
877cfc14f1: TX framed by word valid xw_v (x[1] lanes 0/1, x[567] lanes 2/3 = xs4 xw_q[0]); sticky flt into u_frs_<slice>_C (NL+1);
die_b178_xg.v regenerated; EQ bench v3 (MUT/SEED plusargs; MUT4 = phase-lock removed); TX smoke run_tx_smoke.sh.
cabebb8f2a: tx_release.py + tx_release_r12ng.json (16 slice TX reset depths 47..77, both parities).

## 3 Running jobs
None after the pkg7 H=3 runs end (epyc2 /srv/opentallas-scratch2/claude/bus-gear-2/pkg7, ot-run, own). Nothing to restart.

## 4 Watchers
None.

## 5 Results (final RESULT posted 09:2x)
- Strict bind v2 (877cfc14f1) on ready12ng 77cad171 + plan_xg faaabbe825b4: ELAB rc 0, BIND rc 0 (epyc9 bus-gear-2/r12ng/out_bind;
  v1 out_bind_v1 rc 0). 873 crossings, bits 606,281 -> 566,825; bound_stages = plan_cycles on all buses.
- EQ pkg7 H=2 h9+h10: all mutants caught (MUT1/2/3/4); MUT0 PASS at SEED 2/3; SEED 1/4 one XEQ_PHANTOM at frame B edge 7/8 =
  start-up window: xframe_gear forward relays release on rst_n, frame band forwards only after its reset age (lpr_root age 6).
  Fix if revived: release/gate the xframe_gear forward on the frame's aged reset.
- G0: 74 -> 72, s_2N_L1 cut + t65 ft4 gone; 4 cuts + 18 geometry remain with all lanes geared. Cut dumps epyc9 r12ng/cut_base.json,
  cut_xg.json (tool r12ng/cut_dump.py). Street per-type table posted to DIE-S81-88 (no measured GRT exists for t32/t57/t3/t43/t28/t46;
  placement estimates channel_v 1.7-6x over).
- Calendar ROM pricing: 8192-row monolithic fails SS (clk->q 933-1004 ps); banked 2x4096x72 per calendar ~700 ps SS, +76.6k um2.
- TOK: compiler x_cadence (TOK-VERIFY-2 claude/tok-verify-2-xcad2-1112): BOUND -20% AR compiles; EXPECTED faults (4424 > 4096 rows).

## 6 Next steps
None (parked). On revival: fix the start-up forward release, run H=3, ready12b prep (prep_r12ng.sh SRC0/AB0) + rebind_v2.sh, price A/B.

## 7 Open asks
None open for this lane (DIE-S81-88 x[567] confirm moot while parked).

## 8 Gotchas
- ot-run script must sit inside --dir; epyc7 load gate is slow, use epyc2/epyc9.
- crs4 markers x[0]/x[566] are constant 1 after release; word valid is x[1] (= x[567]). No go tag in x.
- EQ: bubble upper beat is don't-care (RX OGATE 0); compare landed words only on valid edges.
- Never edit bsrc4_* trees (DIE-S81-88's); my copy is r12ng/bsrc_xg.
