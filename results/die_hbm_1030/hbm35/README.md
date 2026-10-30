# DIE-HBM-35 (HBM die owner, 2026-10-30 10:25-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Base plan d32q (intel1 /srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q,
die_plan.json sha256 ce16f2f3f15c). Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-35. Gates are run with MAIN tools
(16f2590f75f, contains 898f22b0f exact abutment), sparse worktree intel1 wt/die-hbm-35.

## (2) SU lane_exp0_id outline option (a) -> plan event d35a (CHECKED)
mk_d35a.py: d32q + ot_hbm_su_static_pgslice_lg__lane_exp0_id 440.64x207.36 (aspect 2.125, AUTO-GEOM FAIL) -> 414.72x207.36
(aspect 2.00) at the SAME origin in q_su00 / q_su10 (MX) and the two __physical_v1 twins (4 hard-core entries). The core only
shrinks, so no neighbour overlaps and no neighbour moves. New pins file
`cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__414.72x207.36__d35a.json` (2068 pins, 1510 moved):
E face 840 M4 pins x 440.544 -> 414.624; W unchanged; the 20-pin clock/reset cluster (clk_bank, clk_insert[4], clk_bank_macro[6],
clk_lane[8], rst_lane_n) moved from the NW corner (x 2.3-31.4) to the N-face centre x 192.84-221.88, offsets and sizes kept; the
other 275 N pins keep their order at 1.378-um mean pitch around it; S pins keep their order scaled into the face; rst_n (partition
reset, S face) at the S centre x 208.44. All x on the 0.024/0.048 track grid; min pitch >= 0.24 on N/S. Centre clock entry
(12.8a, 4.32 lattice) (220.32,103.68) -> (207.36,103.68), island [203.04,99.36,211.68,108.0] (between the two SRAM rows);
partition clock taps and both die tap tables x -12.96. The six 94.824x41.064 SRAMs (right edge 371.30) stay inside.
Render viewed: lane_exp0_id_pins.png (old vs new).
G0 FAIL 6 err / 918 warn and G0C FAIL 14 err / 128 pending-view / 910 warn: IDENTICAL finding set to d32q on the same main tools
(0 new, 0 gone; g0_d35a/*diff*). The 14 G0C errors are inherited (8 hub core_faces + 6 hops L204/L206/L6b and mirrors); note
main tools report 6 G0 errors on d32q where the DIE-HBM-32 tools (9a8d05473a3) reported G0 PASS (tool delta, not this event).
Not changed: plan.clock.mesh.core_islands key `..._lane_exp0` (stale non-_id name; check.py only applies it to that module name;
no kit generator reads it). The r2r 580/405 kit item stays with the kit lane (re-measure after the pin move).

## (3) plan-of-record data
physical/die_plan/hbm/plan_of_record/d35a/: die_plan.json.gz, every referenced cores/*.json (gz, incl. the old d31s lane_exp0_id
table d32q uses), every non-report side JSON (gz), SHA256SUMS of the raw files. d32q/: die_plan.json.gz + sha (d35a = d32q +
mk_d35a.py). Unpack: `gunzip -k` in place; raw sha256 must match SHA256SUMS.

## (1) bind-gap floorplan event: ESTIMATE (est/; no build yet)
Input: strict bind of Codex HH candidate hh_seams2 (= d32q + L700/L701 HH lanes; intel1 codex-hbm-1030/hh_seam_bind, main-era
bind.py): 79 UNPLANNED pairs / 51,807 b (d32q itself 81 / 57,312; HH closes NE_hub<->NW_hub 5,505 b). NE and NW are mirror
images, so ~25.9 kb per half. est_gaps.py (CHECKED arithmetic on plan geometry, lane_add face model at 6 pins/um):

| group (per half) | bits | distance | est. cycles @405 um |
|---|---|---|---|
| b100 -> b102 (V-E2, S row west end -> SE corner) | 2,777 | 11.9 mm | 47 via sm3/spb/sm2 |
| b113 network (hub, b110/b111/b112, su11/su20/su31) | ~13,960 | 6.8-16.6 mm | 19-46 |
| hub <-> su00 / su20 (beyond planned 1350/517) | 5,738 | 9.0-9.3 mm | 25 |
| hub <-> spb0, b111, b002->root, sm*->hub, small | ~2,900 | 7-12 mm | 18-33 |
| NW_hub -> root (NW only, face 64.7 um free) | 2,065 | adjacent | - |

Root cause (CHECKED): every large gap crosses the b0xx strip column (x 23259-27752, 8 strips + io, 4.5 mm). Hub-side <-> east
traffic across that column = 57,845 b per half (planned + unplanned) vs 2,706 free pins on b000|b010 at 6/um (est_gaps edge
overflow: NE_b000|b010 demand 11,841 vs 2,706; b001|b010 11,866 vs 6,264; b003|b113 6,737 vs 3,305). Lane adds cannot close it
(DIE-HBM-33 ve2d-j confirm).

Candidate structural events (cost model UNCHECKED: bits x Manhattan between centres, as-built demand):
- Full local-search row reorder (est_rows.py, S and N rows): unplanned bit-um -20%, column 57.8k -> 41.0k; moves all 18 row
  blocks. REJECTED (large disruption, small gain).
- V-B LOCALITY (12.13): S row [b101,b100,b102,b103,b110,b111,su31,su30,spu1,su21,su20] + N row b113 next to b112 (under the hub
  N face): column 57.8k -> 30.5k (-47%), unplanned bit-um -18%, b100->b102 becomes adjacent-pair (2.8 kb), hub->b113 abuts the
  hub. Moves 7 blocks per half; all their lanes replanned. su20 ends farther from the hub (its 5.7 kb get longer).
- V-A FACE BUDGET (no block moves): b0xx strip types E/W faces at 12 pins/um via the existing per-type face_pins_per_um +
  face_budget_g2 G2 probe (KV ruling 10-25 (a), hard cap 16) + repack: 4320 um x 12 = 51.8k pins per strip face vs ~43k
  demand (UNCHECKED: existing occupancy at 12/um not measured); needs a macro-free ft band through every strip (DIE-HBM-33 saw
  SU/SFU macros covering bands) and the G2 probe proof per strip type. Path latencies stay 19-47 cycles (TOK to price).
- NW hub|root: 2,065 b more over a face with 64.7 um free: re-route L156 (2,740 b idx return) via NW_b112 (b112|root 1542 um
  free, hub|b112 1094 um free) - the hh1 detour whose station chain DIE-HBM-33 found blocked by root macros; Codex 04:07 proved a
  macro-free 362.88-um-max-hop root detour for 5,505 b, so the same solver applies (UNCHECKED here).
- Hub NW split: NOT needed on the cell cap - corrected NW soft count 375,862 (Codex, hard children excluded; old 726,958 counted
  5 hard children) < 400k. The LOAD network (literal 330,709 relay FF, 165k per hub) would push NW over the cap; option: host
  the LOAD relay trunks in the empty street partitions spu0/spu1/spt*/spb* (cells 1000 each, own P&R runs) - UNCHECKED.
Recommended build order (successor): V-A first (no block moves; one G2 probe on q_b010 decides it), V-B in parallel as the
locality fallback; adopt the first that passes G0C + strict bind 0 + die GRT0 incl clock. Both need the row-1 source
(codex/hbm-bind-2249 0ee0ed380) decision for the b100->b102 feed.
