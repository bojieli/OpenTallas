# Retained SM tile state and clock decomposition

This candidate preserves the twelve published hard children and every retained
cell of the source-pinned `f6ee9d6d1` EG/WG tile. It has 995 sequential Q bits and
one ICG in each own leaf, or 15,920 Q bits across sixteen tiles per SM. None of
these bits is replaced by a rectangle, an endpoint counter, or a timing stub.

The cut has 618 actual one-bit nets: 355 inputs and 263 outputs. The extra output
is the existing registered ICG enable, `en_r` (source bit 8870). The original ICG
continues to clock the own leaf. The candidate wire parent exposes twelve raw
child roots and instantiates the same negative-level ICG at each root, driven
by that retained enable. A permanently running child clock is not equivalent
to this candidate. Each raw child root must be delivered at the child's measured
boundary phase; its branch ICG/clock insertion and enable setup must be measured.

Graph expansion reproduces all 131 original cells, their parameters, connections,
and original boundary ports exactly for the common-clock decomposition. EG/WG
cycle benches also execute the separate twelve-root ICG candidate against the
original flat parent. With all raw roots tied to the original raw clock, both
pass 4,096 compared cycles after 32 initial warmup cycles with zero mismatches, including a second reset interval and
random traffic on every boundary input. An internal tie-zero of the retained
`cgo` output is a runnable negative: both variants report 2,016 mismatches and
abort. These runs use Verilator 5.050. The mapped own leaf uses actual Liberty-derived zero-delay cell models. The twelve hard arithmetic interiors use
identical explicit deterministic surrogates on both sides; the bench qualifies
retained state, gating and cut wiring only. It does not establish hard-leaf
arithmetic or physical behavior with different clock phases.

An ASIC synthesis against the real ASAP7 RVT TT AO/OA/SIMPLE/INVBUF/SEQ libraries
maps each own leaf to 355.300020 square micrometers of cells, including its ICG.
Of this, 292.591440 is sequential area. The logs and mapped netlists are retained.
The `73.44 x 73.44` outline in `extraction.json` is a partition request, not an
assigned die slot. Pin density is below 4.9 bits per micrometer on the proposed
input face. Placement, pin-register distance, clock insertion/spread, PG phase,
all actual seam cuts/reach, TT/FF/DRC, and native production throughput remain
open. No existing view, clock constraint, immutable price or cost ledger changed.

Reproduce extraction and the behavioral harness with
`tools/hbm_sm_own_logic_1013.py` and `tools/hbm_sm_own_logic_bench_1013.py`.
The emitted `eg_run.sh`/`wg_run.sh` run the positive by default and the negative
with argument `mut`. `map_asap7.sh` performs the mapped sizing run. Execute heavy
builds through `ot-run` using measured memory; these benches used 4 GB and four
threads, and sizing used 2 GB and one thread.

The first full-synthesis sizing candidate reduced995sourceQbits to975physicalflops.
Its CTS record is preserved as diagnostic_975_gate.json. The retained candidate
maps directly before constant/merge simplification, with kept Q nodes, and
contains995actualstandard-cellflipflops (967DFFHQN +28DFFASRHQN) plus oneICG.
This mapped netlist itself passes the flat-parent cycle bench and observed
mutant. Its physical source is eg_retention_asap7.sv; WG has the same functional
cell/parameter/connection graph, proved in eg_wg_graph_identity.json.
