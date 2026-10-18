# S81-DV bk units on the V rung (lane S81U-BK, 2026-10-17)

The units are `dsdv_bk_sel` (plan p4h `bk_sel`, column 4) and `dsdv_bk_col` (plan p4h `bk_col`, column 1). The RTL is in
`rtl/dsrom_sys/s81_dv/unit/bk/`.

## What they are
- p4h wires both units only through their column's 276-b V rung. So the old slab's four die lanes in, and its vd lane out,
  ride the rung as BK beats through the shared stop leaf `ot_dsdv_vstop`. `dsdv_bk_v.sv` defines the beat format and the
  CTL drain command.
- The select and collect logic is the unchanged closed tiles:
  - selector: `dsfd_selt_q2` x4 and `dsfd_selt_c`;
  - collector: `dsfd_colt_lane` x4 (RING) and `dsfd_colt_mrg`.
- The schedule is static:
  - no unit port carries a credit, ready or back-pressure signal;
  - egress leaves only in compiled drain windows (one CTL per window);
  - any violation is a sticky fault (the vstop slot collision, ingress protocol, buffer overflow or an overlapping window).
- The old ctrl endpoints (`_c` / `_c1`: the c_cmd / c_done job queue) are dropped.
- The quarter-tile and lane-tile credit loops of the closed tiles stay inside the unit. Each is a fixed registered hop,
  deterministic, and never visible on a port.

## Leaves

| Unit | Leaves | Outline (um) | Plan p4h |
|---|---|---|---|
| bk_sel | `dsdv_bksel_lq` (quarters 0/1; the same master, MX, holds quarters 2/3), `dsdv_bksel_lm` (vstop, vin, selt_c, vout) in the middle | 561.6 x 432 / 561.6 x 259.2 / 561.6 x 432 (stack 1,123 tall) | 4 x 680 x 721 (2,882 tall) |
| bk_col | one leaf `dsdv_bk_col` | 475.2 x 475.2 | 6 x 680 x 697 (4,179 tall) |

- **Collector content.** It is about 0.12 mm²: 10 macros and about 50k um² of std cells. That is 4% of the plan
  outline. Leaves split out of it would each fall under the 35% fill floor.
- **Selector leaf hops.** Each face carries 3,148 pins (5.6/um). Every bit is registered at both ends: these are the
  closed tiles' own pin flops.

## Benches
`rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh` runs the unchanged slab benches through the adapter
`tb_dsdv_bk_wrap.sv`, using the `OT_DSDV_BK` define in `tb_s81ph_sel` and `tb_s81ph_col`.

**What is checked**
- The selector is compared transaction by transaction against the native `ot_hdc_v41x_sel`, including replays.
- The collector is checked with the frame, order, DONE and image scoreboard.
- Every through beat of other units passes exactly 2 edges later.
- Egress appears only inside its windows.
- The unit fault pin stays 0.

**Variants**
- rung directions: mirrored (`mir`) or not;
- with or without XQ/XB and single-beat through traffic (`thru`);
- the fault cases.

**Results**

| Run | Selector | Collector |
|---|---|---|
| Golden | PASS in 4 variants (`sel_exact.txt`) | PASS in 4 variants and all 5 fault modes (`col_exact.txt`) |
| Mutants that FAIL | 1, 2, 3, 4 (`sel_mut*.txt`; mutant 3 is caught only with through traffic, since without it the late part 1 lands in the next window's free slot) | 1 (half swap), 3 (window overrun), 4 (egress half swap) |

- Collector mutant 2 (a single-beat word drops its type/tag) is not exercised by the collector, which has no
  single-beat words. The selector's headers use that path.
- The collector's fault mode 1 floods two lanes on opposite rung directions. One lane alone cannot outrun the merger,
  because one lane's V ingress is at most 1 word every 2 cycles.

## Open item for the S81-DV lead: rate
- **Selector.** The 276-b rung gives the selector at most one 16-score beat per cycle (2 V beats per score word,
  both directions full). The native slab takes four, so this is 1/4 of the slab's ingest.
- **Collector.** One 512-b word every 2 cycles, which equals its old PACE-2 output.
- If the selector's priced rate needs more, the scores must reach bk_sel on a wider port, or the local top-k moves
  beside the regional svc slices. This needs a plan decision.
