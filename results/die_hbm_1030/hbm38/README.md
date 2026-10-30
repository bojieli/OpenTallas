# DIE-HBM-38 (HBM die owner, 2026-10-30 12:26-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-38.
Tools = branch base 9ff378bb6dc (= main 16f2590f75f tools, same as the d35b gates). G2 probes use g2.py from
claude/flow-9-g2cut-1030@7518687ff52 (run-local copy g2tools/, the COORD-accepted '<inst>.<cut>' fix; not committed here).

## (P) COORD priority: station-hop defect in the plan of record (d35a/d35b q_b010) -- FIXED in d38r
- Reproduced on PLANNED targets (plan_hops.py = proto_geometry.hop_stats on probe.tcl place_inst targets, CHECKED):
  d35a/d35b q_b010 planned over-reach 983 bits (L28x2 512.2, L204mx1 414.4, L36x2 407.6, L168mx1 405.1 um); actual
  post-DPL 1,014 bits. So the defect is plan geometry, not placement. d35b = d35a for q_b010 (only collar pins differ).
- Root cause L28x2 (E->N, 1,615+1 b): worst bit in-pin (829,2912) -> out-pin (559,4320) = 1,678 um Manhattan; station0 is
  registered beside its input pin (g2/ft_bit_sites convention), so 4 stations = 4 hops -> >= 420 um: cannot close at
  405 with 4 stations whatever the sites. -> L28x2 4 -> 5 stations = lane L28 and L28m 28 -> 29 cycles (+1 each).
- d38r = d35b + re-station (mk_d38.py r; identical edits in q_b010 and q_b010__physical_v1; no core/pin/outline/
  neighbour change): L28x2 5 stations, 4 packed clusters re-solved (min max per-bit hop, centre hops <= 360 for the G0C
  0.9x405 reach rule; legal stage-1 packing translated on the 0.054 x 0.27 grid); L36x2 clusters re-solved (3 stations);
  L168mx1 station0 cloud (712.8,1982.88)->(740.16,1952.64); L204mx1 station3 (17.28,1520.64)->(17.28,1485.0).
  Planned max hop 396.9 um, over-reach 0 bits (CHECKED); centre hops L28x2 245/356/356/355 um.
  die_plan.json sha 09038a089e89 (plan_of_record/d38r gz + SHA256SUMS; other files = d35b).
- G0 6 err/918 warn, G0C 14 err/128 pending/910 warn = d35b finding set with 0 new / 0 gone apart from 3 findings
  whose text carries the changed numbers (L28x2 geometry WARN "> 5 station(s)" was "> 4"; pre-existing L204m hop-4 ERROR
  900 um was 936 um) (CHECKED, g0/setdiff.txt). First version (v1) had 2 new G0C L28/L28m reach ERRORs (centre hop 373 >
  364) -> fixed by the centre-hop constraint.
- Die clock: no clock tap/entry/core moved (diff = ft_slots + notes + latency L28/L28m only, CHECKED) -> die clock rerun
  not needed for d38r.
- Tok/s: +1 cycle on L28/L28m (NW_hub->NW_sm0 data) UNCHECKED; earlier single-lane +1..+3 cycles priced -0.0x %
  (DIE-HBM-29T) -> far below 5 % -> no OWNER item; @TOK-12 to price.
- Probe q0f_d38r (0 congestion iterations): initial overflow 706,479 vs base 889,963 (-21 %, CHECKED). Actual post-DPL
  hop check = q0f_d38r/grt.json after pin_access (LIVE at park).

## (a) one-core move (d38a = d38r + core) -- channel works for L28x2, but moves the jam to L36x2
- u_hb_idx__s_Q2_r0c2_k0h1 (587.52,3291.84) -> (483.84,3291.84): opens core-free N-S channel x 702.4-829.4 from y 2903
  to the N face; L28x2 clusters solved inside it (5 stations, max hop 382.7); L36x2, whose stage-1 cluster sat where the
  core lands, needs 4 stations (lane L36/L36m 14 -> 15, +1) [CHECKED planned hops 387.9, 0 over-reach].
  G0/G0C identical to d38r (0 new). sha 5f84154ebe05. Render viewed: q_b010_d38.png.
- Initial overflow q0f_d38a 588,726 (-34 % vs base, -17 % vs d38r). Sampled congestion report (first 20k violations):
  d38r = L28x2 vertical over core 587-806 (x 700-800, y 3200-3600) 42k + L168mx1 16k + L36x2 14k;
  d38a = L28x2 only 6k, but L36x2 50k HORIZONTAL at y 3290-3345 x 480-700: the moved core blocks the only M2/M4 band the
  1,330-b E->W lane had (cores obstruct M1-M5; x 250-469 and x 483-702 have no common free H band) [CHECKED bins].
  -> (a) is better on the trend but not clean; it needs L36x2 re-homed (e.g. through the 3108-3292 band + a 2nd cut).

## (b) V-A at 8/um across the W column + remainder through an N-S band -- REJECTED by the probe
- vb8 = probe + 5,027 E->W through bits (W face 5.43 -> 8.0/um in y 950-2908, max 200-um bin 8.4/um) + 6,839 remainder
  bits E->N (va_turn, N face x 10-826 -> 10.4/um). Initial overflow: d38r+vb8 2,628,784 (M3 1.34M, M5 0.73M);
  d38a+vb8 2,369,029 vs va12 (all 11,866 E->W at 12/um) 1,352,609 [CHECKED]. The N-S turn remainder through q_b010's
  staggered N core field is much worse than 12/um E->W: no N-S band in q_b010 can take ~6.8k b.

## Not done
- NW hub hard transport cuts: the LOAD relay network is not yet in the plan/bind (Codex estimate only), so there is
  nothing to cut; estimate stays DIE-HBM-37's (8 cuts/hub ~20.7k FF, north band 6.87 mm2 free) [UNCHECKED].
- RING pin-only event d35c (COORD 12:5x optional): skipped (station-hop priority; HBM-CORES-KITS-28 rebuilds RING on d35b pins).
- 30-iteration probes: none launched by me. DIE-HBM-36's dhbm36-g2-* still LIVE (stock d35a = pre-fix baseline).
