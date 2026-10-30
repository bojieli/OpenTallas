# DIE-HBM-36 (HBM die owner, 2026-10-30 10:50-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Plan of record d35a (intel1
/srv/opentallas-scratch2/claude/die-hbm-35/plan/d35a). Tools = main 16f2590f75f (sparse wt intel1 wt/die-hbm-36).
Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-36. Scripts in tools/ (die-local, no shared tool change).

## Goal (2) V-B (S/N row locality reorder): NOT BUILDABLE as specified (CHECKED plan arithmetic)
The S row is cut by the fixed N-S street column (NE_spu1 x 20813.76-22282.56, aligned with spb0-2 / spu0 / spt0-2):
west segment b101,b100,b110,su31,su30 = 5771.52 um (full), east segment su21,su20,b111,b103,b102 = 6117.12 um.
DIE-HBM-35's V-B order [b101,b100,b102,b103,b110,b111,su31,su30,spu1,su21,su20] puts su30 at x 20969-23034 (over the
street column), spu1 at 23034-24503 (its 7,722 b of N-S slots L2/L33/L40/L48/L49/L53/L83/L87 lose the street) and su21
(4,734 b planned to the hub incl. L2 2,999 b) at 24503-26395, 1,244 um east of the hub E edge (23258.88) = the
VB2-REJECTED (10-29) mode. No equal-width swap exists across the street (b101+b100 1460.16 vs b103+b102 1416.96; all
singles differ). => any locality move needs outline changes or a street move (bigger event). Not built.

## Goal (1) V-A (strip face budget 12/um, no block moves)
Face arithmetic (strip_faces.py, check.check_abutment pins on d35a, CHECKED):

| edge (both halves equal) | pins | /um | in occupied windows | headroom @12/um |
|---|---|---|---|---|
| hub|b000 | 15,625 | 3.62 | 5.57 | 36.2k |
| b000|b010 | 21,611 | 5.00 | 5.59 | 30.2k |
| b010|b001 | 18,152 | 4.20 | 5.54 | 33.7k |
| b001|b011 | 15,822 | 3.66 | 5.52 | 36.0k |
| b011|b002 .. b003|b013 | 13.5k .. 9.8k | 3.1-2.3 | 5.4-5.5 | 38-42k |

Face pins are NOT the binding limit at 12/um (worst face 33.5k of 51.8k with the ~11.8k/half demand). But lane_add
only allocates in FREE gaps (b000|b010 has 451 um free -> 5.4k pins at 12/um), so V-A also needs every existing window
on those faces re-windowed at 12/um (DIE-HBM-33 repack_edge.py form, pins move, strips re-kit).

Second limit = N-S turns inside the strips (strip_turn.py, the check_cuts partition-segment model, CHECKED inputs):
NE unplanned 24,873 b (HH bind): 12,630 b cross the column to the N row east (su00/b113 network), 6,828 b to the S row
east (b102/b103/b111/su20), 3,774 b S-row-east <-> N-row-east (full strip height). Per-strip N-S spare at cut 0.6:
b000 1,996 / b010 4,219 / b001 2,662 / b011 650 / b002 1,534 / b012 2,240 / b003 1,089 / b013 990 = 15.4k per half
with today's bands; 45.9k if each strip's whole core-free width were an NS die_ft_band (share 1.0). Demand per cut
~ (12.6k+6.8k)/2 + 3.8k = 13.5k if turn entries spread evenly over all 8 strips (UNCHECKED spread model) -> V-A fits
only with new NS die_ft_bands in most strips (b011/b003/b013 are near full today) and a per-strip turn allocation.

G2 probe on q_b010 (g2.py part, docker, adjust 0.5, M2-M7). Probe-local deviation: g2.py probe_blockages blocks the
whole u_hcb_Q7 content outline (276.48,1218.24 51.84x915.84, soft remainder of 3 split cores) because the cores are named
'u_hcb_Q7.<cut>' and the matcher only accepts '<inst>_*' -> 1,929 FIRM ft bit sites inside a placement blockage,
DPL-0004/DPL-0033 on the STOCK probe (CHECKED, both base and va12). That one outline is removed from probe.tcl
(probe.tcl.stock kept); the 3 cores stay blocked. FLOW item: g2.py should also match '<inst>.'.
Variants: base = stock d35a probe (41,379 pins, 79,833 FF); va12 = base + 11,866 synthetic 3-station through bits E->W
in the core-free EW corridor y 950-2908 (faces up to 11.6-12.0/um per 200-um bin); va12t = va12 + 3,000 E->N turn bits
(E y 2950-4250, N x 300-826, stations <= 390 um).
Initial GRT (0 congestion iterations, before rip-up; NOT a verdict, CHECKED from grt.log):

| probe | usage | overflow total | M4 | M6 | M3 | M5 |
|---|---|---|---|---|---|---|
| base | 13.4 % | 889,963 | 47,412 | 42,032 | 413,693 | 256,834 |
| va12 | 20.4 % | 1,352,609 | 185,628 | 206,651 | 427,446 | 270,188 |
| va12t | 22.4 % | 1,534,740 | 190,433 | 207,830 | 495,853 | 360,530 |

The stock base already overflows before rip-up (packed FIRM bit-site clusters); the 30-iteration runs (g2/base, g2/va12,
g2/va12t, ~15 min per extra iteration, LIVE at park) decide. Pass = va12 (and va12t) final overflow 0 with no pin-access
failures AND base also 0; if base does not reach 0 the probe proves nothing about 12/um.

## Goal (3) LOAD relay network vs the 400k cap
Codex count (codex/hbm-1030 c097e6dee3e results/hbm_die_codex_1030/load_network, arithmetic re-added here: 16,506 +
66,080 + 33,158 + 214,965 = 330,709 FF; NW 165,362 / NE 165,347). NW hub soft count 375,862 + 165,362 = 541,224 > 400k.
Neither V-A nor V-B moves the northern hub frames where the LOAD lots/banks sit, so the adopted variant places the relay
network as hard transport cuts inside the hub frames (own P&R runs, each <= 400k; >= 1 per hub, ~4 by function:
command/fill/leaf-quartet/local delivery), keeping the hub soft count at 375,862 - or shared trunks first (Codex: the
independent-path count is a failed capacity design, not a lower bound). UNCHECKED; nothing emitted into the plan.
