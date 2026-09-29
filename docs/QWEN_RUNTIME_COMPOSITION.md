# G4 runtime composition: simulation boundary contract

This decomposes simulator compilation only. It adds no proposed silicon queue,
wire register, arithmetic unit or clock cycle. Production RTL remains unchanged.

| Boundary | Per-instance input payload | Output payload | Service | Latency / storage |
|---|---|---|---|---|
| W16 MAC group | 512 weight bits + 32 activation bits + valid/first/add-valid | 512 sum bits + 16 fault bits | Existing one operation per lane per clock | Original multiplier/add pipelines and IL8 circulation; no new storage |
| B4 W16 reduction bank | 2048 held bits + 2048 pair-A bits + 2048 pair-B bits + add-valid/select | 2048 result bits + fault | One vector each clock | Original 3-cycle arithmetic/hold plus output register = 4 cycles |
| Controller -> MAC | G4 groups as above, conditioned operands and original timing controls | Four group results | Every original edge | Host copying represents wires, not a FIFO |
| Controller -> reduction levels | Original vline/split-derived valid/select | Two reduction-bank output vectors and faults | Every original edge | Two levels = 8 cycles, same as original G4 |
| External memory/result interfaces | Original matvec ports unchanged | Original addresses, requests, masks, output data, argmax, maxima, progress, fault | Compared every checked cycle | No host memory-response shortcut or extra buffering introduced |

Queue depth introduced at every cut: **zero architectural entries**. The host
holds current wire values long enough to evaluate a simultaneous edge. It must
never feed a newly registered producer value to a consumer on that same edge.
Clock freezes stop all kernel/controller clocks together. Data/fault responses
are copied back after all rising-edge evaluations, then controller combinational
logic is settled without another rising edge. Normal sequential state stays
inside the Verilated RTL models.

The gate's externally driven ROM/scale/KV/activation test values are synthetic
and held inputs. They exercise interface equivalence, not HBM service timing or
checkpoint accuracy. Later integrated memory tests must bind the existing
service model and replay its stalls identically on both sides.

No G6144 elaboration is authorized by this contract. The next size requires a
complete G4 exact verdict, then measured G64/G512 resource gates approved by root.

## G4 acceptance result

The complete public-port differential against safe a4870d3b passes 24 cases /
5,520 clock iterations / 412 write cycles, with a completed-operation check on
each case. Split0/1/2, INT8 row scales, BF16 KV source, ragged output counts,
mmode/rmax, equal-value argmax operands, reset and clock freezes are covered.
The same-edge scheduling mutant fails at case0 tick44 on o_data.

An initial coordinator failed after reset because it captured producer data
before propagating asynchronous reset into the kernel models. Four clock-low
settling passes fix that event propagation before the snapshot; no rising edges
or architectural registers are added. This settling depth is qualified for the
G4 cut only. Generalized G64 composition must check convergence explicitly.

The next proposed remote resource experiment is **controller-only G64**, not a
G64/full-token execution claim. The controller still contains scale/argmax logic
and may be the next compilation bottleneck. `python3 run.py --only
replay_controller --groups 64` imposes 2GiB address space, 300CPU seconds and
360s wall time for each stage, with make -j2. Stop on cap failure. G512 and
G6144 are deliberately not accepted by this runner.

## Reproduction from the repository

```bash
python3 tools/qwen_matvec_runtime_emit.py --groups 4 --out /tmp/qwen-runtime-g4
python3 tools/qwen_matvec_runtime_run.py --workdir /tmp/qwen-runtime-g4
```

The source Git objects `a4870d3b` and `a80d6a30` must be available. The generator
exports them into the output directory, generates the simulator-only controller
and fixed bank wrappers, and does not edit production RTL. The reference is the
safe pre-experiment RTL; the candidate extraction is from the bank-cut experiment.

`results/rtl/qwen_runtime_composition/g4_exact.json` pins emitted sources, the
runner and tool version. Its compile/build stages may reuse existing generated
objects; they are not a fresh scaling benchmark. The final generic coordinator
passes 24 cases, 5,520 cycles and 412 write cycles, with clock-low convergence in
at most three passes. Peak process RSS is 18,176 KiB on this local run.

The runner supports Verilator 4.x and 5.x runtime linkage. Its G64 guard prevents repeating the known costly flat-reference elaboration.
G64 full equivalence now passes with the qualified leaf-hierarchy reference
(see the result below). The current whole-matvec gate uses NW16 and the reduced default scale
base selection; NW18 remains unqualified; scale-base mode 1 has the G4 follow-up below.

## Scale-address mode follow-up

The `--scale-wcs-base 1` gate rebuilds both controller and safe reference with
`INT8_SCALE_WCS_BASE=1`, while retaining identical compiled arithmetic kernels.
It passes 24 cases / 5,520 cycles / 412 write cycles and rejects the wrong-edge
mutant. This validates the full-shape scale-base **selection mode** at G4; it is
not a full-shape matrix or token result. The record is
`g4_scale_wcs_base1_exact.json`. NW remains 16 in this gate.


## G64 complete runtime equivalence

On ot-pve1, Verilator 5.050, the safe reference uses only the previously qualified
fmul/qadd leaf hierarchy. The runtime candidate uses 64 MAC objects and 96 fixed
B4 reduction-bank objects. Root's previously built G64 controller archive is
reused after byte-for-byte controller source verification. No hardware
partition, latency or queue is changed.

The exact gate passes **56 cases, 12,880 cycles and 956 write cycles**, comparing
every public port. Clock-low settling converges within three passes. Runtime
is 34.60 seconds wall / 34.59 seconds CPU and 42,552 KiB peak RSS. The wrong-edge
mutant fails on case 0, tick 46, o_data. Result and compiled archive/binary pins
are `results/rtl/qwen_runtime_composition/g64_exact.json`.

Fresh hierarchical reference front-end: 53.32 seconds, 1,460,376 KiB peak RSS.
C++ reference compilation: 10 minutes 24 seconds at make -j8, 579,456 KiB maximum
individual child RSS. This is not total concurrent build memory. Full reference
build is deliberately allowed to finish; the former six-minute wall limit is
replaced by a configurable one-hour default. Kernel builds are independent and
compiled once per ADDS variant. Earlier link failure was missing hierarchy DPI
headers/runtime and was fixed without modifying RTL or source test data.

Reproduce with Verilator 5.050:

```bash
python3 tools/qwen_matvec_runtime_emit.py --groups 64 --out /tmp/qwen-runtime-g64
python3 tools/qwen_matvec_runtime_run.py --workdir /tmp/qwen-runtime-g64 \
  --hier-reference --verilator /path/to/verilator-5.050/bin/verilator --jobs 8
```

G64 used NW16 and scale-base mode 0. The separate G4 gate covers scale-base mode 1.
Neither is checkpoint execution, complete core composition, or full-shape token
performance. G512 is not accepted by the runner and requires another root gate.

## Full-core integration boundary (generated and linted, not connected yet)

`tools/qwen_runtime_core_emit.py` removes only `u_me` from a generated copy of
`ot_hdc_core_vector_weight` and exports its 54 non-clock ports. Instructions,
SU/reduction, embedding control and completion stay in RTL. The emitted G4
NW18/scale-base1 controller lints; the complete core-runtime composition has not
yet executed. Production RTL is untouched.

The actual checkpoint loader is `tools/runtime/qwen_runtime_memory.hpp`.
`tools/qwen_runtime_checkpoint_memory_gate.py` verifies input hashes against the
existing layer0 oracle, loads 36,569,088 packed code words and 404,928 scale words,
checks 72 independently decoded words (including groups 0/63/511/6143), and checks
read-before-write, held read responses and ordered write priority. This does not
by itself establish RTL/memory composition.

The full-core host must first snapshot memory requests and old-data reads, clock
all RTL objects simultaneously using prior read responses, then commit the new
memory responses and ordered writes. The original TB write order is increasing
ME group/lane, MX, SU, RD, TP. No memory transaction may bypass this edge boundary.

The current shipped layer0 TB leaves SU_VEC=0/SW=1 defaults. The first full-core
exact run must explicitly retain and label that scalar-SU reference profile.
It cannot establish the modeled SW1024 cycle rate; a full-throughput profile
requires separately approved resource/physical budgets.
