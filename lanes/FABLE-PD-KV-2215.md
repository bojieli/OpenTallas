# FABLE-PD-KV-2215: structural review of KV plan events 7uh, 7v, 7w, v21 ring split, 7p pv delta (2026-11-15 21:55 PST)

Read-only review under r199. MEASURED = computed by me today from the named plan JSON, gate output or table.
REPORTED = from a lane post. INFERENCE = my reasoning, not run. I ran no build, bind or OpenROAD; only Python
readers of the plan JSONs (scripts `/tmp/fpk2215_s*.py` on epyc7 and epyc10). Nothing launched, stopped or edited.
Prior review FABLE-PD-KV-1945 is not repeated; sections below are what changed since.

Inputs: epyc7 `/srv/opentallas-scratch2/claude/kv-102/kvgeom7/` (kvgeom7u / 7uh / 7v / 7w / 7p `.json`, `*.gate.out`,
`*.pingate.out`); epyc10 `/srv/opentallas-scratch2/claude/kv-hgsplit-1115/` (v21 plan 2b180eb7da4b, `out/v21*.out`,
`disp_v21c.tsv`); 7u base = `kv-102/adopt_kvgeom7u/plan_c.json` b7156937f334.

## 0. Verdict

| event | plan sha | blocking finding (r199: measured, released type) | verdict |
|---|---|---|---|
| 7uh (hroot start origin + tap split) | 68a458bd5824 | none | adoptable after its c1-tree gate |
| 7v (ECTL krsp +5 / rq +3) | 685e18352c8e | none | adoptable alone, but see 7w x v21 |
| 7w (7uh + 7v) | 829954a7dfc7 | none | adoptable alone, but see 7w x v21 |
| v21 ring split (7x) | 2b180eb7da4b | none; strict bind still running at 21:50 | adoptable when bind + LATCHECK pass |
| 7p pv delta (D=3) | 60d186d82b30 | none | do NOT adopt: superseded by 7y (D=4) |

No event touches a released (signed) type, so nothing is BLOCKING by the r199 definition. One finding is a hard
compose condition all the same: **7w and v21 collide on 7 of the 8 hg types** (section 3). Each passes its gates
alone; the merged plan has never been gated, and G0 does not check a station site against a hard-core footprint.

## 1. 7uh: kv3_hroot only

MEASURED (diff 7u -> 7uh = 79 leaves, all under `partition_types/kv3_hroot/clock`):

| item | 7u | 7uh |
|---|---|---|
| reader start origin rect | [181.9, 6.5, 199.2, 19.4] | [1568.2, 365.0, 1585.4, 378.0] |
| reader depth / writer depth | 7 / 7 | 5 / 7 |
| reader hops (origin -> stages -> band centre): max, over 340, over 405 | 399, 1, 0 | 348, 4, 0 |
| writer hops: max, over 340 | 314, 0 | 340, 0 |
| raw reset hops: n, max, over 300 | 28, 326, 18 | 28, 326, 18 |
| added taps / `tap_max_sinks` | 35 / 1200 | 36 / 1500 (new `clk_t40` at 1795.4, 276.6) |
| pin `cland_tstart_in` (M7, ctl) | (190.56, 19.98) | (1576.8, 369.9) |
| gates (tools18 + pinned r8 53d6d7b1dc9a) | | G0 0 errors (2363 warnings, same as 7u), bind 0, R8 recheck 0, LATCHECK 2404/2404 |

NON-BLOCKING findings:

1. `cland_tstart_in` is now the only one of 102 landing pins more than 30 um from every face: 324 um from E,
   370 um from S, on M7. In 7u it was 20 um from the S face. hroot is a soft type (`hard` false), so the die net must
   cross 324 um of the partition on M7 or above to reach it. G0 does not check this (warning count unchanged).
   The 1654 -> 348 um gain inside the type may partly move to the die side. DIE-KV-ROUTE-1 should state the die-side
   length of this net before volume. Not measured by me.
2. Four reader hops are 348 um (ft8_i, ft9_i, i_fch_pc_Q_N_q + 1): over the 340 target, under the G0 limit
   (`budgets.ft_station_max_um` 405). 7u had one hop of 399. Net improvement.
3. `tap_max_sinks` 1200 -> 1500 is a relaxed limit, not a measured window. Worst tap 1486 sinks (REPORTED). The tap
   window is proven only by a routed kit; hroot has none on 7u (DRT-0255 class, 1945 section 3c).
4. No c1-tree gate output for 7uh / 7v / 7w exists in `kvgeom7/` at 21:50 (only `kv102t18_*` trees). The c1 re-gate
   with OT_HCPARAM_ALL on is REPORTED in flight.

## 2. 7v: ECTL depth on the 8 hg frames

MEASURED (diff 7u -> 7v = 202 leaves): `internal_stations` 29 -> 34 rows on each of the 8 hg types; 64 lanes change:
32 lanes 5 -> 10 cycles (krsp +5, L2053..L2204), 32 lanes 5 -> 8 (rq +3, L362..L486); LATCHECK 2404/2404 on the pinned
bind (r8 1693daf6da40).

| row | bits | hops (um) | last station -> pin |
|---|---|---|---|
| krsp -> ectl_q0 | 512 | 374, 272, 270, 206, 360 | 152 |
| krsp -> ectl_q1 | 768 | 374, 272, 270, 206, 84 | 140 |
| krsp -> ectl_q2 | 768 | 374, 374, 374, 263, 120 | 161 |
| krsp -> ectl_q3 | 512 | 374, 374, 374, 374, 329 | 160 (farthest pin 244, REPORTED) |
| rq q0 -> face W | 39 | 366 x 4 | - |

NON-BLOCKING findings:

1. 10 of 20 krsp hops are 360-374 um: over 340, under the station law used on KV rows (380 in the row notes, 405 in
   G0). q3 has no slack to take a detour: four hops at 374.
2. The plan is only valid with the four ectlk cores at QK 37 / RL 26. The guard pair CORE_QK / CORE_RL fails
   elaboration against 36/25 views by design (REPORTED KV-ECTLK-RL). I found no post that the cores37 q0-q3 builds
   signed off. Adopting 7v or 7w before those views exist turns every hg kit into WAIT-CHILD. q2 also carries the
   M3 edge class of 1945 section 1.
3. G0 does not check the `rsp_data` hops (no core_conns sidecar for ectl; REPORTED KV-ECTLK-RL). The hop numbers
   above are plan arithmetic from window centres, not per-bit.

## 3. v21 ring split, and its collision with 7w

### 3a. v21 alone (MEASURED, plan 2b180eb7da4b vs 7u)

| item | value |
|---|---|
| rings as hard cores | 106 in 19 types, 16 masters, 0 soft rings >= 250 bits left |
| band-centre displacement | median 19, p90 214, max 390 um; 1 over 340 (kv3_hg_v3 i_slg_Q_N_krsp); 28 over 110 |
| v20 for comparison | median 117, max 1000, 27 over 340 |
| forwarded-clock pin -> ring rect | 0 over 405; 2 over 340: hgi_v5 ft17_i 371 (7u 347), hgi_v7 ft17_i 349 (7u 148); hgi_v8 ft17_i 323 (153), hgi_v4 ft17_i 310 (249) |
| `max_pin_to_band_hop_um` | byte-equal to 7u on all 106 rings (46 values over 340, max 402.6): NOT recomputed after the move |
| existing clock taps moved | 0 in all 19 types; +2 to +9 taps per type = one `cl_*.clk` core tap per ring |
| reader start max hop | hgi_v8 336 -> 378; kv3_hg 306 -> 335; hgi_v1 (both) 301 -> 335; others unchanged |
| raw reset hops over 340 | hg_v1, v1p2-p4: 7 -> 10, max 366 -> 403; hgi_v3: 11 -> 18; hg_v3 30 -> 22; hgi_v7 26 -> 22; rest equal |
| reset `local_taps_um` | unchanged in all 19 types; none inside a ring |
| hard-core area share | hg 49.9 -> 51.3-51.9 %; hgi 38.4 -> 39.6-41.4 % |
| plan cells | hg_v1p2-p6 4.97 M -> 176-179 k; hgi_v3-v8 3.03-3.09 M -> 73-91 k |
| channels between a ring core and another hard core, facing > 20 um | 28 under 8.64 um, 77 under 17.28 um, 0 overlaps |
| gates | G0 0 errors (2385 warnings; 7u 2363), worst segment 0.5027 -> 0.5195 at horizontal@17250:hgi_EN_5; v21n (same geometry, no raw rows): bind 0, R8 recheck 0, LATCHECK 2404/2404; v21 strict bind running since 21:21 PST |

NON-BLOCKING findings:

1. "Taps re-solved" means core taps added. No existing tap moved, so the tap table of every hg / hgi type grows but
   keeps its 7u rows. Good for the clock window; the new taps add 52 TAP-RADIUS-TARGET and 8 TAP-LIMIT-INFO
   advisory lines in G0.
2. The narrowest channels: 5.18 um between `cl_..._u_ctl_qo` and `ectl_q1` on 7 hg types (36-71 um long); 7.78 um
   between `cl_i_ectl_Q_N_tN` and `head2_e6` on 10 hgi types (52-216 um long); 8.21 um against head cores on hgi.
   Both sides are blanket M1-M5 OBS cores. If either facing side carries pins, all of them escape through a
   5-8 um slot: the capacity-0 gcell class that held m7hg_g in congestion for hours (FABLE-PD-KV-1450). I did not
   read which faces carry pins.
3. 16 of v21's own station sites sit within 4.32 um of a ring-core edge (hgi_v5 3, hgi_v8 2, one each on the 8 hg
   types, hgi_v4, hgi_v7), none inside. The station bit column will straddle the edge.
4. The raw reset chain on hg_v1 / v1p2-p4 gets longer hops (max 403 against `reset.relay_um` 300). The same class
   exists in 7u (hgi_v8: 70 of 70 hops over 340), so it is not new; v21 makes it worse on 5 types.
5. 16 ring masters are mostly unsigned (REPORTED). Every hg / hgi kit waits on them.

### 3b. 7w x v21 (MEASURED: 7w station rows against v21 hard-core rects)

| collision | types | detail |
|---|---|---|
| krsp q2 station S5 (605, 1300), 768 bits, inside ring core `cl_i_astk_Q__u_strip_u_strip_u_ctl_qo` [544.3, 1261.4, 637.2, 1316.7] | hg_v1, v1p2, v1p3, v1p4, v1p5, v1p6 | 6 sites |
| krsp q3 station S5 (925, 1300), 512 bits, inside ring core `cl_..._g_ep_N__u_ep_zo` | kv3_hg [889.9, 1201.0, 931.4, 1313.3]; v1p5, v1p6 [872.6, 1252.8, 958.2, 1307.2] | 3 sites |
| rq leg (30, 731) -> (30, 365.5), 39 bits, runs through ring core `cl_i_slg_Q_N_krsp` (x 8.6-51.8, y 371.5-590.5) | all 8 hg types | detour about +50 um on a 366-um hop: about 416, over the 405 limit |
| krsp launch: ring core moved 295-298 um (390 on hg_v3) from the (123, 277) point the row starts at | all 8 hg types | first hop must be re-measured from the new core's q face |

- Only kv3_hg_v3 is free of a station-in-core hit.
- The q3 row is the binding one (four hops at 374). Moving its S5 out of the ring core lengthens hop 4 or hop 5.
- v21 was sited against the 7u station list; the 7v rows were sited against the 7u bands. Neither lane saw the other.

Fix (one compose, not two events): KV-HGSPLIT runs hgsplit21 on **7w** as base, so the 5 new station rows are in the
keep-off list; KV-ECTLK-RL re-sites S5 of q2 / q3 and the rq column against the ring boxes; then raw rows, bind,
LATCHECK. Add a G0 check "FIRM station site inside or within 4.32 um of a hard core" so the class cannot pass
silently again.

## 4. 7p pv delta

MEASURED (diff 7u -> 7p = 34 leaves): one type changes, kv3_pv_v1n (internal_stations 18 -> 109, raw rows, reset
local taps, define OT_PV_VPORT_SELREP32); 27 latency entries; `clock.core_link_pipe` with F1 D=3, **F2 `y` D=3, F4
`out_v_lo` D=3**.

| item | value | source |
|---|---|---|
| gates on tools18 tree | G0 0, bind 0, PVX_CHECK PASS, R8 recheck 0, LATCHECK 2404/2404 | `kvgeom7p.pingate.out` |
| gates on c1 tree | same, except BIND4 RC 1: HARD_CORE_PARAM_ALL pv_join_t RESET_PIN (registry record, REPORTED wrong) | `kvgeom7pc1.pingate.out` |
| trunk | TRUNK_D as-built 54 -> 73, FLAG_D 58 -> 78, C 19 | same |
| pad flops | column pads 272,164; VDH shared estimate 898,520 (unshared 7.25 M) | same |
| legs over the hop limit at D=3 | F2 204 of 2,051 (9.9 %), F4 409 of 2,048 (20.0 %); at D=4: F2 2, F4 0 | REPORTED KV-PVGEN placed read |
| leg lengths | F1 max 988; F2 max 2297, p99 1402; F4 max 1396 um | REPORTED KV-PVGEN |

NON-BLOCKING findings:

1. 7p as composed carries D=3 on F2 and F4. The owner lane's own placed read puts 10-20 % of those legs over the hop
   law. r224 already ruled D=4. 7p is a gate proof only; 7y replaces it.
2. D=4 changes the alignment groups (6/6/7 -> 10/10/11) and the y lane by +11, so TRUNK_D, FLAG_D and both pad
   tables must be rebuilt for 7y. The 7p numbers (73 / 78, 1.17 M pad flops) are not the 7y numbers.
3. About 1.17 M pad flops (272 k + 899 k estimate) come on top of pv types planned at 6.99-7.02 M cells. G0 warning
   count is unchanged (2363), so the cell budget does not see them. Area and GRT cost in the pv region is unpriced.
4. `lp_even.tcl` FIRM equal-hop siting merged to main at 7f435727cde, after the c1 tree's main 8989ba7b1755. A 7y
   gate on c1 needs the pvgen patch as a listed overlay, or a tree rebuilt at the newer sha.
5. Two F2 legs stay over the limit at D=4 (max 2297 um). They need a station row or a named exception.
6. Only pv_v1n carries the pipe. The other 15 pv types are unchanged by 7p.

## 5. Adoption order

1. **7uh now**, as soon as its c1 gate passes. One soft type, no RTL, no dependency, 79 leaves.
2. **One hg event = 7uh + v21 + the 7v rows re-sited** (section 3b), when: v21 strict bind and LATCHECK pass, the
   ectlk 37/26 views exist, and the merged plan passes G0 / bind / LATCHECK. Do not adopt 7w and 7x one after the
   other: both rewrite the same 8 hg types, and hg kits cannot launch before the split anyway (1945 stop 3).
3. **7y** (pv D=4, lp_even, PVX rebuilt), on a tree that carries main 7f435727cde or the listed overlay. It touches
   only pv_v1n and is independent of 1 and 2.
4. 7p and v20: not adopted.

## 6. Risks

| risk | state |
|---|---|
| lane latency | LATCHECK 2404/2404 on 7uh, 7v, 7w, 7p, v20, v21n. 7v: 64 lanes change (+5, +3). 7y will change the pv lanes again (+11 on y). The merged hg plan is unchecked |
| 340-um hop law | 7uh: 4 start hops at 348. 7v: 10 krsp hops 360-374. v21: 2 clock-pin-to-ring distances 349 / 371, reader start 378 on hgi_v8. All under 405. The stale `max_pin_to_band_hop_um` hides the real data hop per ring. 7p: F2 / F4 fail at D=3 |
| reset relay reach | raw hops over `relay_um` 300 exist in 7u and stay (hroot 18 of 28; hgi_v8 all). v21 raises the max to 403 on 4 hg types. No event adds a relay stage |
| clock tap windows | no existing tap moved by any event. hroot limit raised to 1500 sinks; 106 new core taps on hg / hgi. No routed kit on any of these types, so no window is measured |
| GRT congestion, ring region | 28 channels under 8.64 um next to ring cores; 512-768-bit station columns in the same W street; hard-core share up to 51.9 % |
| GRT congestion, pv region | about 1.17 M pad flops unpriced in the cell budget; 91 new station rows on pv_v1n |
| tools | 7uh / 7v / 7w gated on tools18 trees; 7y needs a newer main than c1 |

## 7. Owning lanes

| item | owner |
|---|---|
| 7uh c1 gate and adoption; merged hg compose; 7y compose | KV-102 |
| v21 on 7w as base; recompute `max_pin_to_band_hop_um`; widen the 5.18 / 7.78 um channels where a pin face looks into them; sign-off list of the 16 ring masters | KV-HGSPLIT-1115 |
| re-site krsp S5 (q2, q3) and the rq column against the ring boxes; status of the 37/26 core views | KV-ECTLK-RL |
| 7y: D=4, lp_even sites, PVX rebuild, the 2 F2 legs over the limit | KV-PVGEN |
| die-side route of `cland_tstart_in` to (1576.8, 369.9) | DIE-KV-ROUTE-1 |
| G0 check: station site against hard-core footprints | PLAN-GATE-PRE-1115 |
| pv_join_t RESET_PIN registry record | HCPARAM-ALL |
| c1 tree overlay list for the pvgen files | TOOLS-CONVERGE-1115 |

## 8. Stop list

1. No adoption of 7p (D=3 on F2 / F4). No pv kit from it.
2. No adoption of v20. No adoption of v21 before its strict bind and LATCHECK finish.
3. No merge of 7w with v21 by `kv7merge.py` alone: 9 station sites land inside ring cores.
4. No adoption of 7v or 7w before the ectlk 37/26 core views exist.
5. No hg / hgi launch from 7uh or 7w without the split (1945 stop 3 stays).
6. No further rise of `tap_max_sinks` on hroot without a routed tap window.
7. No use of `max_pin_to_band_hop_um` as evidence for a moved ring until it is recomputed.
8. FABLE-PD-KV-1945 section 5 and FABLE-PD-KV-1450 section 4 stay in force.

## 9. Not checked

- The v21 strict bind result (running at 21:50 PST) and any 7x / 7y gate output (none written yet).
- Which faces of the ring cores carry pins, and so whether the narrow channels are pin channels.
- Per-bit data hops from face pins to the moved ring cores; I measured the forwarded-clock pin only.
- The die-side length of `cland_tstart_in`, and what drives it.
- Sink counts per tap on hroot (1486 is REPORTED), and any tap window: no routed kit exists.
- Sign-off state of the ectlk 37/26 cores and of the 16 ring masters.
- Whether G0 prices the PVX pad flops anywhere; I infer not from the unchanged warning count.
- 7p station rows on pv_v1n (91 new rows) against the pv hard cores.
