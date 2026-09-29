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

The runner supports Verilator 4.x and 5.x runtime linkage. Its G64 full-run guard
prevents repeating the known costly flat-reference elaboration. G64 emission and
a bounded controller-only resource probe are available, but no G64 exact verdict
is claimed. The current whole-matvec gate uses NW16 and the reduced default scale
base selection; NW18 and `INT8_SCALE_WCS_BASE=1` require additional qualification.

## Scale-address mode follow-up

The `--scale-wcs-base 1` gate rebuilds both controller and safe reference with
`INT8_SCALE_WCS_BASE=1`, while retaining identical compiled arithmetic kernels.
It passes 24 cases / 5,520 cycles / 412 write cycles and rejects the wrong-edge
mutant. This validates the full-shape scale-base **selection mode** at G4; it is
not a full-shape matrix or token result. The record is
`g4_scale_wcs_base1_exact.json`. NW remains 16 in this gate.
