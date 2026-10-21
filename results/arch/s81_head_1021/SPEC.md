# S81 release head die (S81.HEAD), spec v1 (S81-HEAD, 2026-10-21)

The die hosts the LM head, argmax and MTP sequencer for the S81 72-frame release array.
Rack: claude/rack-1021@4b528ad2b, 12 head dies = H0, H1, H2 groups x TP4 rank.
Interfaces follow the owner/coordinator decisions of 10-21:
- direct cabling;
- host on head dies only; stage dies start locally (option b);
- the last stage's single NEXT circuit feeds the head;
- the head forwards to mtp.0 over the draft fan-out links;
- the head returns tokens to S000 over the normal stage circuit.

## 1. Content (one die master for all 12 dies; ROM code differs per rank)

| Block | Master (new wrapper; reused core) | Count | Size (um), estimate | Notes |
|---|---|---|---|---|
| LM-head tile | `ot_s81hd_tile` around `ot_dsrom_head_bundle` (5 elems, 10 x ot_rom_4096x274_m8, 128 vocab rows, measured 8,357 cyc go->result, token 21946 exact) | 253 | 648 x 648 (synth-sized at 40-60 %) | rank r holds bundles: ranks 0/1 = 253, ranks 2/3 = 252 (sum 1010 x 128 = 129,280 rows). On ranks 2/3, tile 253 has strap `ten`=0 and is excluded from the merge. Straps per tile: `row0[16:0]`, `ten` |
| Spine out node | `ot_s81hd_spo` (register + 3-way forward) | 26 (13 N + 13 S) | 216 x 648 | carries x/go + null-best to the W/E chain starts |
| Spine return node | `ot_s81hd_spr` (capture-all-then-fire 3-way argmax) | 26 | 216 x 648 | lowest-id first-max (same key as ot_rom_argmax_rows) |
| Head controller | `ot_s81hd_ctl`: x store (5,120 BF16 = 80 kb SRAM macros), stream issue, N/S final compare, rank merge (ot_rom_argmax_rows rule), `dsfd_mtp_seq`, token/seed former, host frame endpoint, fault/status | 1 | ~1,500 x 1,500 | die centre between the N and S spines |
| Stage-circuit endpoint | `ot_s81hd_lep`: 4 x `dsfd_coll_lane_w_safe8_ntf` + `ot_s81sl_lep_mu_ab #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1)` (the same lep as stage s_0N, so the NEXT-circuit protocol is identical) | 1 | ~1,300 x 2,600 | pair B (lk_WN2/3) RX: XB beats from S240 or the previous head group. Pair A (lk_WN0/1) TX: forward to the next head group, or token return to S000 (H2) |
| Lane block | `ot_s81hd_lane`: 1 x `dsfd_coll_lane_w_safe8_ntf` + static adapter. Link credits stay at the off-die boundary; the core side is valid-only, with a TX SRAM buffer sized by the schedule (overflow = fault) and RX always-accept (would-overflow = fault) | 13 | ~520 x 1,100 | 6 TP4 mesh (3 pairs: rank argmax exchange), 2 host (lk_HOST0/1), 5 draft fan-out (1 per draft row package, MTP plan P2) |
| SerDes PHY | `ot_pdie_serdes` (hard macro, slot 518.4 x 3844.8) | 17 | | = rank-die 10 + host 2 + draft 5 (rack: "rank-die master + 1 host pair + 5 draft") |

There is no HBM on the head die. The LM head is ROM-resident and the argmax/MTP state is small, so the rack's "4 stacks per head die" row (10-06 rule) is not needed. That row is MODEL: dropping it saves 48 stacks. The rack owner decides.

## 2. Topology (neighbour-only hops, no star hub)

- One bus type B, 565 b, on every array port:
  - `[511:0]` x (xa = [255:0], xb = [511:256]), `[512]` go, `[513]` xv;
  - `[514]` rv, `[531:515]` row, `[563:532]` bits (FP32 logit), `[564]` flt (OR-accumulated).
- `ot_s81hd_tile`: ports `ck, rst_n, i[564:0], o[564:0], row0[16:0], ten`.
  - It forwards x/go one registered cycle per tile.
  - It captures the chain best (i.r) and its own bundle result. When both are present it sends max(i.r, own) on o.r.
  - The bundle's x timing (`slice m at G+5+m`) holds at every tile, because go travels with the stream.
- Row-pair chain: 10 tiles.
  - It starts at spo level L, runs outward on row 2L, makes a U-turn and comes back on row 2L+1 to spr level L.
  - There are W and E chains per level, and 13 levels per half (N, S), so 52 chains of <= 5 tiles a row (253 placed of 260 slots).
- `ot_s81hd_spo`: ports `ck, rst_n, i, o, ow, oe`.
  - The top spo's `o` feeds the top spr's `i` (spine U-turn).
  - The ctl drives a null best (rv 1, bits -inf, row 1FFFF) with go, so every port is bound and no end variant exists.
- `ot_s81hd_spr`: ports `ck, rst_n, i, iw, ie, o`. The bottom spr `o` goes to ctl `sn_i`/`ss_i`. The bottom spo `i` comes from ctl `sn_o`/`ss_o`.
- Rank merge: the local best (50 b + tag) goes from ctl to the 3 mesh lanes. All 4 ranks hold the same merged result after one hop (all-gather, then the same deterministic compare). The token then goes through `dsfd_mtp_seq` to:
  - pair A: the next head group, or the token return to S000;
  - the 5 draft lanes: seed to mtp.0 / the row packages;
  - the host lane (results and status).

## 3. Links, schedule, latency (MODEL until GEN measures)

- Stage circuit: XB in = 5,120 BF16 = 81,920 b = 160 beats of 512 b; token out = 1 beat. Head hop D = 251-257 cyc (rack).
- Per position: XB ingress 160 + x tree <= ~32 + bundle 8,357 + return tree <= ~40 + mesh merge 251 + ~20 + MTP seq ~6 = ~8,870 cyc (7.4 us). This replaces the priced lm_head 8,416 + argmax 12 + labelled 42.
- Occupancy: 8,357 cyc per position < the AR slot gap of 20,555 (cal c028c373c). One group covers AR. The 3 groups (H0..H2) give MTP verify/draft positions in flight. The calendar (L5B-CAL successor) owns the slot assignment.
- The schedule is static. There is no on-die backpressure: chains and spines are valid-only pipelines, and link credits stay in the lanes (off-die boundary). Every added cycle goes to the calendar.

## 4. Die size and floorplan

- 17 SerDes slots at the W/E edges in G7 slot geometry, column A + column B, >= 86.4 streets:
  - W: lep pair A/B (4) + host (2) + 2 draft;
  - E: mesh (6) + 3 draft.
- The tile array is 2 x 5 columns either side of a two-lane spine, with 26 rows of 648 + channel per half side.
- Target ~13 x 20.5 mm, about 270 mm². That is well inside the 858 mm² reticle (26 x 33 mm). The outline grows instead of squeezing.
- Relay channels: dv_route72 relay stations on every link longer than 405 um. Tile-to-tile and tile-to-spine hops are abutted (< 405 um). U-turn hops (one tile pitch, ~760 um) get 1 station.

## 5. Cut analysis (bits per cut vs tracks; limit 0.55-0.60)

| Cut | Bits | Tracks (estimate) | Ratio |
|---|---|---|---|
| Vertical, spine/E-array boundary, 20 mm | 13 x 2 x 2 x 565 = 29,380 | 3 H layers x ~6.9/um x 20,000 = 414k | 0.07 |
| Horizontal at ctl, 13 mm (spine 2 x 565 + 13 lanes x 1,074 + lep ring 2 x 1,104) | ~17,300 | 2 V layers x ~6.9/um x 13,000 = 179k | 0.10 |
| Spine node face, 648 um | 3 x 565 = 1,695 | 3 layers x 6.9 x 648 = 13.4k | 0.13 |
| Tile face, 648 um (i or o) | 565 | ~13.4k | 0.04 |

PASS everywhere (<= 0.13).

## 6. Clock / reset / safety (summary; full 8-point review per new tile in its kit README)

- Clock regions:
  - each row-pair chain with its spo/spr node (~4 x 1.6 mm, identical tiles);
  - the spine-root/ctl region;
  - each lane/lep block.
- Every crossing between regions (spine level to level, ctl to lanes, ctl to lep) is a land-plan row: a fixed-latency landing ring with no flow control.
- Spread is <= 80 ps inside a region at TT+FF.
- Reset: per-block reset leaves with 2-stage landing. Only control/valid bits are reset; the bundle datapath is not reset.
- Fanout: x enters each tile once, and the bundle's BST stages fan it out internally. The census must be <= 32 loads per driver; spo/spr 3-way copies are kept as registered copies.

## 7. Reuse and binding

- Bind CLOSED views where they are identical: `ot_pdie_serdes` (macro), `ot_rom_4096x274_m8` (macro).
- No CLOSED view exists for `ot_dsrom_head_bundle`/elem in the current closure flow. The 10-05 r4_A/B physical.json are characterisation records in the old flow, with no views. `ot_s81hd_tile` is therefore a new tile, gated main + fallback.
- `dsfd_coll_lane_w_safe8_ntf` and `lep_mu_ab` are bound when their kits close (lepmu t5c/t5d live).
- Die chain: plan -> strict bind -> GEN -> GRT -> STA -> CLK (dv_diecase / dv_rvcase as `release72/run_die72_g7.sh`). The script is `tools/s81_dv/head72/run_head_h1.sh`, run on the fleet with unpinned ot-run.
