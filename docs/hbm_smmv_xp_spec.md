# HBM SM.MATVEC x plane (xp): spec settlement and physical partition plan

Status: DRAFT 2026-10-13 (stream `el1013-hbm-redesign-smmv`, branch `claude/hbm-redesign-smmv`). It settles the two
findings of the redesign log, and replaces the log's assumed face lengths with the placed ones of the die contract
`results/arch/hier_contract_1011/r25gq.json` v11 (the B2 placement). `results/rtl/hbm_accel_die_floorplan_20261005/floorplan.json`
is the pre-B2 24.4 x 24.6 mm die with ONE central `hb_vm`: it has no quadrant slice, so no xp face exists in it.

Grades used below: **placed** = coordinates read from the contract; **counted** = counted from RTL; **modelled** = the
schedule model `xd2.py` (section 2); **estimate** = not synthesised, not routed. Nothing here was simulated in RTL or routed.

## 1. Finding 1: lane credits (10 vs 16)

### 1.1 What the 10 of B2 v0.8 is

`ot_vms_bank` (`rtl/hbm_accel/generic/vm/b2/ot_vms_bank.sv`): `rq_cr` returns one credit **when the request leaves the
bank's lane queue**, and `rr` has **no back-pressure**. So D-B2-12's `4 + 2 x S` (parameter `RRS`, 4 b a read group,
default 3 -> 10 entries of 12 b) sizes the bank REQUEST queue. It does not size the client's landing store.
`ot_hgi_xp_rd` uses a different counter: `CR` = landing space, returned when the join pops a wave. The two loops are:

| loop | length (counted, T1 abutted on the slice face, S relay stages each way) | bound on the rate |
|---|---|---|
| bank credit (B2, 10) | issue flop -> bank pin flop -> queue -> `rq_cr` flop -> T1 pin flop -> counter = 5 + 2 S | 10 / (5 + 2 S): 1 wave/cycle for S <= 2 |
| landing credit (`CR`) | issue flop -> pin flop, queue, S1, S2, M, C, D, R (8 edges to `rr`) -> T1 pin flop -> landing write -> pop = 11 + 2 S | CR / (11 + 2 S) |

The unit bench modelled the slice as an 11-cycle request-to-response delay (4 up + 3 bank + 4 down). The bank alone is
8 edges pin to `rr` (counted), so with T1 abutted the response is back after 9, and the landing loop is 11 at S = 0.

| CR | S = 0 (RT 11) | S = 1 (13) | S = 2 (15) | S = 3 (17) | S = 4 (19) |
|---|---|---|---|---|---|
| 10 | 58.2 el/c (1.11x of 52.4) | 49.2 (0.94x) | 42.7 | 37.6 | 33.7 |
| 16 | 64 | 64 | 64 | 60.2 (1.15x) | 53.9 (1.03x) |

S includes relay stages INSIDE the slice between a bank tile and the slice face (bank tiles are 308.88 um square in a
950.4 x 1,684.8 um slice, so the far banks are > 500 um from any face). That count is not in the RTL (`ot_vms_slice`
wires banks straight to its ports) -> **unverified**; it is the number that decides the margin.

### 1.2 Cost of 16

- Landing store: 8 x 16 x 256 = 32,768 flops against 8 x 10 x 256 = 20,480 (+12,288). At the measured FIFO cost of
  2.364 um2 a stored bit (ot_meso_fifo W512 D4 = 4,842.31 um2 std-cell, `results/uarch/meso_fifo_20261004`, quoted in the
  floorplan record `r15_lint_fix.meso_fifo.area_basis`): 77.5 k um2 std-cell, 129 k um2 placed at 0.6 utilisation, against
  48.4 k / 80.7 k. Delta **+48 k um2 a quadrant, +0.19 mm2 a die**.
- Clock roots: with the pin flops the rule requires (section 3) T1 is 37.6 k sinks. CR 16: 4 lane-pair leaves of 9.3 k.
  CR 10: 2 four-lane leaves of 12.5 k. Delta **+2 leaf roots a quadrant**.
- Slice face: **no extra bit, no extra track.** `vxl` stays rdn 2,065 + rup 129; the per-lane credit bit is already in rdn.
- Slice side: **no deeper request queue**, provided T1 also runs the B2 bank-credit counter (10, from `rq_cr`). Without
  it, 16 outstanding requests can sit in a 10-entry bank queue whenever the bank read port is contended, and the bank
  latches FAULT. `ot_hgi_xp_rd` has no `rq_cr` port today -> RTL obligation.
- A 16 x 546 macro (`ot_sram_1r1w2c_16x546_m1`, 176.9 x 81.0 um) does not help: two lanes land in different cycles and
  would share one write port, so it takes 8 macros (114.6 k um2), no saving over flops.

### 1.3 Alternatives

- **Shorten the round trip to <= 9.** Not reachable: the bank pipeline alone is 8 edges and the pin flops on both sides
  are mandatory; the landing loop is 11 at best. At 11, 10 credits give 58.2 el/c, an 11 % margin that disappears with ONE
  relay stage each way (0.94x).
- **Keep 10, accept 53 el/c.** Modelled cost at 53.3 el/c: L0 3,172 against 3,140 cycles, L1 3,930 against 3,895 = **+1.0 %
  of the SM.MATVEC layer**, paid on the two loads the dataflow serialises (cold start, router). Zero margin on the w2 chain.
- **Raise the bank parameter (`RRS` 6 -> 16 entries).** Needs a re-harden of the closed `vms_bank` (v08) for +72 flops a
  bank; `LQ = lqmax` also declares the 276-b write queues 16 deep (pruned only if synthesis proves entries 10-15 dead).
  Not needed once T1 honours `rq_cr`.

### 1.4 Recommendation

**CR = 16 as a T1-private landing depth; the B2 bank stays at RRS 3 (10); T1 adds the `rq_cr` bank-credit counter.**
Decisive number: with CR 16 the reader meets 52.4 el/c for any round trip up to 19 cycles (S <= 4); with 10 only at
exactly 11 (S = 0). Cost 0.19 mm2 a die and 2 leaf roots a quadrant.

**B2 spec change (text only, `results/arch/hbm_b2_1012/SPEC.md`, D-B2-12 and section 2 "Local lane group"):**

> D-B2-12 credits are BANK-QUEUE credits: a client holds at most `4 + 2 x S_g` unreturned `rq_cr` / `wq_cr` credits a
> lane. A client's landing store for `rr` is client-private and unbounded by this rule (`rr` is never back-pressured);
> the SM x reader holds 16 a lane. The SM x-load (`vxl_<q>`) is read group 1 of `ot_vms_slice` (RG = 2: group 0 = the
> local lane chain), NOT slot 4 of the chain's round-robin `lanearb`; `S_xl` <= 2, so RRS[1] = 3 stands. The bank read
> port is one a cycle, round robin over {group 0, group 1, packet}: a wave completes at the rate of its slowest bank.

No RTL parameter of `ot_vms_bank` / `ot_vms_slice` changes. `ot_hgi_xp_rd`: `CR` stays 16; add `rq_cr[7:0]` and `BCR = 10`.

### 1.5 Open risk this finding exposed (not settled)

SPEC section 2 lists the SM x-load as slot 4 of a per-BURST round-robin `lanearb` shared with SU, SFU, HC and ATT; the
contract gives it its own pins (`t_xl_rdn`, `f_xl_rup`). Either way the bank has ONE read port. If another client reads
the same slice during a load, the x rate halves: modelled at 32 el/c L0 is 3,300 cycles (1.119x) against 3,140 (1.064x).
The concurrent read duty of group 0 during the w2 chain is **not measured**.

## 2. Finding 2: x store depth (XD 128 vs 160 / 192)

**How the store is built (counted).** `ot_hbm_accel_smh` leaf: slice width `LBS x 266 + LSB x 16` = 788 b -> `NXL` = 4
macros `ot_sram_1r1w_128x256_m1_r2c2` (94.824 x 41.064 um = 3,894 um2). 32 leaves an SM -> 128 macros an SM, 4,096 a
die; an address holds 25,216 b = 13 beats of 2,048 (`NBEAT`), 3.23 Mb an SM. The production configuration is checked as
`XD == 128` (`ot_hbm_accel_smh.sv` l. 136) and the tiles (`smh_tile_eg` / `_wg`) are hardened at it.

**Cost of growing.** There is no 160- or 192-deep macro; the next one is `ot_sram_1r1w_256x256_m2_r2c2` (172.824 x
41.064 um = 7,097 um2):

| | XD 128 | XD 160 / 192 on the 256-deep macro | a new 192-deep compile (interpolated, not compiled) |
|---|---|---|---|
| macro area an SM | 0.498 mm2 | 0.908 mm2 (+0.410, +11.3 % of the 3.638 mm2 SM slot) | ~0.70 mm2 (+0.205) |
| a die (32 SMs) | 15.9 mm2 | 29.1 mm2 (**+13.1 mm2**) | ~+6.6 mm2 |
| address width | 7 | 8 | 8 |

Width changes at 8 b: `xw` 2,063 -> 2,064 (SM pin `x[2062:0]`, every spine stage), `op_xb`, `xw_addr`, the row / beat /
`fs_d` / `fx_b` buses inside smh (+1 b each), `ot_hbm_accel_issue_pq` `XDEPTH`, `ot_hgi_xp_sched` `rec_xb` / `iss_xb` /
`s_xb` and its hard-coded `> 9'd128` range check, and `x_xb` in `ot_hgi_smmv`. Every smh tile is re-hardened (4 macros a
leaf each 78 um wider).

**Does 128 bind in L0 / L1? (modelled.)** `xd2.py` (kept in the session scratch `/tmp/claude-1000/smmv-spec/`, not
committed) replays the price sheets of `sm_tput_bench.program_records` (`meta.json` regenerated 10-13 03:39, scratch) with
a slot choice that overlaps the oldest readers first, one reader at 64 el/c + 15 cycles.

| | XD 128 | 160 | 192 | 256 |
|---|---|---|---|---|
| L0, router x after wo_b (dataflow) | 3,140 (1.0644x) | 3,140 | 3,140 | 3,140 |
| L1, same | 3,895 (1.0558x) | 3,895 | 3,895 | 3,895 |
| L1, router x pre-loadable (no dependency) | 3,895 | 3,800 | 3,800 | 3,800 |
| L0, no dependency, greedy slot choice | 3,140 | 3,140 | 3,140 | 3,045 |

- The only exposed loads are the layer's first (95 / 111 cycles, cold start of the bench) and the router's (95).
- The router's x (BF16 K 5,120, 80 addresses, `akey` VM 41152) is the post-attention state, i.e. wo_b's result written in
  place. Its load cannot start before wo_b is done, whatever XD is. Under that dependency **XD 128 costs 0 cycles** in L0
  and L1. The dependency is read from `akey` and the log, **not verified against the program's O addresses**.
- If the router x could be pre-loaded, XD 128 would cost 95 cycles a layer (2.6-3.2 %); 144 addresses (wo_b 64 +
  router 80) remove it with a look-ahead allocator, so XD 160 would be enough and 192 buys nothing more.
- No other pair binds: w2 chain 6 x 16 + FP4 K 5,120 24 = 120 <= 128.

**Recommendation: keep XD 128.** 13.1 mm2 a die and a re-harden of every closed smh tile buy 0 cycles on the priced
program. Compiler obligation (hardware verifies 1 and 3, fail closed):

1. every record: `xb + nxe <= 128`, `nxe = 8 x ceil(K / {BF16, INT8: 512; FP8: 1,024; FP4: 2,048})`; A is 8-sector aligned;
2. a load's range may overlap only slots whose last reader is at least two records back, or the record that produces
   the load's own x (which serialises it anyway); the allocator is liveness-aware and looks one load ahead;
3. a load never overlaps a slot a later `XR` record names;
4. a BF16 record with K > 3,072 (nxe > 48) next to a neighbour of more than 128 - nxe addresses is single-buffered: the
   compiler must show the pair is dataflow-serialised, else report the exposed cycles (no silent loss).

Re-open if a program appears with a BF16 K 5,120 load that is NOT serialised behind its neighbour.

## 3. Physical partition plan

### 3.1 Real placement (placed; SW cluster, the other three are mirrors)

| object | origin um | size um | xp pins |
|---|---|---|---|
| `hb_vms_SW` | (13,399.8, 8,998.6) | 950.4 x 1,684.8 | `t_xl_rdn[2064:0]` N face M5; `f_xl_rup[128:0]` E face M4 (offset 1,157) |
| `sm0`..`sm7` (`hfd_sm`, MY) | columns x 625.1 / 4,271.6 / 7,917.7; rows y 2,162.2 / 4,503.6 / 6,197.0 (3 + 3 + 2) | 3,214.08 x 1,131.84 | `x[2062:0]` master W face (die E), M4, offset 1,036.4 of 1,131.84 |
| `hb_cmdproc` | (14,736.0, 14,623.2) | 1,399.7 x 1,404.0 | `cSW[898:0]` W face M4 |
| column channels | x 3,839.2-4,271.6 and 7,485.7-7,917.7 | 432.4 / 432.0 wide | col 1-2 partly under `ep_S0` |
| row channels | y 3,294.0-4,503.6; 5,635.4-6,197.0 | 1,209.6 / 561.6 high | |
| strip above SM row 2 | y 7,328.9-7,976.9 (to `hb_su_SW`) | 648.0 high | |

The log assumed 1,036.8 / 500 / 480 um. The real ones are 950.4 (slice face), 432.0 (SM channel) and 1,404.0 (cmdproc face).
The 760 x 480 um "xload macro field" is not a slot of the contract.

Three facts the assumed geometry hid:

1. **The slice is not next to its SMs.** Slice face to the SM x pins is 7.4 mm (sm5) to 17 mm (sm0) Manhattan: 13 to 36
   stages at the 430.56 um `ot_fwd_link_stage` span. The x-load latency is therefore not "+15" but about 11 (read) + 4
   (quantise, write) + 36 (spine) = **~51 cycles** to the farthest SM. Modelled at +50: L0 3,210 (1.088x) against 3,140
   (1.064x), i.e. +35 cycles on each dataflow-serialised load; the hidden loads stay hidden.
2. **The xl pins are on two faces** (rdn N, rup E, 527 um from the corner) and on the far side from the SM field.
3. **The spine is a tree of ~66 relay stages a quadrant** (estimate from Manhattan lengths: 8 slice to field, 17 trunk, 3 x
   11 column drops, 8 taps), ~154 k flops a quadrant, ~0.45 mm2 at the closed relay's 2.93 um2 a flop footprint
   (`vms_relay_ring`: 2,226 flops in 43.2 x 151.2 um, `closes_signoff` true). They are NOT in any SM's clock root.

### 3.2 Site

T1, T2 and T4 go **south of the slice** (x 13,399.8-14,350.2, y 7,329-8,998.6: 950 x 1,669 um, no die slot of contract
v11 overlaps it; relays and stations that are not slots are unverified), toward the SM field. This needs a slice pin
re-plan: `t_xl_rdn` and `f_xl_rup` to the S face. T4 sits with T1, not at the cmdproc face (4.4 mm away): `cSW` reaches it
over ~10 relay stages, latency only.

### 3.3 Leaves (sinks counted from `ot_hgi_xp.sv` dd090a0d3 plus the pin flops the rule requires)

| leaf | n a quadrant | sinks a root | content | RTL |
|---|---|---|---|---|
| `hgi_xp_rd_ln` | 4 | 9,300 | 2 lanes: rs pin flops 2 x 257, landing 2 x 16 x 256, head register 512, credits, pointers | to split out of `ot_hgi_xp_rd` |
| `hgi_xp_rd_ctl` | 1 | 700 | command queue 4 x 30, cursor, wave meta 16 x 17, join | to split |
| `hgi_xp_qp` (T2) | 1 | ~9,500 (estimate) | wave register 2,048, 3 quantise / pack stages, beat 2,063 | NOT WRITTEN |
| `hgi_xp_spine` (T3) | ~66 | 2,330 | {xw 2,063, issue bus ~260} relay | `ot_fwd_link_stage`, width TBD |
| `hgi_xp_sched` (T4) | 1 | 800 as written; ~2,600 with the 899-b record pin flops | window 8 x 46 b, 16 slots x 17 b | exists |

All <= 15,000. Every hop <= 430.56 um by construction of the relay master; the lane leaves abut the slice face (4 x 237.6
= 950.4 um) and T2 abuts them. `hgi_xp_rd_ctl` must sit at the face centre (<= 475 um to the outer lane leaves) or take
one more registered stage each way on `cr_ok` / `pop` (round trip +2, covered by CR 16).

Not registered at the pin today: `rs_d` writes the landing FIFO directly (16 write enables a bit) and `rec_rdy` is
combinational. Both are in the `_todo` lists of the specs.

### 3.4 Cuts redone (bits / usable tracks; usable = 18.2 tracks/um for the two layers of one direction)

| cut | face (placed) | bits | tracks | ratio | note |
|---|---|---|---|---|---|
| A slice N face, xl only | 950.4 um | 2,065 | 17,297 | **0.12** | |
| A slice N face, every bus on it (ring 2 x 2,148, hc 338, vcbc 2, xl) | 950.4 | 6,701 | 17,297 | **0.39** | on the M5 pin layer alone (9,900): **0.68 > 0.60**, an existing condition of the slice face |
| A' xl moved to the S face (lg rdn / wdn, r, q, + xl 2,194) | 950.4 | 4,925 | 17,297 | **0.28** | M5 alone 0.50; the N face drops to 0.47 |
| B T1 -> T2 abutted (wave 2,048 + meta 18) | 950.4 | 2,066 | 17,297 | **0.12** | M5 alone 0.21 |
| C spine in a column channel, alone | 432.0 | 2,323 | 7,862 | **0.30** | |
| C + the two upper-row weight buses of that column (2 x 1,143) | 432.0 | 4,609 | 7,862 | **0.59** | assumes both climb this channel: not placed |
| C + weights + two result buses (2 x 270) | 432.0 | 5,149 | 7,862 | **0.65 > 0.60** | FAIL if all share one channel: needs the die GRT |
| C spine trunk in the strip above SM row 2 | 648.0 | 2,323 | 11,794 | **0.20** | |
| D cmdproc W face, every bus (cSW 899 of 10,828) | 1,404.0 | 10,828 | 25,552 | **0.42** | M4 alone 0.74, existing condition; xp adds no bit |

Faces that do not exist in the placement: the T1 / T2 / T4 slots themselves; the xl pins on the slice S face; a spine
route (no `xw` relay chain from slice to SMs in contract v11; the pre-B2 record has `xbcast_*` from the central VM, max
15.9 mm / 38 stages); the SM-side issue bus pins (the contract has `c[111:0]` on the SM N face only).

### 3.5 Spec drafts

`tools/ref_tile/specs_xp/hgi_xp_{rd_ln,rd_ctl,qp,spine,sched}.json`, shaped on `tools/ref_tile/specs/hgi_smmv_eng_rt.json`.
Each carries `job.benched_by: "hgi_xp"` (a composition gate that does NOT exist yet in `composition_gates.json`), the M5
plan, outline, pin faces and clock targets (insertion <= 300 ps, spread <= 80 ps) under `_plan`, and a `_todo` list of
what depends on unwritten RTL. `ref_tile.py` has no stand-alone validator; the drafts were only checked as JSON with the
example's keys. `_plan` / `_todo` are not `ref_tile.py` keys and must be dropped or mapped before `gen`.

## 4. Assumed or unverified

- relay stages inside the slice between bank and face (decides the credit margin); bank latency is counted, not simulated;
- xl as its own read group; the read duty of other clients on the slice during a load (rate halves under contention);
- router x depends on wo_b (makes XD 128 free); w2 x depends on its slot's w1 / w3 + SU (not in the model at all);
- every stage count and the 66-stage spine: Manhattan estimates on the contract, no route, no GRT;
- weight / result buses sharing a column channel with the spine (cut C 0.30 to 0.65);
- T2 sinks and area (RTL not written); all std-cell areas (measured unit costs applied to counted flops, no synthesis);
- the free site south of the slice (checked against die slots only).

## Production compiler stacked image (2026-10-13)

`tools/hgi_sim/ds_native.py` emits one record per expert slot for w1 and w3. The `ffn.experts.w13` extent has 4,608 rows per expert and records index it with the router ID and the full expert stride. The shared expert has a corresponding fixed `ffn.shared_experts.w13.weight` extent. To make each die's 48 rows contiguous, the physical image orders `[w1 rank0 rows; w3 rank0 rows; w1 rank1 rows; w3 rank1 rows; ...]`. Manifest `row_order=tp96_w1_w3_shards` and `matrix_rows=2304` specify this mapping; `_wrows` supplies the checkpoint rows in that order to the simulator and image exporter. The checkpoint tensors keep their original names and contents.

Each die writes its 48 outputs at the beginning of that slot's g buffer. SwiGLU reads 24 gate rows at offset 0 and 24 up rows at offset 24. The remaining gather and w2 layout stays at its original global row offsets. Hazard writes name both original g/u regions, and record price provenance includes both original op IDs. The immutable prices are added.

`PYTHONPATH=tools python3 -m unittest hgi_sim.test_ds_stacked_experts -v` checks all 96 ranks, all seven slots, fused and unfused SwiGLU, wire descriptor roundtrip, indexed expert stride, checkpoint row mapping across shard boundaries, and mismatched-pair refusal. These tests do not replace full checkpoint bit-exact validation or physical qualification. The latency evidence under `results/rtl/tput_map_1011/hbm_smmv_xp/latency_1013` keeps flat and hardened-leaf measurements separate.
