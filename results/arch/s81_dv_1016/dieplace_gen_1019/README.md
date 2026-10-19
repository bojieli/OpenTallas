# S81-DIEPLACE GEN candidate (opt-in, 10-19) — input for mu3/mu4 GEN

Branch claude/s81-dieplace-gen-1019 = codex/s81-mu3-1019 + codex/s81-dieplace-serdes-1019 + this lane.
Default flows are unchanged (no flag/env -> byte-identical paths).

(b) Plan `plan.json` = `dv_plan --pathfix --placefix --reset-space` + `serdes_slot_candidate.py --reticle-reserve-um 256.55`:
eight MU1 SerDes slots 518.4x3844.8, die 32486.9x25000 (W/E reserve 256.55 declared per the 08:47/08:54 approval,
default 500 kept). Blocks/links identical to Codex reset_space_1019/plan.json. Max hop 404.9 um, 0 over 405,
0 block/band/relay overlap, worst cut 0.5663, 3182 stations / 864100 bit-stages. PNG viewed (serdes_slots_1019/diagnostic.png).
Scribe/seal/PDN keepout fit is still owed (no structure removed).

(a) Reset: `OT_RESET_LEGAL=<obstacles.json>` (tools/s81_dv/reset_legal.py, dv_bind.reset_tree_legal). Obstacles come from
`dv_rvcase --dump-obstacles` (blocks, relay bodies, CLOSED landing footprints as placed, lane bands). Tree on mutually
legal R0 slots (0.048 lattice, 0.5 clearance), BFS with <=8 children and <=16 sinks per station, EXACT R0 pin reach
.o->.i/.rs <=405 um; sinks to body centre + half-perimeter/2. Every landing-calendar release (hop-0 ICG enable, landing rs)
is DELIVERED at its physical sink: a station of that release depth within reach, else calendar-chain stations (rsg_c*)
on free slots. Releases are only raised to the earliest physically present one, keeping E_land+RL-E_gate = N mod 2
(K, lane ages, G-R0 unchanged; one-time reset latency recorded as reset.calendar_release_shift). dv_rvcase places each
body AT its slot (no spiral) and re-measures every reset connection on placed bodies (case/reset_reach.json, FAIL > 405).
The old isolated st_rs_38_7_1 problem disappears: the tree is rebuilt, its consumers are sinks served by legal nodes.
Native regional clock/RC/PG of the reset stations still owed.

(c) `lane_age_delta.json`: vs record mu2 plan p4l_lkcol_mu_pf, 20 links change station count (3113->3182); compiler lane
age delta = ceil(N'/2)-ceil(N/2) at the same K (hist 0:4, 1:7, 2:3, 3:1, 4:3, 5:2; max 5 edges); bundles to re-equalise
f_4L03, f_4L13, jw_E->rsv_11. Landed lanes have stale die-STA E: dv_land_pilot must re-derive E/K on this case's STA
before any gate; until then the case is PILOT_NOT_A_GATE.

Run: `run_gen.sh <dir> <source_sha> <main_sha>` (pass1 emit-only -> obstacles -> strict bind with legal reset -> case -> GRT/STA).
Tests: tools/test_s81_reset_legal.py (3 PASS), tools/test_s81_rv_placement.py (7 PASS).
