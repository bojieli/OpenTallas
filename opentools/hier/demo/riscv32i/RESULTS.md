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

---

# OSS-HIER-2 update (2026-10-27 20:40-21:40 PDT): root cause of the +340 ps, registered map, context, top DRT

All numbers below were measured by this lane. They are **UNCHECKED** (no independent NUMBER-CHECK).
Run data is in the same directory: `sta3tt/`, `gen4/ work4/ sta4/ sta4tt/` (registered map with context),
`gen4n/ work4n/ sta4ntt/` (registered map, no context), and `gen5/ work5/ work5_flat/` (TC rebuild, see the end).

## Root cause of the +340 ps: a library-corner mismatch, not the boundary crossings

The ORFS asap7 platform defaults to `CORNER ?= BC`, which selects the FF libraries. ohier did not set a corner, so the
following were all built and characterised with FF libraries:

- every partition, the top and the flat baseline;
- every `generate_abstract` ETM. Its log shows `read_liberty ..._FF_nldm...`.

The hierarchical STA reads TT libraries. As a result, the ETM view compared an FF model against TT netlists.

Measured case: in `gen4`, the RCORE block-only TT STA gives an arrival at the `dataadr_5_` port of 1105.6 ps. The arcs
for the same path compare as follows:

| ETM | clk->dataadr_5_ fall arc |
|---|---|
| FF `_typ.lib` | 806 ps |
| TT re-characterisation (`scripts/etm_tt.sh`, same routed block, same SDC/SPEF, TT libs) | 1106 ps |

Fixes:

- `emit.CORNER = "TC"` is now written into every block, top and flat `config.mk`.
- `ohier abstract` and `ohier sta-scripts` take `--etm-suffix`. It is `typ` for new runs; use `TT` for the re-characterised
  old runs.

The ETM clock insertion in the shared plan was also FF. The TT values for `gen4` are RMEM 58/84 ps and RCORE 83/110 ps
(min/max).

## (1) Flat baseline vs stitched vs ETM (TT STA, all FF-built implementations)

| run | map | flat WNS | stitched WNS | ETM WNS (TT model) | flat-stitched endpoint mean / max (ps) |
|---|---|---|---|---|---|
| gen3 (top SPEF from GRT) | 3 regions, 5 comb crossings/cycle | -378.8 | -669.9 | -642.7 | -223.1 / 340.3 (r 0.987) |
| gen4n (top routed) | 2 regions, SRAM boundary, no context | -378.8 | -476.6 | -469.4 | -71.2 / 139.0 (r 0.993) |
| gen4 (top routed) | 2 regions, SRAM boundary, context | -378.8 | -487.7 | -515.1 | -83.4 / 157.0 (r 0.994) |

- Hold WNS is about +47 ps in flat and in stitched for all three runs.
- The registered map cuts the hierarchy penalty against flat from 223 to 71-83 ps (mean over 1355 common endpoints).
- The worst stitched path in gen4/gen4n is inside RCORE: pcreg -> boot ROM -> decode -> ALU -> dataadr. It does not cross
  a boundary. Part of the remaining flat-to-stitched gap is therefore partition QoR against first-pass budgets, not a
  boundary effect.

## (2) and (3): abstract error, per partition boundary pin, stitched vs ETM

Each row uses the worst slack through each of the common boundary data pins. "+" means the ETM is optimistic.

| run | setup mean / max abs / p95 (ps) | setup r | hold mean / max abs (ps) | hold r |
|---|---|---|---|---|
| gen3, FF ETM (OSS-HIER-1 number) | +340.4 / 437.4 / 432.5 | 0.9988 | -14.2 / 197.7 | 0.57 |
| gen3, TT ETM, 5 crossings/cycle | **+22.2 / 52.1 / 38.4** | 0.9999 | +89.4 / 281.4 | 0.63 |
| gen4n, TT ETM, <=1 SRAM crossing, no context | **+9.1 / 19.0 / 15.7** | 0.9999 | +176.1 / 515.7 | 0.26 |
| gen4, TT ETM, <=1 SRAM crossing, context | **-12.1 / 36.9 / 31.8** | 0.9997 | +190.9 / 538.3 | 0.33 |

Register-endpoint view, stitched vs ETM over the 99 common endpoints:

- setup: mean +3.9 ps, max 4.7 (gen4) and 5.8 (gen4n);
- hold: mean +227 ps.

Findings:

- **Setup.** The TT ETM is accurate to <= 19 ps on the registered map and 52 ps with 5 comb crossings. The error still grows
  with crossings per cycle, as OSS-HIER-1 expected, but it was 22 ps, not 340.
  - The prototype map is not strictly 12.13c. `dmem`'s byte/word read mux in RMEM uses the current address, so
    `dataadr -> RMEM glue -> readdata -> RCORE` is a 2-crossing combinational path. The worst stitched boundary path
    (-487.7, through `dataadr_31_` and `readdata_7_`) is that path.
- **(3) Drive/load context** (`set_driving_cell` = real driver leaf, `set_load` = far-side pin caps + 0.2 fF/um top wire)
  makes the TT ETM **21 ps more pessimistic** (+9.1 -> -12.1 mean). It does not improve accuracy. These ETMs index only
  the output load (OpenSTA `write_timing_model`), so the driver cell delay in the block SDC is counted again at the top.
  Context stays on by default because it is the conservative side and is industry practice for block constraints.
  `--no-context` reproduces the closer number.
- **Hold: the ETM cannot be used per pin.** OpenSTA `write_timing_model` writes one (max) table per arc, so the min
  analysis reuses max delays. Example: the gen4n path through `dataadr_28_` has stitched hold slack 336 ps. In the ETM
  view the worst min path is an `instr` -> `dataadr` arc of 695 ps, giving 851.6 ps. Hold must be signed off on the
  stitched (or flat) view. A min-delay ETM is open work. The worst-pin hold slack still agrees by chance (within 5 ps).

## (4) Top detailed route: FIXED

- OSS-HIER-1's top log showed `DRT-0418 Term u_riscv_top_RRF/clk has no pins on routing grid` before DRT-0255. The
  region corners were snapped to 1.08 um. With 1.08, a slot at x = 5.4 um puts every M5 partition pin 0.024 um off the
  top's M5 tracks (pitch 0.048, offset 0.012).
- Region corners now snap to `grid_um = 2.16` = lcm(1.08 row/site grid, 0.048 M4/M5 pin pitch).
- Result: in gen4 and gen4n the top detailed route finishes with 0 violations and 0 DRT-0418. The STA above uses the
  routed top SPEF.
- Caveat: gen4 also has a different map than gen3. The grid is the cause shown by the DRT-0418 term, but the 3-region
  map was not rerun with the new grid.

## Live at lane end: gen5 = gen4 plan built at CORNER=TC (hier blocks+top and flat)

These are the first apples-to-apples TT implementations. When they finish, collect:

```
ohier abstract --gen gen5 --work work5 --nick riscv32i_ohier
ohier sta-scripts --gen gen5 --work work5 --flat-work work5_flat --nick riscv32i_ohier --lib "$B/libs/*.lib" --out sta5
scripts/sta_run.sh sta5 $B $H
ohier compare --gen gen5 --sta-dir sta5 --out sta5/compare.json
```

## (5) A real die region as a partition: NOT BUILT, estimate only (12.14b)

- The HEAD 27-region connectivity map (LAND-HEAD-3) groups 326 partitions, about 12 hard cores per region. At ASAP7, about
  400k cells fill about 0.10-0.14 mm² (owner cap memory). A HEAD region flattened into one partition is therefore about
  10x over the 400k OpenROAD cap.
- The feasible form is macro-aware: the region partition holds its member hard cores as BLOCK macros (signed-off
  LEF + ETM) plus the region glue and clock, and ohier only flattens the glue. ohier already treats LEF CLASS BLOCK
  leaves as macros (as with the SRAMs here).
- Inputs needed:
  - the region netlist (`gen_rtl` with the member cores as black boxes);
  - per-core LEF/ETM at TT;
  - the region rectangle from `locality.py`.
- With TT ETMs and hold on the stitched view (above), the method is ready. Next lane: one small QC-slice sub-region
  (2-4 cores) end to end.

### gen5 hier collected (21:56 PDT): the registered map with context, built at CORNER=TC

The abstract log reads the TT libraries.

- **Top detailed route:** 0 violations, 0 DRT-0418.
- **Abstract check:** PASS for both partitions. TT clock insertion is RMEM 62/87 ps and RCORE 84/113 ps (min/max).
- **WNS:** stitched -500.0 ps setup and +46.9 ps hold; the native ETM view gives -518.8 ps setup.
- **Boundary-pin setup error of the native ETM:** -15.7 ps mean, 40.3 ps max, r 0.9998. This matches the re-characterised
  gen4 result (-12.1 / 36.9), so the corner fix is confirmed.
- **Hold:** still optimistic, +190 ps mean.
- **Register endpoints, setup:** stitched vs ETM mean 3.9 ps, max 5.3 ps.
- **Stitched WNS did not improve with the TT build** (-500.0 vs -487.7). The worst path is internal to RCORE. Partition QoR
  against the first-pass budgets is the next lever: a re-budget loop.

The TC flat baseline (`work5_flat`, container `ohier_flat_3302759`) was still running at lane end. Collect it with the
recipe above using `--flat-work work5_flat`.
