# DIE-HBM-24 (HBM die owner, 2026-10-29 18:36- PDT)

## HBM-044 (A) -> plan d23c (CHECKED)
`side_drop.py` on d23a 4133ce1e4e0d -> **d23c die_plan 77d613ccd600** (intel1:/srv/opentallas-scratch2/claude/die-hbm-24/plan/d23c).
Removed per type (q_su00/01/10/11 + __physical_v1, 8 types, one each): the side hard core u_su_Q<q>_side_softplus|rest,
its clock tap, and the instance sidecar rows (core_conns 8, clock_entries 8, clock_taps_die 8). The side cores had no
contents, stations or buses (core_conns = clk_side tap only); the script fails closed otherwise. 0 cycles, no RTL.
G0 PASS 0 err; G0C 8 = the d23a set (core_faces q_hub_ne/nw), 0 new. Report d23c/side_drop_report.json.
Codex adopted d23c for its all-gap bind (codex/hbm-bind-1848@a48995b3c results/hbm_bind_codex_1848): strict FAIL
163 = 92 UNPLANNED (82,285 b) + 71 EMIT; HBM-044 side-core EMIT gone.

## --all-gaps strict bind (OWNER 18:40)
My draft (claude/die-hbm-24-1029@edbd6445029 on the hub, NOT for merge) was adopted by Codex as 47eed2ef4 + crash fix
e37f82f82 (skip rejected ID leaves); both already on hub main (0a3f2040d62). Check (CHECKED, intel1 docker py3.12):
test_bind_all_gaps 2 tests FAIL on main 1ab03f66914 bind.py, PASS on the Codex bind.py; bind/reset/parent-id suite
56 files: tip 305 pass / main 301 (+2 new +2 of my wavefront tests), tip failures a subset of main's (all env/sparse).

## Plan d24a = d23c + 10.8-um macro channel fold (COORD 19:09 HBM-CORES-KITS-22-PARK (3)) (CHECKED)
`macro_fold.py` folds the HBM-CORES-KITS-22 `_b` placements (intel1 hbm-cores-kits-22/k2/mp) into core_macros.json;
die_plan.json byte-identical (77d613ccd600); core_macros 5047d56dac7e. Fails closed unless every rect is inside the plan
outline and every facing pair is abutted or >=10.8 um apart.
| core | macros | old min channel | new min channel |
|---|---|---|---|
| hfd_ep_static | 0 -> 4 | (none declared) | 21.576 |
| ot_hbm_host_cp_rxs | 6 | 8.64 (4 violations) | 10.8 |
| ot_hbm_su_static_sfustore_hw | 16 | 6.48 (5 violations) | 10.8 |
G0 PASS 0; G0C 8 errors and every message identical to d23c (0 new / 0 gone).
Open (not folded): cp_rxs kit outline 434.808x302.4 vs plan 434.808x480 (macros fit both); sfustore plan outline
362.88x388.8 but its pins file is the fr17 336.96x328.32 table and fr17 AUTO-GEOM FAILs fill .032/empty .859/r2r 559.8
-> outline/plan item; EP core_macros macro_placement_tcl still names the old 250.56x375.84 tcl.

## Far pairs (partial, sub-lanes stopped at the 19:00 usage limit; Codex FT/L7c covered 18:47-19:03)
- V1 SFU re-home ESTIMATE (v1/v1_est.py, opt3 pair model, UNCHECKED): VL3d far rows 79 -> 75 (b111<->spu1 or
  b113<->spu0 swaps); best row enumeration 67 (8 NW partitions moved). No SFU move alone approaches 0 far pairs.
- L7: l7/ scripts only (Codex L7c covers it: 0 lanes lost, G0C 12 core_faces). V2: v2/ scripts only (Codex
  codex/hbm-ft-1849@e5df1bc90: 12 lanes / 10 rows / 1560 b on L7c).
