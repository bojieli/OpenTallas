# MESO-INTEG-1: count-aligned ring integration (shared, all 5 dies; opt-in until final adoption)

Lane MESO-INTEG-1 (COORD 12.14). Base: origin/main@20ad990030, which contains claude/meso-count-1027@258bc16208.
The old ring (`ot_dp_clk_landing`, OFFSET 2 + RDREG = 3 cycles) stays the DEFAULT everywhere. The count-aligned form
switches on only when a regions table has a `count_aligned` block, written by `count_align_bind.py --table`.
No credits and no backpressure: the 10-14 static schedule stays.

## What is built
1. **Wrapper swap (opt-in):** `clock_landings.py`. When the table has `count_aligned`, the landed rows instantiate
   `ot_dp_clk_landing_ca #(.W, .DEPTH, .K)` with per-crossing DEPTH and K from the bind.
   - Each region gets one origin: the root gets `ot_dp_landing_root #(.SETTLE)`, and every child gets
     `ot_dp_landing_origin #(.PAD, .EDGE_FALL)`, which syncs the parent's start forwarded on the tree port's bus
     (`cland_fstart_out_<bus>` -> `cland_fstart_in_<bus>`).
   - Ring wiring: `t_rst_n` = sender start, `rst_n` = receiver start.
   - The fault output goes to the same per-bus observer/status path as the old ring. `clock_landing_verify.py` checks
     the CA ring, origin and root wiring, with 5 mutants.
   - `clock_landing_plan.py` gives the CA pins and ports.
   - Fails closed in three cases: a missing K, a region with more than one landed partition, or a type whose copies
     need different K/DEPTH/origin role (error "count-aligned landing TYPE_SPLIT required").
   - `rtl/common/ot_dp_clk_landing_ca.sv` adds `ot_dp_landing_root`.
2. **Start tree and loops:** `count_align_plan.py` and the new `count_align_bind.py`.
   - The plan grows a directed start tree from the region crossings: each tree port runs parent -> child, and a
     reversed tree port is refused.
   - Tree crossing latency comes from the real sync window; `tree_shift` absorbs wander.
   - The bind computes per-crossing K, DEPTH and `sched_lat` = K+1+n_dst-n_src, plus the per-region origin
     (parent, port, edge, PAD).
   - It checks the identity on every crossing and that every fundamental loop closes:
     sum(sched_lat) = sum(K+1), so K is consistent around loops.
   - A physical start-up Monte-Carlo draws tree phases, non-tree d over the derated interval, and wander.
3. **Pricing:** `annotate_table` writes per-crossing `added_cycles = sched_lat`.
   - `clock_landings.network_lane_cycles` accepts `data_cycles_per_crossing = "count_aligned"`.
   - `s81_head/fallback_land.head_pass` weights each lane by its own cycles.
   - `kv_ca_price.py` reprices the KV v39r lane-class model.
4. **Shared die STA:** `die_sta_related.py --count-align BIND.json` (opt-in, main model, no fork).
   - Landed pairs are judged on the ring lag window. Non-tree L is re-derived from the STA's own derated arrivals.
     Tree L comes from the plan sync window.
   - COORD rule: at least 100 ps inside [T/2+T/8, (DEPTH-1/2)T-T/8].
   - A crossing without taps fails.
   - slot->read = L_lo - T/2 >= T/8, so the existing landing_contract half-period slot->RDREG SDC holds.
   - The default ±T/2 gate is unchanged and is kept as INFO.
5. **Bench:** `bench/run_loop_bench.sh`.
   - It generates die-style wiring for 5 regions and 11 crossings with 7 fundamental loops (root, origins, rings,
     registered forwarded start), runs Verilator lint, and runs 200 chips. Each chip draws random phases inside the
     derated d and random raw-reset release times.
   - Every crossing must show no fault, be ready, and give q == word(c-K).

## Finding: tree K was off by one for the real wiring (fixed here)
In the die wiring, the forwarded start is the parent origin's register output. It rises right after parent edge e,
while the parent's rings write word 0 at edge e+1. MESO-COUNT-1's tb_ca_tree drove p_start at the word-0 edge.

With the MESO constants (K_tree = -2-PAD), the loop bench gives these lags:
- tree crossings L = 0.23-0.40 T (window starts at 0.5 T)
- loop-closing er L = -0.19 T
- result: ready never rises, plus a fault

The bind now uses K_tree = -1-PAD and an origin step one count shorter (`LAUNCH = 1`). The physical lag and `sched_lat`
are unchanged. Bench: 200 chips x 11 crossings, 782,183 word checks, 0 bad. Lint clean.

The formal PDR proof and the NUMBER-CHECK should use this convention, or prove the tb_ca_tree convention matches the
die wiring.

## Numbers (own tool runs; NOT independently NUMBER-CHECKed)
| | HEAD3 (LAND-HEAD-3 sfbR) | KV (land-kv-1027 lpo) |
|---|---|---|
| regions / tree edges clean | 326 / 325 of 325 | 160 / 152 of 159 |
| crossings D4 / D8 / FAIL | 427 / 0 / 0 | 3398 / 517 / 0 |
| sched_lat hist | {2:217, 3:210} | {2:2426, 3:989, 4:363, 5:137} |
| total cycles CA vs old ring | 1064 vs 1281 | 9956 vs 11745 |
| fundamental loops, identity errors | 102, 0 | 3756, 0 |
| start-up sim 2000 chips: violations | 0 | 0 |
| min margin low / high (to ap-inset edges; COORD margin = +104) | 179.4 / 787.2 ps | 105.6 / 168.9 ps |
| K range, max origin count | [-2, 62], 78 | [-34, 41], 92 |

MESO-COUNT-1 reported HEAD3 {2:349, 3:78} = 932. That figure under-stated tree latency by one cycle on 132 crossings
because it used the window [c, c+T) instead of the sync boundary.

TOK (UNCHECKED):
- **HEAD:** a head pass over 37 crossings goes from +111 to +91 cycles, and the gather round trip from 60 to 48.
  The total goes from +171 to +139 cycles, giving 9,421 against the 10,357 window (slack 936, was 904).
- **KV (v39r lane-class):**
  - Per request: 66 -> 62.
  - Embed: 123 -> 112.
  - Added: 2499 -> 2344 cycles.
  - Throughput: 4763.2 -> 4766.2 tok/s.
  - 208 lanes are slower than 3 cycles per crossing (up to 5). The interior families (vport/pv/ahub/seq/acal) are not
    priced, as in the source.

## Open
- TYPE_SPLIT: per-instance K differs between copies of the same type. Under CA, this needs either type splits or
  per-instance parameters. HEAD/KV variant counts have not been computed.
- KV multi-partition regions (128 groups): an intra-region start distribution is needed. It is not built; the binder
  errors fail closed.
- The root SETTLE must cover the die's raw-reset wavefront spread (default 64).
- Fall-edge tree origins are not exercised by the loop bench (all rise in this graph); tb_ca_tree covers the sync alone.
- `die_sta_related --count-align` has unit tests only. It has not run on a real die proof yet.

Files: `kv_ca_price.{py,json}`, `bind/{head3,kv}_bind{,_summary}.json`, `bench/`.

## Intra-region start relay (DIE-KV-3/CAORIGIN, 2026-10-27 22:0x; COORD 21:14 ASK 3)
COORD accepted "one origin per region + start relay to its partitions as a timed ctl pin". This section builds it. It
is opt-in: it switches on only when the bind gets partition endpoints (`count_align_bind.py --table`, or `--parts ocv`).
Without them, the bind output is byte-identical to MESO-INTEG-1 (loop bench `single`: `loop_bind.json` identical).

- **Origin choice (deterministic).** A child region's origin is the partition that its start-tree port lands in. The
  root region's origin is the partition that sends the most child tree ports; ties go to the most landed crossings,
  then to the first name. Every other landed partition of the region is a **relay**.
- **Hardware.** The relay is `ot_dp_landing_relay`: one flop with a synchronous raw-reset clear, on the region clock.
  - The origin partition has `u_cland_rstart_tx` (d = origin start), which drives `cland_rstart_out`.
  - The die net `clock_landing_rstart_<origin>` carries it to `cland_rstart_in` of every relay partition.
  - In each relay partition, `u_cland_rstart_rx` produces that partition's `cland_start`.
  - This gives r = `RELAY_STAGES` = 2 counts. The path is a same-clock registered ctl edge (`cland_relay__<part>` in
    `landing_network.edges`, registered at both ends), timed by the die STA as an intra-region related pair. It is not
    a landed crossing.
- **Count frames (derived in `bind_parts`).** Each landed partition q counts from its own start N_q.
  - Child origin: N = N_sender + m + SYNC - 1 - LAUNCH + PAD. The tree port's sender may be a relay, so a region
    origin also moves by r for each relayed tree sender on its path.
  - Relay: N_q = N_origin + r.
  - Ring lag: L = (K + N_d - N_s) T + d.
  - Tree port: K = K_tree + tree_shift (unchanged).
  - Other crossings: K = sched_lat - 1 - (N_d - N_s).
  - `sched_lat` is the absolute latency the schedule and TOK use. It is unchanged, and q == word_s(c - K) still holds
    in the receiver partition's counts.
- **Loops.** The start spanning tree is over partitions: tree ports plus relay edges. A relay edge is (sched_lat r,
  K+1 = 0), because it moves the count origin by r. Every non-tree crossing closes one loop, and the identity
  sum(sched_lat) = sum(K+1) must hold on every loop. The physical start-up MC now also draws the origins per partition.
- **Wiring.** `clock_landings.py` emits the tx/rx flops and the pins, and checks that the bind roles match the regions.
  A multi-partition region with no bind `parts` still fails closed. `TYPE_SPLIT` now includes the origin/relay role
  and the tx flag.
- **Plan.** `clock_landing_plan.py` adds the pins: a `cland_rstart_out/in` scalar ctl beside the first landed bus
  (the tree bus for an origin). It also adds the `cland_relay__*` ctl ports, and the cohort signature includes the
  relay role.
- **Verify.** `clock_landing_verify.py` checks rx.d == tx.q, tx.d == origin start, the clocks and raw resets, ring
  t_rst_n/rst_n against each partition's start, and that p_start comes from the tree port's sender partition. It
  adds 3 mutants (skip tx, ring on the origin start, no bind roles).

### Numbers (own runs, intel1 docker; CHECKED-own, not independently NUMBER-CHECKed)
- **Tests:** 93 (`tools/die_plan`: clock_landing*, count_align*, die_sta_related) + 7 (fallback_land) PASS. 9 tests
  are new.
- **Loop bench `multi`** (`run_loop_bench.sh OUT 200 multi`):
  - Graph: 5 regions, 9 partitions (regions with 2, 2 and 3 partitions), 17 crossings, 13 loops.
  - Coverage: 2 tree ports sent from a relay partition, 6 crossings with a relayed receiver, 6 with a relayed sender.
  - Result: lint clean; 200 chips, 1,203,219 word checks, **0 bad**.
  - Negative control (`mutant_noshift`, region-frame K with the relay offset ignored): 20/20 chips bad.
  - Bench `single`: unchanged (782,183 checks, 0 bad).
- **KV land128 bind:**
  - Inputs: `die-kv-3-1027/base/L128fish_xing_lpo.json` (byte-identical to `die-kv-2-1027/L128_xing_lpo.json`),
    `l128_table.json`, and `landed_l128_plan.json`; see `caorigin/kv_l128_bind_summary.json`.
  - Size: 128 regions, 160 landed partitions, 3595 crossings (D4 3505 / D8 90 / FAIL 0).
  - **Multi-partition regions: 32 (all 2-partition: phy/pc pairs, 950 um centre to centre)**. 96 regions have a single
    partition.
  - Relays: 32 relay partitions. Relay pins: 32 tx_out + 32 rx_in, with 32 `cland_relay` ctl edges.
  - 130 crossings have a relayed receiver and 120 a relayed sender. 3 tree ports are sent from a relay. 151 non-tree
    K values shift.
  - Rc 0. **Identity/loop errors 0** on 3468 fundamental loops.
  - Start-up MC: 2000 chips, 0 window violations, min margin low/high 104.4 / 341.7 ps.
  - The binder no longer fails closed on multi-partition regions.
- **TYPE_SPLIT** (`caorigin/kv_l128_typesplit.json`, `Landings` with no RTL): 20 of 60 landed types need a split, giving
  119 variants. Per-instance K/DEPTH alone already gives 117. The origin/relay role adds 2 variants (6 types differ in
  role, and those are already split by K). TYPE_SPLIT still fails closed; resolving it is the remaining open item
  (type splits or per-instance K parameters).

### sched_lat <= 0 and >= 9 on KV land128 (parent's question): not the relabel, not a bind bug
The `sched_lat` histogram from this partition-frame bind is identical to the region-only bind:
- {-4:2, -3:28, -2:2, -1:8, 0:7, 1:161, 2:1347, 3:1920, 4:34, 5:30, 6:23, 7:1, 9:1, 10:16, 11:15}
- total 9276 vs old ring 10785.

`sched_lat` does not depend on origins or relays. It is a count-frame latency: sched_lat = 1 + (L - d)/T, within 0.5
on every crossing. The 79 extreme crossings are all non-tree. Only 1 touches a relay partition.

They are the pairs whose measured region clock phase differs by 6-8 periods. Examples:
- pv_N_7 -> hgi_EN_7: d = +6.5 ns, sched_lat -4
- phy_EN_7 -> hroot_EN: d = -5.7 ns, sched_lat 11
- hroot_EN -> phy_EN_7: -3

In total, 139 crossings have |d| > 2T. The physical lag of these crossings is a normal L of about 2.2-2.4 ns. A
round trip sums to the physical value (11 + -3 = 8), so loops and token loops are exact.

Open-lane sums of `sched_lat` include the endpoint regions' phase offset. That is correct in each region's own count
frame, but it is not a physical time.
