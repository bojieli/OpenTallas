# Qwen reduced matvec tile: pin geometry trial

This trial uses the **same adopted matvec RTL**, modeled ROM/SRAM macros,
1.5 ns clock, 0.32 ns max transition, and 45% slew repair margin as the
completed route in `physical.json`. It changes only IO placement constraints
for `kv_load_data[220]`, `kv_load_data[251]`, and `x_load_addr[7]`.

## Why the previous explicit-buffer trials stopped at CTS

The three source-pinned BUFx24 trials in `attempt_isolation*_cts_failure.json`
stop after CTS hold repair. Their residual overlaps are BUFx2 `hold*` cells:
four at 15% utilization, one at 12%, and five at 10% with cluster size 12.
The 15% trial also overlaps a repaired input cell and a wire buffer with hold
cells. This is a **local detailed-placement legalization failure** (`DPL-0033`),
not evidence of global standard-cell density closure. Reducing the utilization
alone did not eliminate it. The completed 45% margin route has 11,416 final
`hold*` instances; its reproduced source-identical CTS checkpoint has 11,400
hold buffers, 17 hold violations under placement-estimated parasitics, and zero
placement violations. Global-route timing repair subsequently clears hold in
the completed route.

The completed route's final netlist drives the two failing KV macro inputs
through BUFx2 hold chains. A representative clock endpoint in `6_finish.rpt`
has clock arrival at about 2.02 ns. Together these observations explain why
input-to-macro minimum paths need many inserted delay cells. They do not prove
that every overlap is on one of the four original max-slew nets.

## Geometry and controlled change

The source-identical baseline was rerun through CTS with a retained OpenROAD
database. In its macro-placement checkpoint, `g_bank[0].u_kv` spans
`x=7.052–181.796 µm, y=452.544–523.014 µm`. In its IO placement checkpoint,
the `kv_load_data[220]` and `[251]` pins are on the bottom edge at
`(175.776, 0)` and `(174.720, 0)` µm, respectively. Their vertical separation
from the target SRAM is over 452 µm. The completed route's remaining KV slew
violations are 351.85 ps and 327.34 ps against 320 ps.

The controlled route pins those two inputs to the left edge within
`y=450–530 µm`, the macro's vertical span. It constrains `x_load_addr[7]` to
the left edge within `y=0–80 µm`, next to its vector SRAM, and `o_data[179]`
to the left edge within `y=320–360 µm`, near its producing flop at about
`(146, 342) µm`. A preliminary right-edge placement was discarded before
routing after it placed the output at `x=694 µm`, increasing that output's wire
distance. An unbounded left-edge trial was also stopped before routing after
the IO placer put the KV inputs at `y≈131 µm`, still far from the target macro.
No metrics from those discarded placements support a closure claim.

The constrained IO-placement checkpoint puts the KV pins at
`(0, 450.144)` and `(0, 450.240)` µm, the vector address at
`(0, 29.472)` µm, and the output at `(0, 320.064)` µm. The corresponding
baseline pins were `(175.776, 0)`, `(174.720, 0)`, `(0, 45.408)`, and
`(0, 328.992)` µm. These are OpenROAD BTerm box lower-left coordinates,
read from source-retained `3_2_place_iop.odb` files at 1,000 DBU/µm.

## Reproduction and outcome

Baseline CTS:

```sh
tools/run_hdc_matvec_memory_tile.sh --max-transition-ns --slew-margin-percent 45 \
  --pnr-stop-after cts --keep-workdir /tmp/ot-qwen-cts-base \
  --output results/physical_hdc/asap7/matvec_memory_tile/cts_baseline_diag.json --force
```

Constrained full route:

```sh
tools/run_hdc_matvec_memory_tile.sh --max-transition-ns --slew-margin-percent 45 \
  --pin-region '^kv_load_data\[(220|251)\]$=left:450-530' \
  --pin-region '^x_load_addr\[7\]$=left:0-80' \
  --pin-region '^o_data\[179\]$=left:320-360' \
  --keep-workdir /tmp/ot-qwen-pinprecise \
  --output results/physical_hdc/asap7/matvec_memory_tile/pinprecise.json \
  --nickname-tag hdc_mem_tile_pinprecise --force
```

Baseline CTS `config.mk` SHA256:
`a475e5edfb0ed5949ca521d2c4978c3fc420eecd66aa7303a63720cd08266d4c`.
Baseline `constraint.sdc` SHA256:
`761642202ad4bae185cdf17cdcdb66ef7a5494f91df58452e5cf817f9b5d88f6`.
The constrained run has the **same SDC SHA256**. Its `config.mk` SHA256 is
`af513bab74631c206aab47fa33887efa9ed59fa9ece45a4e94f2090b2d151408`;
its bounded `io_constraints.tcl` SHA256 is
`5685ac0f604db2642bd3fb284c6468a85b698f3830358fc6b2d93b9d2467175c`.
The generic driver extension that records and emits bounded edge ranges is
commit `969a209d`. The completed route record is from commit `8f9b83fa` and
the reproduced CTS checkpoint is from `fcb12397`. All 11 named RTL and macro
blackbox source hashes match across the baseline and constrained records.

## Measured result: CTS legalization failed

| Observation | Source-identical baseline CTS | Bounded-pin trial |
| --- | ---: | ---: |
| Hold-violating endpoints found by `repair_timing` | 2,137 | 3,178 |
| BUFx2 hold buffers inserted | 11,400 | 18,445 |
| Post-CTS placement overlaps | 0 | 10 |
| CTS checkpoint | Completed | `DPL-0033`; no routed result |

The bounded pins reduce the physical distance to the macro but also shorten
the input-to-macro minimum paths. CTS inserted **7,045 additional hold
buffers** (61.8% more) and the detailed placer could not legalize them. The
ten final overlaps consist of three hold/hold pairs and seven wire-buffer/
hold-buffer pairs; the full source-pinned failure tail is in `pinprecise.json`.
The geometry change therefore does not close this reduced tile. It provides
no extracted slew, setup, hold, DRC, or antenna result. The completed baseline
route still has four max-slew violations and remains **NOT_MET**.

This result points to the short minimum paths and CTS hold-repair load as the
next physical issue to solve. A clock-tree or input-minimum-path change would
need its own matched SDC and routed acceptance evidence; pin proximity alone
cannot be counted as a fix. All evidence here is limited to the W4/G2 reduced
ASAP7 tile with model-grade memory macro LEF/Liberty, not a full Qwen core or
manufacturable macro.
