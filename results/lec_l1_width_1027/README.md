# L1 explicit beat-count width

Source: `rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1.sv`, base main `5b3f0f6b2`.
The L1 frozen proof reported thirteen clean matched-state control differences.
An actual `c_fw` abstract-state witness has `nseen=126`, `av=bv=1`, `nsc=0`,
`st=S_IN`: the Slang reference gives one and the classic-frontend gate gives zero.
This is an abstract-state witness, not a reachable-system counterexample.

The exact combinational expression in `expr.sv` reproduces the frontend
mismatch. The reference is the original source read by Slang, as in the kit's
independent LEC frontend. `fixed.sv` adds an explicit seven-bit cast to the sum.
Classic Yosys on the fixed expression is equivalent to the original Slang
reference for every input combination. An eight-bit cast mutant differs.
There is no new register or latency cycle. Whole-core closure is pending a
fresh gate built from the corrected source; this packet is the smallest
mechanism proof and negative control, not a whole-core receipt.

Measured with `openroad/orfs:asap7lock`, Yosys 0.67 git `2d1509d1b`:

- `compare.log`: original Slang versus original classic, SAT mismatch.
- `fixed.log`: original Slang versus corrected classic, UNSAT / SUCCESS.
- `mutant.log`: original Slang versus eight-bit mutant classic, SAT / FAIL.

Each proof reads the original with `read_slang`, the candidate with
`read_verilog -sv`, then `proc; opt`, stashes the two modules as gold/gate,
creates `miter -equiv -flatten gold gate m`, and runs
`sat -prove trigger 0 -show-inputs -show-outputs m`.
The original/classic comparison uses the same procedure with the frontends
applied to `expr.sv`. No input assumptions or reset assumptions are present.
