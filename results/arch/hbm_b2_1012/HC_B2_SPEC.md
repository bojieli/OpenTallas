# HC unit on the B2 quarter map: central control / Sinkhorn shell boundary and cut analysis

**Status: v0.1 (2026-10-13), CANDIDATE, nothing here is qualified.** Architecture step before RTL (owner rule: cut
analysis before RTL). No RTL was changed. No price was changed: prices are immutable inputs, and every cycle effect
below is a count to be measured against them.

Inputs:
- `results/arch/hbm_b2_1012/SPEC.md` v0.8 (floorplan, HC x lanes v0.7, rules R1 and F4, cut re-check 6a);
- `results/arch/hbm_b2_1012/cuts_v07.py` (die network, segment counting and track-capacity model, reused unchanged);
- `results/rtl/ref_tile/hc_tile_xl/b2_functional_map.json` (source 550082537);
- RTL at worktree HEAD 4dadba80b: `rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv` (the unit and `ot_hgi_hc_tile`,
  same file), `ot_hgi_hc_quarter.sv`, `rtl/hdc/v41x/ot_hdc_v41x_hcp.sv`, `rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv`.

Arithmetic: `results/arch/hbm_b2_1012/hc_central_cuts.py` → `hc_central_cuts.json`. Every number in sections 2 to 4
is quoted from that record.

Marking used below: **RTL** = read from the source (module, signal, line); **EST** = an estimate of mine;
**open** = the RTL does not answer.

## 0. Summary

- The shell is everything in `ot_hgi_hc_unit` (SYS 1, QPAIR 1) outside the four `ot_hgi_hc_quarter` instances: the
  record adapter, the sequencer, the HCP control and reduction tree (`ot_hdc_v41x_hcp`, SYS 1), the scalar POST chain
  (one FP32 multiplier, one adder, the exp pipe, the divider) and `ot_hdc_sinkhorn_mc`.
- Boundary, as the RTL drives it today: **622 b a quarter** (618 down, 4 up), plus the chain entry (40 live bits into
  quarter 0), the chain return (1,025 b from quarter 3) and a 270-b fork of HBM lane 0's response. **3,823 b at the
  shell** on its quarter side. With the B2 x-staging command (EST 50 b a quarter) it is 4,023 b; with the residual
  engine's 497 b a quarter added, **6,011 b at the centre**. The shell's other ports are the 942-b record bus and the
  612-b VM packet client (5,577 b over all shell ports, without the residual engine).
- The quarter-to-quarter chain (3 x 1,065 b) and the shell-to-quarter control are **not in the die network today**:
  `cuts_v07.py` carries only the record bus, the VM packet buses and the x lanes for HC. This check adds them.
- All three placements stay inside 0.55 on every channel cut when added to the v0.7 loads. Worst channel cut:
  **0.483** (centre), 0.476 (in the SW slot), 0.476 (between SW and NW); all on y = 12 mm, which was 0.459.
- The placements differ in relay depth, not in cut load. The centre gives 10 to 14 control stages to every quarter
  and 3 to cmdproc; the two west placements give 22 to 24 stages to the east quarters and 12 to 14 to cmdproc.
- **Recommendation: the centre placement (P_C), chain order SW → NW → NE → SE, the shell as one die-placed hardened
  cluster.** Section 5.
- Three dependencies need a decision before RTL: the per-row all-tiles ready join (conflicts with rule R1 as
  written), the count-timed chain return (`SYS_LAT`), and x staging, which the RTL still does in the shell.
  Section 1.3.

## 1. The boundary

Parameters of the production shape (RTL, `ot_hgi_hc_unit` 32-80, `ot_hgi_hc_quarter` 3): W 32, SPL 4, HAW 35, AW 16,
RMAX 128 (CWW 8), NVW 6, TG 11, NXM 2. Today's relay parameters: XRLY 4, DRLY 2 (68-69).

### 1.1 Shell ↔ one quarter (two bank tiles)

Stage counts are for the recommended centre placement (section 2); the other placements are in section 3. "Both
ends" means a flop on the shell side and a pin flop in the tile.

| # | group | signals (RTL) | width a quarter | dir | activity | registered both ends today | B2 relay stages (P_C) |
|---|---|---|---:|---|---|---|---|
| 1 | window pulses | `c_start`, `c_rel`, `c_pgo` (tile 842, 847) | 6 (3 a tile) | down | one pulse a row; `c_pgo` once a record and only on tile 0 (`(g == 0) && p_req`, 444) | yes: `cc[]` 444, tile `cs_q / cr_q / pg_q` 949 | SW 11, NW 10, NE 12, SE 14 |
| 2 | window geometry | `c_base` 35, `c_soff` 140, `c_nwk` 32, `c_bnd` 64, `c_pbase` 35 (DB = 306, 434) | 612 (306 a tile) | down | quasi-static: `c_base` changes once a row (`rowbase`, S_REL), the rest once a record (S_PAR 606-611); sampled when `c_start` arrives | yes: `cd[]` 448, tile `base_q` .. 951 | same |
| 3 | ready / fault | `t_rdy`, `t_flt` (tile 849-850) | 4 (2 a tile) | up | levels; `t_rdy` rises once a row, `t_flt` sticky | yes: tile 1028-1031, shell `rb[]` 444 | same |
| 4 | x lanes | `xl_q` 8 x 150, `xl_cr` 8, `xl_done` 8 | 1,200 + 16 | down / up | streamed, one x row an edge while staging | forward: yes (`ce / a / d / m` 241-252, tile pin flops). Return: **unconnected** (`.xl_cr(), .xl_done()`, 479 and 493) | not a shell signal in B2: slice q → quarter q (SPEC 2a) |
| 5 | x-stage command and done | none in RTL | EST 50 (48 down, 2 up) | both | once a record | open | same as rows 1-3 |

Rows 1 to 3 are **622 b a quarter as driven today**. 271 of the 306 geometry bits are identical for all eight tiles
(`pbase`, `bnd`, `nwk`, `soff`, 436-448); only `c_base` (`rowbase + boff[g]`) and the pulses are per tile. Sending the
common part once a quarter and forking it at the last relay stage gives 351 b a quarter. The cut analysis uses the
conservative 622.

### 1.2 The chain, the parameter fork and the shell's other ports

| # | group | signals (RTL) | width | from → to | activity | registered both ends today | B2 relay stages (P_C) |
|---|---|---|---:|---|---|---|---|
| 6 | chain entry | `d_v`, `d_ss`, `d_nv` 6, `d_wa` 16, `d_xa` 16 = 40 live bits; `sum_in` and `f_in` of tile 0 are tied to 0 (429), `first` is a strap | 40 (of a 1,065-b port) | shell → quarter 0 | streamed every cycle of a row | yes: `dv_r / dd_r` 416-428 (DRLY), tile W-face flops `g_tir` 886-895 | 11 |
| 7 | chain hop | `o_* → d_*`, `sum_out → sum_in` 1,024, `f_out → f_in` | 1,065 | quarter k → quarter k + 1, three hops | streamed every cycle of a row | yes: tile E-face flops `g_tor` 878-883 (TOR 1), next tile's `g_tir` (TIR 1) | 2, 21, 2 |
| 8 | chain return | `csum[8]` 1,024, `cf[8]` 1 (421, 425). Tile 7's `o_v / o_ss / o_nv / o_wa / o_xa` (`cv[8]` ..) are **not used** | 1,025 | quarter 3 → shell | streamed; **no valid, timed by count** (1.3 D2) | yes: tile `g_tor`, shell `sr / fr` 417-430 (DRLY) | 14 |
| 9 | parameter response | HBM lane 0 response `{hr_v, hr_tag 11, hr_beat 2, hr_data 256}`, tag source 8 (339-342, 563-566) | 270 | HBM lane 0 of bank 0 → shell (and → tile 0) | 4 beats a record (`p_got == 4`) | yes: shell `hr_vl ..` 340-341, tile 953-955 | 11 from the fork (EST: fork at quarter 0's face) |
| 10 | record | `rec_v`, `rec_hdr` 128, `rec_a / b / o` 768, `rec_n_a / n_o` 42; `rec_rdy`, `rec_done`, `rec_fault` (82-89) | 939 + 3 | cmdproc ↔ shell | once a record | adapter `ot_hgi_hc_record` (119); die model `hgi_hc_cmd` / `hgi_hc_ret` | 3 |
| 11 | VM packet client | `vmq` 338, `vmr` 274 (90-91) | 612 | shell ↔ a slice | op 2: 3 sector reads (S_LDA 631); every POST: 3 masked sector writes a position (S_DRAIN 750); at most 4 outstanding | `vmq` is a register, `vr <= vmr` (137) | open: which slice (1.3 D7) |

Not on the shell boundary, listed so the quarter face is complete: the HBM lanes of a quarter (`hq_*` 400 b out,
`hq_rdy` 8 in, `hr_*` 2,160 in; 2,568 b) go to the quarter's lane sources.

**Totals** (`hc_central_cuts.json`, `widths`):

| scope | bits |
|---|---:|
| shell ↔ one quarter, as RTL (rows 1-3) | 622 |
| shell ↔ one quarter with the x-stage command (EST) | 672 |
| residual engine ↔ one quarter (given: 140 + 2 x 45 + 2 + 259 + 6) | 497 |
| one quarter ↔ centre, both | 1,169 |
| shell, quarter side, as RTL (4 x 622 + 40 + 1,025 + 270) | 3,823 |
| shell, quarter side, with the x-stage command | 4,023 |
| centre with the residual engine (+ 4 x 497) | 6,011 |
| all shell ports (+ record 942 + VM packet 612), without the residual engine | 5,577 |

### 1.3 Cross-boundary dependencies found

No signal crosses the boundary combinationally: every group above is launched from a flop and captured in a flop.
The problems are global joins and count-timed paths.

**D1. Per-row all-tiles ready join.** `S_RW: if ((ap_job || &w_rdy) && h_cr && rw_hold == 6'd0)` (674). `w_rdy` is
the eight relayed `t_rdy` levels (452). The HCP command for a row is issued only when all eight tiles' windows are
full. The join is registered on both sides, but it is an all-done wait across four quarters, which SPEC rule R1
forbids as written ("no record, unit or slice waits for all slices"). It is needed because the chain has no
back-pressure: a descriptor that reaches a tile whose window is not full cannot wait.
- Stale-ready guard: `rw_hold <= 2 * XRLY + 6` at S_ROW (539-543). It is a fixed count that assumes one XRLY for all
  eight tiles and also covers "the row's last x writes land in the tiles' macros" (comment, 537-538).
- B2 form (proposal, to be ruled by the B2 lead): keep one join a row, but make it a credit, not a count. Each
  quarter returns `t_rdy` with the row's epoch bit (the shell toggles it with `c_start`); the shell latches a
  per-quarter ready for the current epoch and issues when all four latches are set. `rw_hold` disappears, and the
  relay depth may differ per quarter. This is a join inside one unit's record, not a cross-slice exchange; whether R1
  admits it is **open**. The R1-clean alternative is a valid / credit seam in every tile, which changes the hardened
  tile and makes the chain elastic (D2).
- Cost: the join waits for the farthest quarter's round trip. Count in section 4; to be measured.

**D2. Count-timed chain return.** The HCP takes the sums `SYS_LAT` cycles after tap 0 with no valid:
`leaf <= dl[DW*(T_LEAF-1) + F_V] ? sys_sum : 0` (`ot_hdc_v41x_hcp.sv` 355, `T_LEAF = SYS_LAT + 1`, 141).
`SYS_LAT = 2 DRLY + 1 + 7 (SLA + 1 + TSOR + TTOR + TTIR) + 3 + 2 + (TTML - 2) + SLM + SLA + TSOR + TTOR + TTIR`
(unit 260) = 106 today. Every relay stage on the chain entry, the three inter-quarter hops and the return must be in
that number.
- B2 form: the chain stays a fixed-latency registered pipeline (plain relay flops, not elastic stages; a credit link
  cannot be used on it). `SYS_LAT` becomes `106 - 2 DRLY + D_in + D_out + R_01 + R_12 + R_23`, with the five relay
  counts taken from the die contract and asserted against it. The alternative is to return tile 7's `o_v` (it
  exists and is unused, row 8) and capture on it; the HCP's delay line would then need a valid-timed leaf. Open.

**D3. The bank order of the chain.** Stage k adds term k to stage k - 1's partial sum; the chunk order
`((0 + t0) + t1) .. + t7` is kept op for op (`ot_hdc_v41x_hcp.sv` 75-79). The order of banks 0 to 7 is therefore
fixed, and quarter k must hold banks 2k and 2k + 1 (`ot_hgi_hc_quarter` 68-71, `first && t == 0`). The physical
order of the quarters is free and is chosen in section 4.

**D4. x staging is still in the shell.** With QPAIR 1 the shell still reads x itself (`vmq / vmr` packets in S_STAGE
646, or the 32-lane wide group `wrq / wrr`, 8,224 b, with WVM 1) and drives all eight tiles' x lanes, 4,800 b,
through XRLY relays (224-252, 455-468). SPEC 2a (v0.7) moves that to slice q → quarter q. What the RTL does not yet
have:
- a command from the shell to the four slice HC stations (row base, R, positions, stride) and a completion back;
  `xl_cr / xl_done` are unconnected (479, 493). Row 5 is my estimate of it. Open.
- a completion join: S_ROW must not start before every quarter's x rows are written. Today that is the shell's own
  `w_done` / `rsec > sec_end` plus the `rw_hold` count. B2 form: a per-quarter x-done credit with the record's epoch,
  joined with D1's latch (the same join, not a second barrier).
- the BF16 check. The shell faults when a staged word's low 16 bits are nonzero (557-558, 654). The slice station
  drops those halves before the die crossing, so the check must move into the station or be dropped by contract.
  Open.

**D5. Broadcasts.** `w_start`, `w_rel` and `p_req` go to all tiles. Each is registered in `cc[0]` (444) the edge
after it is produced, then relayed; none is used in the cycle it is produced outside the shell. `p_iss = p_req`
(500) is shell-internal. No change needed beyond per-quarter relay depth.

**D6. Fault OR.** `|w_flt` (572) and the chain's `f_out → cf[8]` are sticky and latency-insensitive. No change.

**D7. Scalar POST (op 2) depends on tile 0.** `p_req <= (op != 2'd1)` (612) and S_LDA waits for `p_got == 4` (644).
The four parameter sectors are fetched through tile 0's HBM lane 0 (`c_pgo`, tile `pend`), and the shell snoops that
lane's response wires (row 9). So HC_MIX_POST, which uses no bank stage, still makes a round trip to quarter 0. B2
form: fork the lane-0 response at a registered relay stage beside quarter 0 (die glue, 270 b). The VM packet client
of the shell (row 11) has no B2 owner yet: the die model ends `hgi_vmq_hc` at `hb_hc_SW` and `hgi_vmr_hc` at
`hb_vms_SW`, and SPEC 1 lists `hc_eng`, not this shell, as a ring client. Open.

**D8. Sinkhorn is a multicycle unit.** `ot_hdc_sinkhorn_mc` clocks `ot_hdc_sinkhorn` once every STEP_CYC = 7 core
cycles (unit routed at 151.9 MHz, header 1-9). It is shell-internal and crosses no cut, but the shell's physical
view needs either a divided clock root or multicycle constraints for it.

## 2. Candidate placements

Quarter slots (die model, `quarter_slots`): SW 8,564-10,828 x 11,141-12,640; NW the same x, y 13,340-14,839; SE
21,293-23,557 x 11,141-12,640; NE the same x, y 13,340-14,839. The two-tile quarter (1,356.48 x 756.0 um) sits
inside its slot; its position in the slot is open, so distances are measured to the slot.

Shell outline: EST 1,000 x 500 um (0.5 mm2). The shell's area and sink count have not been synthesised. Open.

| id | where | shell lower-left |
|---|---|---|
| P_C | die centre, in the freed old-VM site (SPEC 1: 14,399-16,472 x 12,506-14,580), between cmdproc, coll and `hb_hc_eng` | (14,936, 13,293) |
| P_SW | inside the SW quarter's slot (the die model's present assumption: record and VM packet buses end at `hb_hc_SW`) | (9,828, 12,140) |
| P_W | in the channel between the SW and NW slots, at their east end | (9,828, 12,740) |

Model, all from `cuts_v07.py`:
- capacity of a cut = 0.75 of the upper layer over its whole length + 0.75 of the lower layer and 0.5 of M4 / M5 in
  the channels only (x cuts: M8, M6, M4; y cuts: M9, M7, M5; pitches 80 / 64 / 48 nm);
- a bus counts on a cut when its centre-to-centre segment crosses the line inside the window;
- base = the v0.7 die loads (ring 2,224 b, COLL star 4 x 2,130 b, x lanes 1,216 b a quarter).

Added buses: control 622 b and x-stage 50 b shell ↔ each quarter; chain entry 40 b; three chain hops of 1,065 b;
return 1,025 b; parameter fork 270 b; residual engine 497 b from `hb_hc_eng` to each quarter (as given). For P_C the
record (942 b, from cmdproc) and VM packet (612 b, to `hb_vms_NW`) buses are added at the shell and the old
SW-ended ones are left in place, which double counts them (conservative). For P_C the shell is added as a block, so
it removes channel capacity on the cuts through it.

Extra cut lines beyond `cuts_v07.py`: x = 11, 19, 20 and 20.8 mm (window y 10-16 mm), and y = 12.99 mm between the
two quarter slots of each side (`hcW_y12.99`, `hcE_y12.99`).

## 3. Cut results

Utilisation, v0.7 base → with the HC shell, chain and residual engine added. Bits are the added load.

| cut | base | P_C centre | P_SW | P_W | added bits (P_C / P_SW / P_W) |
|---|---:|---:|---:|---:|---|
| y 12 hub (worst channel cut) | 0.459 | **0.483** | **0.476** | **0.476** | 3,176 / 2,194 / 2,194 |
| y 10 hub | 0.462 | 0.462 | 0.462 | 0.462 | 0 |
| y 15 hub | 0.450 | 0.459 | 0.450 | 0.450 | 1,554 / 0 / 0 |
| y 12.5 hub | 0.394 | 0.414 | 0.402 | 0.408 | 3,176 / 1,169 / 2,194 |
| y 13 / y 14 hub | 0.320 / 0.385 | 0.340 / 0.406 | 0.327 / 0.392 | 0.327 / 0.392 | 3,176-3,395 / 1,169 / 1,169 |
| x 13 hub | 0.370 | 0.406 | 0.412 | 0.412 | 3,713 / 4,428 / 4,428 |
| x 15 spine | 0.317 | 0.390 | 0.355 | 0.355 | 4,325 / 4,428 / 4,428 |
| x 15.5 | 0.203 | 0.265 | 0.240 | 0.240 | 4,428 each |
| x 18 hub | 0.371 | 0.407 | 0.407 | 0.407 | 4,428 each |
| x 19 / x 20 / x 20.8 | 0.330 / 0.338 / 0.324 | 0.392 / 0.403 / 0.387 | same | same | 4,428 each |
| slice → HC, SE (`vmap_SE_x`) | 0.350 | 0.400 | 0.415 | 0.400 | 2,194 / 2,866 / 2,194 |
| slice → HC, NE (`vmap_NE_x`) | 0.304 | 0.395 (largest increase, +0.091) | 0.356 | 0.356 | 3,931 / 2,234 / 2,234 |
| slice → HC, SW / NW | 0.282 / 0.241 | 0.307 / 0.296 | 0.331 / 0.279 | 0.319 / 0.279 | |
| between W quarters (`hcW_y12.99`) | 0.122 | 0.146 | 0.150 | 0.208 | 2,544 / 2,906 / 4,241 |
| between E quarters (`hcE_y12.99`) | 0.034 | 0.069 | 0.058 | 0.069 | 3,259 / 2,234 / 3,259 |
| y 16 hub (slice-body artifact, SPEC 6a) | 0.770 | 0.776 | 0.770 | 0.770 | 612 / 0 / 0 |

- **Every channel cut stays ≤ 0.55 for all three placements.** Worst: 0.483 (P_C), 0.476 (P_SW), 0.476 (P_W), all on
  y = 12 mm. No cut is pushed over 0.55 or 0.60 by the HC load (`over_055` is empty in every case).
- y = 16 mm was already 0.770 in v0.7. SPEC 6a explains it as a centre-to-centre artifact through the NW / NE slice
  bodies (real channel cuts beside it 0.455 and 0.276). P_C adds 612 b to it (the VM packet client to `hb_vms_NW`).
  Attaching that client to a south slice removes the addition.
- The W-E load is the same in every placement, 4,428 b on every x line from 11 to 20.8 mm: one chain hop, the
  return or the entry, two quarters' control and two quarters' residual traffic always cross.
- Variant, residual engine centred at the shell instead of `hb_hc_eng` (P_C only): worst 0.487 (y 12), largest
  increase +0.103 on `vmap_NE_x` (0.407).
- Quarter face (`quarter_face`, one 48-nm layer along the face, the convention of `b2_functional_map.json`): the
  756-um E / W face carries one chain port 1,065 + control 622 + x-stage 50 + residual 497 + x lanes 1,216 = 3,450 b
  of 15,750 tracks, **0.219**. With the quarter's HBM lanes (2,568 b) on the same face it is 0.382. The 1,356-um
  N / S face takes the vertical chain hop: 1,065 of 28,260, 0.038.

Limits of the model, all open:
- segments are straight lines between block centres. The W-E crossing runs over `hb_hc_eng` and the SU / SFU
  columns; relay sites every 504 um on that path are not placed. A die GRT with placed relays is the real check.
- the die model still carries the old 2,264 x 1,499-um HC slot, not the two-tile quarter.
- the shell outline is an estimate.

## 4. Relay stages and the chain

Stage count = ceil(distance / 504 um) (SS: 261 ps + 1.135 ps/um, one 833-ps stage). Distances are Manhattan, from
the shell centre to the quarter slot, and slot edge to slot edge between quarters. Face flops at both ends already
exist in the RTL and are not counted again.

**Chain order: SW (banks 0, 1) → NW (2, 3) → NE (4, 5) → SE (6, 7).** Any order has three quarter-to-quarter hops;
this one has exactly one W-E crossing. An order that alternates sides has three.

| hop | distance um | stages |
|---|---:|---:|
| SW → NW | 700 | 2 |
| NW → NE | 10,466 | 21 |
| NE → SE | 700 | 2 |
| tile to tile inside a quarter (21.6-um seam) | | 0 |

| | today (RTL) | P_C | P_SW | P_W |
|---|---:|---:|---:|---:|
| control stages to SW / NW / NE / SE (XRLY) | 4 each | 11 / 10 / 12 / 14 | 0 / 2 / 24 / 22 | 1 / 1 / 23 / 23 |
| chain entry stages (shell → quarter 0) | 2 (DRLY) | 11 | 0 | 1 |
| inter-quarter stages | 0 | 25 | 25 | 25 |
| chain return stages (quarter 3 → shell) | 2 (DRLY) | 14 | 22 | 23 |
| `SYS_LAT` | 106 | 152 (+46) | 149 (+43) | 151 (+45) |
| `rw_hold` = 2 x max XRLY + 6 | 14 | 34 (+20) | 54 (+40) | 52 (+38) |
| record bus stages from cmdproc | 13 relays in the die model (to `hb_hc_SW`) | 3 | 14 | 12 |
| relay flops: control / chain / return | | 29,234 / 26,625 / 14,350 | 29,856 / 26,625 / 22,550 | 29,856 / 26,625 / 23,575 |

Latency effect (counts, **to be measured, not priced**):
- The chain adds `SYS_LAT` once per HCP command, that is once per row (S_RW → S_RC waits for `h_last`, 674-680),
  not per chunk: the chain streams. The row loop is serial (S_ROW → S_RW → S_RC → S_REL), so a 24-row HC_MIX sees the
  increase 24 times: +46 a row for P_C, +43 and +45 for the west placements. The 21-stage W-E hop is in all three.
- The window-start round trip adds up to +20 a row (P_C) or +38 to +40 (west). It runs while the windows fill from
  HBM, so part or all of it may be hidden. With the epoch-tagged ready of D1 the count goes away and only the real
  round trip remains.
- Scalar POST (op 2): only the parameter fetch touches a quarter. P_C: `c_pgo` takes 11 stages instead of 4 and the
  response fork takes 11 back, +18 cycles, in parallel with S_LDA's three sector reads; exposed only if it ends
  after them. West placements: no increase. The 540 / 540 = 1.000 qualification at 550082537 was taken with the
  unit's own relay counts and does not cover any of these placements.
- The residual engine's paths (FUSED.HC_POST 222.7, HC_PRE_NORM 649.4 cycles, gate measured ≤ 1.10 x price) are 12
  stages to the W quarters and 1 to the E quarters from `hb_hc_eng` (`residual_um_stages`). They are the parent
  stream's to measure and are not affected by the shell placement.
- If a measured count misses its gate, the levers are structural (shorter crossing, overlapped rows with
  double-buffered windows), never a new price.

## 5. Recommendation

**Boundary.** Section 1 with these B2 forms:
1. control: rows 1-3 per quarter, relay depth per quarter from the die contract; ready returned with a row epoch
   and latched per quarter in the shell (D1); no `rw_hold` count;
2. chain: fixed-latency relay pipeline in the order SW → NW → NE → SE; `SYS_LAT` derived from the five contract relay
   counts and asserted (D2); the entry carries 40 b, the other 1,025 b of quarter 0's chain port are tied at its face;
3. x: slice q → quarter q as SPEC 2a; the shell sends a per-quarter stage command and takes a per-quarter x-done
   credit (D4); the 4,800-b shell-driven x path and the shell's wide read group are removed;
4. parameters: registered fork of bank 0's HBM lane 0 response at quarter 0 (D7);
5. residual engine: the given 497 b a quarter, unchanged.

**Placement: P_C, the die centre.** Reasons:
- cut load is the same class as the others (worst 0.483 against 0.476) and inside the target;
- control depth is balanced (10 to 14 stages) instead of 0 to 24, so the per-row join waits 14 stages, not 24;
- the record bus is 3 stages from cmdproc instead of 12 to 14;
- it sits beside `hb_hc_eng`, so both HC centre blocks share one region and one clock entry area.

Its cost: it puts a block in the channel the B2 spec freed (x 15 goes 0.317 → 0.390, x 15.5 0.203 → 0.265), and the
scalar POST parameter fetch gets 18 cycles longer. The slot needs the B2 lead's agreement.

**Physical-view plan.**
- The shell is substantial logic (HCP control and a 32-leaf FP32 tree, four FP32 units, Sinkhorn, 6,144 b of raw-mix
  store `TP`, 128): **one die-placed hardened cluster**, not glue. No third hard level: any hard leaves sit directly
  in the cluster, as the bank tile does with its four lane leaves.
- M5 leaf default. Clock: ≤ 15k sinks a root. The sink count is not synthesised; my estimate is 20k to 40k flops
  (the HCP delay line grows with `SYS_LAT`), so expect two or three roots, for example HCP control + tree, POST
  units + stores, and Sinkhorn on its divided clock (D8). Open until a synthesis count exists.
- Seams: every port in section 1 is a face flop in the cluster and a pin flop in the tile. The XRLY / DRLY shift
  registers leave the unit RTL: relay stages between the shell and the quarters are die relay stages in the
  channels (about 70k flops for P_C, table in section 4), placed by the die flow like every other bus.
- Glue goes into tiles: the tie-off of quarter 0's unused chain inputs, the common-geometry fork (if the 351-b form
  is taken) and the epoch latch belong to the tile face or the shell, not to a new block. `ot_hgi_hc_quarter` stays
  a logical group of two die-placed tiles.
- The lane-0 response fork is one relay stage of die glue beside quarter 0.

**Gates still open (nothing here is qualified).**
1. B2 lead ruling on D1: is the per-row ready join inside the HC unit admitted under R1, or must the tile seam
   become valid / credit.
2. B2 lead agreement to a shell block in the freed centre channel, and the slot.
3. Owner of x staging in B2: the stage command, the x-done credit, and where the BF16 check lives (D4).
4. Owner of the shell's VM packet client (which slice, ring client or local tap) (D7).
5. Shell synthesis: area, sink count, clock-root split, Sinkhorn clocking (D8).
6. Die network update: add the chain hops, control, return and fork to the die model; replace the old HC slot with
   the two-tile quarter; then die GRT with placed relays on the W-E crossing.
7. RTL (after 1 to 4): per-quarter relay depths, epoch ready, `SYS_LAT` from the contract, removal of the
   shell-driven x path; exact + mutants on the production shape.
8. Throughput: HC_MIX_ROWS, HC_MIX and HC_MIX_POST measured on the placed relay counts against their immutable
   prices (≤ 1.10 x); the 540 / 540 scalar POST result must be re-taken.
9. The gates already listed in `b2_functional_map.json` (`missing_gates`), unchanged.
