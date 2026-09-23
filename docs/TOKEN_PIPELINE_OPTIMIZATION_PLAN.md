# Fully pipelined token decode on ASAP7: review and optimization plan

Date: 2026-09-23. Scope: an end-to-end RTL decode of one token, datapath and
control, simulated at token level and implemented on the ASAP7 PDK at a high
clock. This document records the review of the current designs, the plan, and,
in its log section, each iteration's measurements.

## 1. Review of the current designs

### Targets and what decodes a token today

| Target | Token-level RTL today | Clock evidence |
|---|---|---|
| Qwen3 reduced, ROM (ABI 3.0) | `ot_a3_shipped_prefix_top` runs the full reduced decode program: 248/248 instructions, 7,901,003 cycles | Slowest instantiated blocks route at 58 MHz (`matmul_bf16_sram_engine`), 70 MHz (`a3_qwen_gqa`), 75 MHz (`a3_microsequencer_dep_depth`) |
| DeepSeek V4.1 reduced, ROM array/wafer (ABI 3.0) | Deployment builds; engines partly integrated; no end-to-end token in RTL | Supporting engines 190–520 MHz |
| ROM redesign mechanisms | Striped banks, package link, layer pipeline (functional, `rtl/rom/`) | Link endpoint routes at 1,339 MHz |
| Prototype compute tile | `ot_compute_unit` (16 lanes) | 1,290 MHz closed, but shares no module with the token path |

The ABI 3.0 machine is a general programmable accelerator. It has a descriptor
control plane, a microsequencer, an admission bridge and engines with IEEE
arithmetic. Its measured problems are structural:

1. **One MAC per cycle.** `ot_a3_engine_array` retires one multiply-accumulate
   per cycle; a 64-lane tile is written but not instantiated.
2. **Unpipelined arithmetic.** A single combinational FP32 add is a ~6.25 ns path
   on ASAP7, capping a block near 160 MHz. Several engines still contain them.
3. **General control costs clock.** The same 16 lanes route at 1,290 MHz alone
   and 226 MHz inside the G2 cluster with its control plane: 5.7× of clock.
4. **Cycle count.** 7.9 M cycles for a 1.28 M-MAC reduced token: about six cycles
   of control and service per MAC.

At its 58 MHz limiter, the reduced Qwen3 token takes ~136 ms in the ABI 3.0 RTL.
The fast pieces already exist in isolation: FP32 add and multiply pipes (1.4 GHz),
the MAC tile (1.2 GHz), a square root (1.36 GHz), the block-max unit (1.7 GHz).

## 2. Design decision

Build a **model-specific, fully pipelined decode core** for the ROM machine, the
design the [analytical report](ANALYTICAL_REPORT.md) recommends. The ABI 3.0
machine remains the general HBM-side vehicle.

- **Datapath.** W parallel MAC lanes. Each lane is a pipelined FP32 multiply
  followed by a pipelined FP32 add, and interleaves I ≥ adder latency + 1
  outputs. Every lane therefore retires one MAC per cycle, while each output
  still accumulates its K products in order (sequential FP32 RNE per output).
  Weights stream from ROM, W per cycle; activations broadcast.
- **Special functions.** Exponential, reciprocal and reciprocal square root are
  fixed pipelines of FP32 multiply/add stages: range reduction plus a
  polynomial, and Newton-Raphson from a bit-level seed. No combinational IEEE
  operation and no iterative divider sits on any path.
- **Reductions.** Sums of squares, softmax sums and maxima use a fixed
  interleaved-partial-plus-tree order, so they are deterministic and pipelined.
- **Control.** A static schedule of macro-operations (matrix-vector, norm, RoPE,
  attention head, activation, residual, argmax) in a small ROM. Registered
  address generators and a single-issue sequencer: no descriptors, no
  admission, no microcode interpretation on the critical path.
- **Memory.** Weight ROM and KV SRAM sit behind simple ports. The simulation
  top supplies behavioural arrays; the physical top leaves them as ports or
  macros.
- **Numerics.** Stated, not inherited:
  - BF16 weights, activations rounded to BF16 at matrix inputs (exact FP32
    products), FP32 accumulation and FP32 elementwise work;
  - the special-function algorithms above;
  - a Python golden model emulating every operation in the same order with
    NumPy float32, so the RTL must match it bit for bit.

  The decoded token is also compared with the project's torch reference oracle.

## 3. Plan

| Step | Deliverable | Gate |
|---|---|---|
| P1 | Golden model of the reduced Qwen3 decode step in the RTL's arithmetic order; prefill KV for the oracle's 16-token prompt | Golden decodes the oracle's first token (1073) |
| P2 | Pipelined arithmetic units: MAC lane, exponential, reciprocal, reciprocal square root, max/argmax | Bit-exact against the golden per unit; each routes at or above 1 GHz on ASAP7 |
| P3 | Matrix-vector engine (W lanes × interleave) and vector/norm/RoPE/softmax units | Bit-exact on real layer data |
| P4 | Static control sequencer and core top; simulation top with weight ROM and KV SRAM | One-token decode in Verilator bit-exact with the golden; token 1073 |
| P5 | ASAP7 synthesis and place-and-route of the core, clock sweep | Routed Fmax, area, cycles per token, tokens/s |
| P6 | Iterate on the measured limiter: lane count, overlap of vector work with matrix work, control fan-out, critical paths | Each change re-verified at P4 and re-measured at P5 |

## 4. Iteration log

Entries are appended as measurements land.

**P1 (done).** `tools/hdc_golden.py` specifies the arithmetic. With the
oracle's 16-token prompt it decodes 1073, 382, 93: the torch oracle's three
tokens. The first token's logit margin is 0.865 against 0.830. Exponential,
reciprocal and reciprocal square root are within 2.4×10⁻⁷ relative error
(≈2 ulp). Test: `tests/test_hdc_golden.py`.

The golden now composes every operation from `add` and `mul`, the qualified
pipes' semantics: IEEE RNE with gradual underflow, and every zero result
canonical +0. It still decodes 1073.

**P2 (functional; physical pending).** `rtl/hdc/ot_hdc_sfu.sv` holds three
pipelines built from the qualified FP32 pipes: exponential (depth 92),
reciprocal (46) and reciprocal square root (61). Each accepts one operand per
cycle. All 18,010 golden vectors match bit for bit, fed with random bubbles. <!-- figure: 18010 src="results/rtl/hdc_iterations/iter1_baseline.json#sfu.vectors" name="HDC special-function vectors checked" -->

**P3–P4 (done).** The core has four parts:

- `ot_hdc_matvec`: 16 lanes × 8 interleaved outputs; the sum circulates in the
  adder pipeline;
- `ot_hdc_stream`: a 2-D element loop through a fixed
  multiply/add/special-function/multiply pipeline, plus a segmented reducer;
- `ot_hdc_core`: the sequencer;
- a program from `tools/hdc_program.py`, with the format in `tools/hdc_isa.py`:
  178 instructions. <!-- figure: 178 src="results/rtl/hdc_iterations/iter1_baseline.json#parameters.program_instructions" name="HDC program length" -->

The program is first run on an ISA-level model, which is bit-exact with the
golden. In Verilator the RTL decodes token 1073 at position 15.

- Cycles per token: **107,228**. <!-- figure: 107228 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.cycles" name="HDC cycles per token, first iteration" -->
- Every logit, the whole vector memory and the whole KV cache match bit for bit.
- From an empty KV cache it consumes the 16-token prompt, writing its own KV
  rows, and generates 1073, 382, 93: the torch oracle's tokens.
- Cycles on which the matrix engine issues: 90,112. <!-- figure: 90112 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.me_issue_cycles" name="HDC matrix-engine issue cycles" -->
- Cycles on which the stream unit issues: 11,729. <!-- figure: 11729 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.su_issue_cycles" name="HDC stream-unit issue cycles" -->
- Cycles on which neither issues: 5,387. <!-- figure: 5387 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.both_units_idle_cycles" name="HDC cycles with neither unit issuing" -->

Record: `results/rtl/hdc_decode_campaign.json`, from
`tools/rtl_hdc_decode_campaign.py`.

Each iteration's campaign record is kept in `results/rtl/hdc_iterations/`.
`results/rtl/hdc_decode_campaign.json` is the current one.

**Iteration 2: attention batching, fused sums of squares, chaining.** None of
these changes alters the arithmetic.

- *Attention.* The matrix engine now takes an x element per slot
  (`xbase + k*xks + j*xjs`), a slot-shifted weight stride (`(j >> jsh)*js`),
  output strides and a lane-mask mode. All eight heads of a layer are one
  scores op and one weighted-sum op: each slot is a head, and it shares the KV
  words of its group. That replaces 16 ops of 128+ cycles each.
- *Norms.* The op that produces x (embedding, residual add) also reduces
  x·x through a squaring stage in front of the reducer. The separate
  sum-of-squares pass of every hidden-size norm is gone.
- *Chaining.* A matrix-vector op whose only hazard is the preceding stream
  op's output starts when that op writes its first element, not when it
  drains. It reads x[k] no sooner than k·8 cycles after starting, so it cannot
  overtake the writer.

Results:

- program: 113 instructions, 13 of them chained; <!-- figure: 113 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#parameters.program_instructions" name="HDC program length, iteration 2" -->
- cycles per token: **95,590**; <!-- figure: 95590 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#single_step.cycles" name="HDC cycles per token, iteration 2" -->
  every logit, the vector memory and the KV cache are still bit-exact;
- matrix-engine issue cycles: 82,944; <!-- figure: 82944 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#single_step.me_issue_cycles" name="HDC matrix-engine issue cycles, iteration 2" -->
  the weight matrices account for about 82K of them.

The limiter is now the 16-lane matrix engine, and only more lanes move it. At
hidden size 128, a lane count above 16 needs outputs × 8 interleave ≥ lanes × 8,
which the 128-row matrices cannot supply. Iteration 3 therefore splits K for
narrow matrices: a deterministic change to the accumulation order, specified in
the golden.
