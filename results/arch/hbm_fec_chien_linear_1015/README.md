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
exercised complete FEC path. It does not qualify whole-decoder synthesis,
physical clock delivery, timing, routing, area, or the final production schedule.
In particular, BM and Forney still contain real variable GF multipliers and
inverse tables. The 49k XOR helper itself still needs a real placement/timing
budget. No old route, price or physical CLOSED marker transfers to this candidate.

Remote preserved proof: `/srv/opentallas-scratch/codex/fec-chien-linear-1015` on
`ot-epyc4`. Original live census is a separate source tree and process.
