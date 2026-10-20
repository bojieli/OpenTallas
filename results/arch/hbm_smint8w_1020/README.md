# HBM SM INT8 wider front: source contract study

Source inspected: d98271674, the existing QINT8 fix. No 128-code front implementation,
new synthesis, timing gate, measured speedup, or release rate is established here.

`ot_smh_static_int8` wraps the actual PIPE1 converter. The static compiler sends
one packed128-code line every two edges. The adapter emits two64-code native
lines with the same original tag, in the original half order. Each136-byte
transport block contains64packed lines, hence128native issue slots.
The established measured baseline is136edges/block; source contract arithmetic
alone cannot lower it.

Widening only the converter does not make a128-code SM: both native subslots
must reach an issue/data path that accepts them on the same edge. Retaining one
64-code downstream issue slot per edge still requires128slot edges per block.
A faster candidate therefore needs two explicit native issue lanes or an
otherwise proven equivalent128-code datapath, including storage read ports,
operand fanout, accumulation contexts, tags and output capacity. Price their
area, memory ports, links and latency before layout.

Exactness obligation: retain each original native subslot's row/group/wave/slot
identity. Preserve conversion rounding, original golden product/reduction tree,
FP32 rounding points and the scale application after reduction. Summing the two
half results together earlier is not an admissible shortcut without an exact
identity proof. Independent row-context interleaving may preserve arithmetic
order but must establish actual SRAM port and context capacity.

The current bit118 SVG checker fix stays a separate prerequisite: compiler and
checker compare the converted stream, not the original packed packet. Test the
real production compiler marking and both halves. Required production cases
are qkv48/o128/gu192/down128 with causal half-swap, tag-reuse, dropped-half,
sign and reduction-order witnesses. No candidate performance enters the token
ledger before those pass and physical qualification establishes actual clocks.

The compact source_contract.json records the admission obligations. This study
finishes the source inventory; implementation and measured proof remain open.
