# Opt-in rooted KP4 Chien constant-linear implementation

The original decoder computes thousands of constant GF powers inside procedural
Chien loops. Its existing census is still running and was not stopped or
restarted. This candidate exposes those constant operations as real combinational
XOR wiring, as already done for this link's encoder and syndrome logic.

`tools/hbm_io/gen_chien_linear.py` derives constants using GF(2^10), polynomial
x^10+x^3+1. It refuses a changed original decoder hash. It generates a separately
named decoder, map, and static-window wrapper, leaving the existing decoder,
wrapper, numerical proof and live census inputs unchanged. The provenance JSON
pins the source decoder, GF helper, wrapper, generator and generated outputs.

The map takes 470 register bits: 16 Lambda coefficients, 30 Omega coefficients,
and X. It supplies 55 groups of {Lambda evaluation, Omega evaluation, odd-Lambda
evaluation, X} and the 47 register values for the next 55-symbol slice. Constant
multiplication is expressed as bit XORs; shared Lambda products serve both Lambda
and odd-Lambda evaluations. BM arithmetic, GF inverse's actual 1024-entry case,
Forney arithmetic, MUT2 behavior, state, resets, eight decoder clock inputs and
all cycle boundaries are retained. This introduces no pipeline stages.

## Validation

Commands are relative to the checkout and run under fleet `ot-run` admission:

```
python3 tools/hbm_io/gen_chien_linear.py
python3 tools/hbm_io/audit_chien_linear.py rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_chien55_map.sv
bash tools/hbm_io/run_chien_linear.sh OUT/basis basis
bash tools/hbm_io/run_chien_linear.sh OUT/map_mutant gate-mutant
bash tools/hbm_io/run_chien_linear.sh OUT/fec_positive 0
bash tools/hbm_io/run_chien_linear.sh OUT/fec_forney_mutant 2
yosys -s tools/hbm_io/chien_linear_map.ys
```

An independent emitted-equation audit uses carryless polynomial multiplication
and reduction, rather than the generator algorithm. All 2,670 exact output
linear forms pass over 470 input bits (1,254,900 basis/output checks); an actual
generated-wire substitution is rejected. The generator also reproduces all four
outputs byte for byte.

The map bench compares the actual generated wiring with the original SV GF
functions for all 470 input basis vectors, zero and 64 deterministic random
vectors. All 2,670 output bits are checked on each vector. The map mutant inverts
an actual generated XOR input wire and must fail. FEC tests use the existing
actual encoder, corrected PMA channel, decoder, finite CDC and 2048-word fixed
window bench. Forney MUT2 must fail numerically.

The isolated map completed Yosys 0.68 and ABC: 49,211 XOR and 692 NOT cells,
720.96 MB peak memory, 37.38 seconds. `mapping_counts.json` records exact output
netlist hashes and counts. These are generic mapped gates, not library area.
The generic netlist has maximum evaluation depth 12 gates and next-slice depth 7,
with maximum input internal fanout 75; these are structural counts, not timing.
No map state or memory was introduced. Full FEC positive passes with age 102;
the actual Forney mutant is rejected at cycle 302, age 102. Both direct map SV tests are terminal: all basis/zero/random vectors pass, and
the actual generated-wire inversion is rejected at vector 0, k=0. All five
admitted runners completed with status zero (negative-test runners require
the expected nonzero simulation and exact failure diagnostic).

## Limits and next work

This proves combinational-map feasibility and numerical preservation for the
exercised complete FEC path. The full generic synthesis/check subsequently passed as recorded below. Physical
clock delivery, library timing, routing, area, and the final production schedule
remain unqualified.
In particular, BM and Forney still contain real variable GF multipliers and
inverse tables. The 49k XOR helper itself still needs a real placement/timing
budget. No old route, price or physical CLOSED marker transfers to this candidate.

Remote preserved proof: `/srv/opentallas-scratch/codex/fec-chien-linear-1015` on
`ot-epyc4`. Original live census is a separate source tree and process.

## Full candidate clock census

`tools/hbm_io/run_chien_linear_census.py --out NEW_OUT` is the source-pinned
full-composition sizing runner. It uses the opt-in wrapper and actual static CDC,
explicit EMUT=DMUT=0, WINDOW_WORDS=2048 and CDC_AW=4. It runs hierarchy, proc,
flatten, opt, memory_map, opt, check and JSON export, then invokes the existing
strict 12-clock FEC census. It records source/checker hashes before synthesis and
requires identical hashes afterward. It performs no ABC or physical timing claim.

One distinct-source candidate run was admitted on EPYC4 with 32 GB / one thread:
unit `oth-ubuntu-1591169-1792057312`, initial Yosys PID `1591185`, output
`/srv/opentallas-scratch/codex/fec-chien-linear-1015/full_census_0`. The run completed with admitted runner status 0. Full hierarchy/proc/flatten/opt/
memory_map/opt/check and JSON export passed in 683.82 seconds with 5229.71 MB
Yosys peak memory. The source-pinned full clock census counts **86,152 flop bits**
across all 12 actual clock ports; maximum **13,790** on `rclk_emit`. Every root is
within the 15,000 sink-count limit. This is a source-level count, not delivered
clock insertion/spread qualification. The 235 MB netlist remains remote with its
SHA256 recorded in `full_census/receipt.json`; the source, script, losslessly compressed log and receipt
are archived here. The original source census PID 1083099 is independent and
was verified live at 02:49:26 elapsed after this candidate completed.


| Actual clock input | Flop bits |
|---|---:|
| clk | 3,757 |
| clk_collect | 5,120 |
| clk_encode | 5,403 |
| clk_codeword | 5,403 |
| pma_rck | 7,627 |
| rclk_syndrome | 5,747 |
| rclk_bm0 | 6,984 |
| rclk_bm1 | 6,984 |
| rclk_bm2 | 6,984 |
| rclk_bm3 | 6,984 |
| rclk_chien | 11,369 |
| rclk_emit | 13,790 |

The full generic netlist includes 86,903 `$mux` and 55,051 `$xor` cells;
these can be multibit cells. It also retains real variable multipliers and
shifts. These counts do not give library area or establish that the Chien/Forney
paths meet the clock period. Actual partition, pin placement, clock distribution,
TT/FF timing and DRC remain required before adoption.


`full_census/qualification_boundary.json` specifies the exact wrapper/window and
clock-family scope. In particular, this does not include the 613/487 gearbox or
registered collective endpoint hierarchy. Their eventual joined hierarchy must
be counted and physically qualified separately; these twelve roots and counts
do not transfer by naming or composition alone. `yosys.log.gz` decompresses to
the exact source-pinned log hash recorded by the full-census receipt.
