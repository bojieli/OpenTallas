# INTENT SHEET: S81 slice S2 street sizing (CPL-S81-SLICE, COORD 04:4x scope)

Plan of record: S81 99f40d35071d. The delta `delta_SLICE-C-S2_99f40d35.json` contains positions and orientations only. It is standalone on 99f and does not depend on SLICE-C v2 or the LP-W window, which are both HELD. The one extra file is `added_taps_SLICE-C-S2.json`: two added clock taps in lepe_nh_mus_LP__t1 move rigidly with the lnland row.

Gate evidence for each changed type:
- composer legality (cgate): 0 new findings;
- station EQ check: 0 new;
- kit tap rule: pass;
- G0: 0 new errors (84 -> 84);
- explorer `--delta --supply` before/after views.

`tools/die_plan` has no separate station_lint tool. G0C and the composer site check cover stations.

The explorer views (scratchpad `coreplace/cpl-s81-slice/SLICE-S2/*_delta.png`) were rendered on the V1 stack: 99f + SLICE-C v2 + LP-W window + tap. The same moves on 99f alone give the same p99 for every type (`evidence_s2/v3_99f.log`). Only lepe_mu_C differs, in its absolute xr position: on 99f alone, xr goes from 388.8 to (457.92, 1019.52).

## Method (hand layout; the search only scores and legalises)

I looked at each flagged type in the explorer (`final/explorer_b`) and read the route_supply hot bin. Every hot spot is in one of four places:
1. **The cap|xr macro street, 17.28 um** (mstreet_H 1.46). The xrt1 W edge carries 2070 pins and faces capc5r. The street is half the 34.56 rule and predates this plan.
2. **The S-edge pin landing of dsfd_coll_lane**, a 1111-pin edge (LP types, core_V 1.06-1.08). The lnland macro sits 26 um below that edge, so the lane's S landing and lnland's N landing share one strip.
3. **The S/N face landing under cap/xr** (ring_H 1.5-2.9). The leafup/leafdn windows (597/668 b each) land in the 34.56-um street under capc5r, which blocks M1-M7.
4. **The E-face landing** (ring_V 1.47-1.74). The xring_i0/o0 windows (1104 b) land in the 35-um street E of the eng_finish row.

Hand rule: move whole functional groups rigidly on the 8.64 lattice, to widen the street the bits cross. The groups are:
- xr alone;
- the finish row g_cp0..3 + u_f, which keeps the chain order and the 190-um pitch;
- the lane row ln0..3;
- the lnland row lnl0..3.

A move is kept only if it passes cgate, EQ, the intent link rule and the tap rule, and lowers p99.

## Dataflow (unchanged by the delta)

```
face leafup_i*  -> xr (xrt1 ring)  -> cap (capc5r) -> leafdn_o* face
face xring_i*   -> finish row g_cp0 -> g_cp1 -> u_f -> g_cp2 -> g_cp3 -> xring_o*
LP: face coll_i* -> ln* (coll_lane) -> lnl* (lnland) <-> lep banks, lnl*.rs_k <- lpc_i0
```

<svg xmlns="http://www.w3.org/2000/svg" width="640" height="250" font-family="sans-serif" font-size="11">
<rect x="10" y="10" width="300" height="230" fill="none" stroke="#888"/><text x="14" y="24">slice C (c1x t6/t10, lepe_mu_C)</text>
<rect x="20" y="40" width="110" height="110" fill="#b8a060"/><text x="40" y="95">capc5r</text>
<rect x="150" y="40" width="70" height="55" fill="#6aa0b0"/><text x="165" y="70">xrt1</text>
<line x1="132" y1="65" x2="148" y2="65" stroke="red" stroke-width="3"/><text x="118" y="112" fill="red">17.28 -&gt; 0 / 34.56 / 86</text>
<path d="M200 12 L185 38" stroke="#4af" marker-end="url(#a)"/><path d="M150 70 L132 70" stroke="#4af" marker-end="url(#a)"/>
<rect x="60" y="180" width="230" height="40" fill="#3a6"/><text x="70" y="204">finish row (t6: -17.28 x)</text>
<rect x="330" y="10" width="300" height="230" fill="none" stroke="#888"/><text x="334" y="24">LP (lepw/lepe mu / mus)</text>
<rect x="345" y="40" width="60" height="90" fill="#a55"/><rect x="415" y="40" width="60" height="90" fill="#a55"/><text x="350" y="90">ln0</text><text x="420" y="90">ln1</text>
<rect x="360" y="150" width="30" height="30" fill="#c96"/><rect x="430" y="150" width="30" height="30" fill="#c96"/><text x="352" y="196">lnl (row)</text>
<line x1="345" y1="140" x2="475" y2="140" stroke="red" stroke-width="3"/><text x="480" y="144" fill="red">lane S landing: gap 26 -&gt; 43 um</text>
<path d="M375 12 L375 38" stroke="#4af" marker-end="url(#a)"/><path d="M375 132 L375 148" stroke="#4af" marker-end="url(#a)"/>
<defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#4af"/></marker></defs>
</svg>

## Per type (route_supply p99; 99f -> S2)

| type | move | p99 | worst after | bit-mm | verdict |
|---|---|---|---|---|---|
| c1x_C__t6 | xr -17.28 x (abuts cap, street 17.28 -> 0); finish row -17.28 x | 1.456 -> 0.825 | face_H | 7967 -> 7949 | ADOPT (0.8-1.0 band) |
| c1x_C__t10 | xr +17.28 x (street 17.28 -> 34.56), station regs as planned | 1.457 -> 0.920 | mstreet_H | 7453 -> 7501 | ADOPT (0.8-1.0 band) |
| lepe_mu_C__t1 | xr +69.12 x (street -> 86 um), station regs as planned | 1.457 -> 0.792 | ring_H | 7853 -> 8042 | ADOPT |
| lepw_mu_LP__t2 | lane row +17.28 y; lnland row +34.56 x | 1.057 -> 0.737 | street_V | 3777 -> 3840 | ADOPT |
| lepe_mu_LP__t2 | same as lepw_mu_LP | 1.057 -> 0.738 | street_V | 3759 -> 3826 | ADOPT |
| lepw_mus_LP__t2 | lane row -8.64 y; lnland row +17.28 y | 0.928 -> 0.750 | core_V | 4195 -> 4211 | ADOPT |
| lepe_nh_mus_LP__t1 | lane row -8.64 y; lnland row +17.28 y; clk_t27/t28 move rigidly | 1.075 -> 0.755 | ring_H | 2022 -> 2024 | ADOPT |

Reasons for the 0.8-1.0 band:
- **t6, 0.825 face_H:** the residual is the N-face leafup/leafdn landing between cap and the N edge. That landing is the window fan-in itself. The cap|xr street is gone, because the two macros now abut.
- **t10, 0.920 mstreet_H:** the street is now exactly the 34.56 rule, and it carries the xrt1 W2070 landing. The only way to widen it further is to move xr +34.56 or more, but then leafup_i3 regs land under the slice-bank u_mem and the move fails cgate.

Station handling: for t10 and lepe_mu_C the plan station regs stay where they are, because re-siting them would put them under u_mem. For the LP types, station ends on a moved core translate rigidly with that core, and the regs stay in place. Station and reg counts are unchanged, and G0C reports 0 new hops above 405 um.

## Over-reach links I accept

- **C types:** the over-reach set equals the plan's: `cap.cw_n_a -> leafdn_o0/o1` at about 416 um, which predates the 99f plan.
- **LP types:** G0C R3-INTERNAL bundles that were already longer than 405 um in 99f, with lengths changed by the delta. None is newly past reach, and no station hop is new.
  - `ln*.rx -> lnl*.n_rxv`: 551 -> 603 (mu) and 547 -> 572 (mus).
  - `lnl*.n_flt -> ln*.flt`: 439 -> 422 (mu) and 435 -> 461 (mus).
  - `lnl*.n_st`: 739 -> 773.
  - `lnl*.rs_k -> lpc_i0`: 1124 -> 1089.
  - All of these stay at 1.1x or less of their plan length. They are pin-side relays the kit already carries as R3 bundles.

## REDESIGN / ARCH (S2 above 1.0; the launch is held for these types)

All of these types have a worst cut of 0.40-0.48, so the min-cut bound fits. The overload is a local landing ring of buses of 512 b or more. Placement cannot fix it under EQ:
- every rigid xr, finish-row and eg-block shift was tried;
- for c1x_t1, a full hand sweep of the cap position over every lattice spot found 0 legal candidates without extra stations;
- with +2/+1 stages on leafdn_o2/leafup_i1, the floor is 1.216.

**Class A, S/N-face ring_H.** capc5r and xrt1 sit on the leafup/leafdn windows.

| type | p99 (99f) | best legal rigid move |
|---|---|---|
| c1x t1 | 2.923 | 2.923 (none) |
| c1x t5 | 2.087 | 1.858 (xr +17.28 y) |
| c1x t7 | 2.373 | 1.901 |
| c1x t8 | 3.03 (v2 2.69) | 2.294 |
| c1x t9 | 1.924 | 1.924 |
| lepw_mu_C | 2.373 | none legal (station EQ) |
| kv512_C | 1.457 | 1.156 (xr +8.64 x; residual is the xr landing ring) |

Proposal (die-level, S81 window plan):
- (1) Regroup the S/N-face windows so the leafdn_o* windows (597 b) land W of capc5r and the leafup_i* windows (668 b) land beside xrt1, never under cap.
- (2) Add one pin cycle on leafdn_o1..o4 and leafup_i1..i2. That is the owner's cheap lever, and it lets cap leave the face landing. The hand sweep shows this is legal, with 1.216 for c1x_t1.
- (3) Change the xrt1 landing form: split the W2070/E2156 pin edges, or give xrt1 a taller and narrower outline so pin density per edge-um halves. That clears the residual xr ring above 1.0.

**Class B, E-face ring_V.** The xring_i0/o0 windows (1104 b) land in the 35-um E street beside eng_finish g_cp3.

| type | p99 |
|---|---|
| c1x t3 | 1.744 |
| c1x t4 | 1.473 |
| lepw_mus_C | 1.744 |
| lepe_nh_mus_C | 1.457 (xr +8.64 gives 1.439, then ring_V) |

The finish row cannot shift W: every shift from -8.64 to -69.12 puts leafdn_o0 station regs under the slice-bank u_mem or under g_cp0.

Proposal:
- move the E xring windows to the y span above the finish row (y > 720), or
- add one pin cycle on xring_i0/o0 so a station can sit N of the row, or
- shorten the finish-row pitch by 34.56. That is a plan-level row change: 190 -> 172.8 um pitch with the chain order kept.
