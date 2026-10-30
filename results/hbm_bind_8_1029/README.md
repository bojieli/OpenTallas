# HBM-BIND-8 (2026-10-29): the 103 UNPLANNED pairs of bind d4 - re-home vs hop chain vs re-plan

Sub-lane of DIE-HBM-21 (COORD 07:16 ruling (b): far pairs -> 12.13 locality re-home; failed -> windows/stations).
Inputs (read-only): plan d16k_q2L sha 0b7b966cbaf2 (intel1 die-hbm-19/plan/d16k_q2L), strict bind d4
(die-hbm-19/bind/d4: manifest, map, elab out/asbuilt.json). Runs: intel1:/srv/opentallas-scratch2/claude/hbm-bind-8-1029
(c0 census, plan/q2L_h8 + q2L_h8b, b1/b2 rebinds, chk/). No shared tool changed; no coll cut touched (HBM-BIND-7).

## Verdict (one line)
Locality re-home by the bind map cannot clear the far pairs: the bits cross between PLAN HARD CORES (or whole glue
cells that fan out to two far rows). The re-home estimate finds 4 bit-connections. Hop chains clear 11 of 103 pairs
(1,791 b). The other 92 pairs (82,285 b) need a die re-plan event (DIE-HBM-21): place the SFU, IDX and SU-half partitions
next to each other, and widen the full hub faces.

## 1. Census of what crosses (CHECKED: c0/census.json, census_d4_summary.json)
census.py re-runs Binder map_cells/analyse/build_buses of main bind.py on the d4 inputs. It works from a private copy
of the module text with the per-bit UNPLANNED list un-capped. It reproduces d4 exactly: 103 pairs / 84,076 b
(far 90 + failed 13).

| group (classify.py) | pairs | bits | driver bits glue/leaf | gap um | what crosses |
|---|---|---|---|---|---|
| SFU split3 ctl/lanes | 32 | 29,068 | 0 / 29,068 | 2,920-13,262 | sfucore __cut_ctl + u_memory (b113, die corner) <-> __cut_lane0-3 (b110), 4-7 (b111), 9-12 (b112), 14-15 (hub); ctl <-> sfu_N1/2/3 (su11/su20/su31); sfup/sfus (hub) -> ctl |
| failed (b): SU halves + hub faces | 13 | 27,787 | 798 / 26,989 | - | su_X3 lane cuts su30 <-> u_slice su31 (b100+b110 between); pgp/sucore/vmb (hub) -> su00/su20 lane cuts; su tap -> cxij/vmb; vmb_S* (hub) -> hb_idx__ctl (root) |
| IDX scorer rows | 28 | 17,643 | 15,702 / 1,941 | 1,616-11,940 | leaf chain r0c1 (b100) -> r0c2 (b101); quarter key/query input $dff (4,396 b, ONE cell) feeds row r0 (b100) AND row r1 (b102, 8.9 mm); r0c3 (b101) -> r0 tail u_t (b103, 11.2 mm); tails -> hb_idx__xq (root); col_idx (root) -> fronts; plan places core r1c0_k0h0 in q_b101 (its 54 siblings in b102) -> b102<->b101 1,181 b |
| hub <-> hub over root | 2 | 5,505 | 0 / 5,505 | 1,685 | hb_vms_SE <-> hb_vms_SW 2,170 b/dir, hcollb 560 b/dir |
| EP endpoints | 6 | 3,741 | 0 / 3,741 | 2,834-4,562 | hb_coll/epcal (hub) <-> ep_S0 (spb0); b2_ep1_root (root) <-> ep_S1 (vsN0) |
| SM front -> svg | 8 | 296 | 0 / 296 | 1,555-1,572 | sm u_front -> svg (hub), 37 b each |
| misc | 14 | 36 | 8 / 28 | 2,074-9,884 | scorer reset relay u_rr, hcb glue -> hc u_cen, fl chain, obs/xc, cp_svg -> router_ids |

## 2. Classification (estimate before build, 12.14b)
- (i) glue homed in the wrong partition: rehome_est.py scores every glue cell on an UNPLANNED crossing (1,279 cells;
  254 leaf cells cannot move by a map). It tries a whole-cell move to each partition the cell connects to and counts
  data-bit connections that stay far (no shared edge and gap > 1,200 um). Best moves: 4 cells, 4 bit-connections
  (scorer b101->b103 and hcb b011->b010, 1 each per half). The large glue groups do not move:
  * The scorer leaf pin regs sit with their own leaf's u_hc cores.
  * The quarter input $dff is one cell that drives both rows. Splitting it is an FF fracture or a duplicate, which a map
    may not do.
  Result: no bind-map change was built (not worth a rebind).
- (ii) true far links (the plan places partner cores far apart): SFU, IDX rows, hub<->hub, EP, SM->svg. Total 90 pairs.
  12.13c form = hop chains through fixed-latency crossings, built below.
- (iii) duplicated-family artefacts (HBM-036, report only, no decision): sfup/sfus (hub copies -> SFU ctl, in the SFU
  group) and pgp (hub -> su00/su20, failed group) carry far bits. Both plan copies sit in the hub, so the choice of
  copy does not change the far distance.
- (b) failed 13: windows on full faces (su30|b100, b010|su00, su21|hub, hub|root) and macro-blocked station chains.

## 3. Build: hop-chain plan candidates (lane_add of main, --near-um 20000 --max-hops 8, first id L200)
| candidate | sha | lanes built | G0 | G0C | strict bind (CHECKED) |
|---|---|---|---|---|---|
| d16k_q2L (base, d4) | 0b7b966cbaf2 | - | PASS | 10 inherited | 104 = 103 UNPLANNED / 84,076 b + EMIT HBM-035 |
| q2L_h8 (all 103 rows) | 72a9b5d566a6 | 13 / 5,115 b | FAIL 1 NEW: NE_b003 cut 0.66 > 0.6 (L200m b113->b111 1,662 b) | 11 (1 new, same) | 91 = 90 / 78,961 b + EMIT |
| **q2L_h8b** (h8 minus SFU b113->b111) | 6c794bcb3774 | 11 / 1,791 b | PASS 0 | 10 = inherited, 0 new | **93 = 92 / 82,285 b + EMIT HBM-035** |

The h8 run's lane_add failures for the 90 pairs it could not build:
- 41 pairs / 31,027 b: no macro-free station chain (6-46 stations).
- 25 / 34,981 b: no free window (8 x su21|hub, 6 x su01|hub, 2 each su30|b100, b010|su00, su21|su20, b111|b003,
  b113|b012, 1 hub|root).
- 20 / 9,507 b: a shared type on the chain (sm*, spb1; hub<->hub routes over sm3).
- 4 / 3,446 b: cycle mismatch (su00->hub 15 vs existing 8; the split of su20->b113).

h8b lanes (plan arithmetic, cycles incl. landings):
- root<->vsN0 EP_S1: 19 + 19 cyc, 17 + 17 stations.
- root->NW_b000 col_idx: 25 cyc (23 st). The NE mirror failed (macro chain).
- root->N*_b100 col_idx: 12 cyc each.
- b000->b002 / b011 reset-relay bit: 11 / 9 cyc.
- su00->su11 fl bit: 20 cyc.
- Total 145 new stations.

Cycle cost: col_idx is a static config collar (quasi-static), and u_rr / fl are reset and flag bits. Bind d4 gave
these bits direct 2-cycle pairs, so the static schedule is not affected (UNCHECKED). EP_S1 +17 cyc each way on the
root <-> vsN0 endpoint is the one lane that may touch the token: 17 cyc x 2 at 1.2 GHz = 28 ns per round trip. If it is on
the per-layer path of ~60 layers, that is ~1.7 us/token, about 0.3 % at ~1.8k tok/s (worst case). UNCHECKED, not
TOK-priced.

## 4. What clears the rest (die owner, re-plan event 12.13e; not a bind-map change)
1. SFU, 29 kb: put the 16 sfucore lane cores and ctl/memory in abutting partitions. Today they sit in 4 die corners
   (b113 NW corner, b110 S mid, b111 S west, b112 N east); sfu_N1-3 sit in su11/su20/su31.
2. IDX, 17.6 kb: make the scorer partitions b100-b103 one contiguous strip. Today r0 is at x 9.7-13.4 mm and r1 + tail
   at x 0-1.4 mm. Move core u_hb_idx__s_Q_r1c0_k0h0 from q_b101 to the b102 type (1,181 b per half).
3. SU halves su30/su31 + hub faces, 27.8 kb: make su30 and su31 abut (b100/b110 sit between them). Re-budget the
   su21|hub, su01|hub and hub|root windows.
4. hub<->hub 5.5 kb: needs a root feedthrough slot (lane_add never routes through root).
5. EP spb0, 1.2 kb per half, and SM->svg, 0.3 kb: a ft slot on the shared types spb1 / sm* (type-shared rule).
After that event, lane_add (near 1,200) builds the then-adjacent pairs.

Scripts: census.py, classify.py, rehome_est.py, run_bind.sh, run_chk.sh; outputs census_d4_summary.json,
classify_c0.txt, rehome_est_c0.*, lane_add_h8{,b}_summary.json, bind_b{1,2}_errors.json, g0*_h8{,b}.txt, rows103.json.
