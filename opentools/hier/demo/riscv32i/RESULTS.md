# ohier demo results: ORFS asap7/riscv32i, 3 map regions (2026-10-27, OSS-HIER-1)

All numbers are measured by this lane and NOT independently checked: **UNCHECKED**.
Run data: `intel2:/srv/opentallas-scratch2/claude/oss-hier-1027/demo` (`gen3/`, `work3/`,
`work3_flat/`, `sta3/`). Clock 950 ps, TT RVT, OpenROAD/ORFS image `openroad/orfs:asap7lock`.

## Region map -> partitions (`region_map.json`, `ohier plan --region-map`)

| region | partition | members | cells | slot (um) | ports | ETM clock insertion min/max (ps) |
|---|---|---|---|---|---|---|
| R_MEM | riscv_top_RMEM | dmem (4 x fakeram7_256x32) | 174 | 89.64 x 57.24 | 100 | 43.7 / 48.9 |
| R_RF  | riscv_top_RRF  | riscv.dp.rf | 6417 | 47.52 x 37.80 | 113 | 67.0 / 87.1 |
| R_EX  | riscv_top_REX  | riscv, pcmux, boot (+2 glue items) | 3247 | 37.80 x 37.80 | 276 | 38.7 / 43.1 |

- 9838 leaf cells, 209 crossing bits (R_MEM-R_EX 97, R_RF-R_EX 112, R_MEM-R_RF 0).
- `ohier verify`: partitioned netlist structurally equivalent to the input (9838 leaves, 10165 nets, 0 differences).
- All 3 partitions routed and abstracted (ORFS `generate_abstract`); `ohier abstract`: LEF size == slot,
  LEF pins == ETM pins == plan ports for all 3 (PASS). Block-level worst setup slack against their budgets:
  RMEM -93.7, RRF -149.4, REX -156.5 ps (the budgets are first-pass; no re-budget loop yet).

## Top assembly

Placement, CTS and global route of the top on the 3 abstracts PASS (die 100.44 x 110.16 um);
**detail route FAILED** (DRT-0255: no access path for clock leaf net to the R_RF clock pin at
(50.15, 66.99) um, M4). Top parasitics for STA are therefore the global-route estimate
(`scripts/grt_spef.sh`, `estimate_parasitics -global_routing`, 452 top nets); the partitions use
their detailed-route SPEF.

## Hierarchical STA: stitched (flat STA of the hierarchical implementation) vs ETM abstracts

Same top netlist + top SPEF + design SDC in both views; stitched = full partition netlists + SPEF
(`read_spef -path`), etm = partitions as ETM liberty cells.

| | stitched | etm |
|---|---|---|
| WNS setup (ps) | -669.9 | -240.2 |
| TNS setup (ns) | -675.6 | -8.7 |
| WNS hold (ps) | +47.2 | +183.8 |

Worst slack through each of the 484 partition boundary data pins (common to both views):

| check | pearson r | mean diff etm-stitched (ps) | max abs diff (ps) | p95 abs (ps) |
|---|---|---|---|---|
| setup | 0.9988 | +340.4 | 437.4 | 432.5 |
| hold  | 0.569  | -14.2 | 197.7 | 177.3 |

**Verdict: the ETM view is NOT accurate enough for sign-off on this cut; it is optimistic by ~340 ps
on setup.** Diagnosis (measured on the worst path): the critical paths cross partition boundaries
5 times in one cycle (REX clk->rs1 -> RRF read mux -> REX address -> RMEM -> REX -> RRF write),
because the demo map splits the register file from its datapath with combinational crossings.
Each ETM arc is characterised in the block's own boundary context (scalar arcs, no input-slew
index), so a small per-arc error is summed 5 times. Under METHODOLOGY 12.13c every region crossing
is a registered hop, so production paths cross at most one boundary per cycle; that case is not yet
measured here.

## Flat baseline

`work3_flat` (same 9838 cells, same die) was still in detail route at the end of the lane; collect
`work3_flat/results/asap7/riscv32i_ohier_flat/base/6_final.{v,spef}` and rerun
`ohier sta-scripts ... --top-v sta3/top_grt.v --top-spef sta3/top_grt.spef` + `scripts/sta_run.sh` +
`ohier compare` for the flat-vs-stitched endpoint numbers.

## Next steps

1. Region map with registered crossings only (12.13c) and re-measure ETM vs stitched.
2. Budget SDC with `set_driving_cell`/`set_load` from the top context so ETM arcs see real slews.
3. Clock-pin access: keep the partition clock pin off the PDN-ring corner, or let the top route
   the clock on M5+ (DRT-0255 above).
