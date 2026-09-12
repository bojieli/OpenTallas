# Datapath redesign: pipelined, conventional, GHz-class

**Status:** proposal with measured justification. Nothing here is implemented yet
beyond the timing probes named below.

## The problem, measured

Every arithmetic block in this repository computes a full floating-point
operation in **one combinational path**. `ot_fp32_rne_pkg::fp32_add_rne` resolves
unpack → align → add → normalise → round between two clock edges, through a
**524-bit exact intermediate** (`accumulator_magnitude`, `product_magnitude`,
`exact_magnitude` at `rtl/ot_fp32_rne_pkg.sv:480-482`).

That buys provable single-rounding exactness. It costs the clock:

| Block, as it stands | f_max | cells |
|---|---:|---:|
| `fp32_add_rne` (unpipelined, 524-bit exact) | 174 MHz | 2,458 |
| `fp32_mul_rne` (unpipelined) | 316 MHz | 5,096 |
| `fp32_to_bf16_rne` | 1,978 MHz | 98 |

**174 MHz is the ceiling for any block that calls the adder**, whatever else is
optimised. No amount of memory restructuring moves it. That is why
`ASAP7_PHYSICAL.md` found the unpipelined proxies closing at 243/84/455 MHz and
concluded they falsify the 0.8–1.1 GHz whole-product clock the system envelopes
assume — the same finding, reached from the other end.

## What a conventional accelerator does instead

No production GPU or accelerator computes an exact wide intermediate, and none
completes a floating-point multiply in one cycle. They pipeline:

- **Latency** of an FP32 FMA on recent NVIDIA parts is roughly 4 cycles.
- **Throughput** is one result per cycle per lane, fully pipelined.
- The clock is set by the slowest **stage**, not the whole operation.

GPUs are especially free to do this because thousands of resident threads hide
the latency — a 4-cycle FMA costs nothing in throughput when another warp issues
meanwhile.

They also pick precisions so the arithmetic is cheap:

- **Multiply in low precision.** BF16 has an 8-bit significand (7 stored + 1
  implicit), so a BF16 × BF16 product is **exact in 16 bits**. No wide
  intermediate is needed at all — the exactness this repository spends 524 bits
  on is free at the multiply.
- **Accumulate in FP32.** One rounding per accumulation, which is the documented
  tensor-core contract, not a 524-bit exact chain.
- **FP8/FP4 for weights** where the model tolerates it: an FP8 E4M3 significand
  is 4 bits, so the multiplier array is roughly (4/8)² ≈ ¼ the BF16 area and
  shallower.

## The measurement that settles it

A five-stage pipelined BF16 × BF16 → FP32 MAC, written as a timing probe
(`ot_probe_mac_pipe`), synthesised on the same ASAP7 view with the same tools:

| | f_max | cells | area |
|---|---:|---:|---:|
| `fp32_add_rne`, unpipelined | 174 MHz | 2,458 | — |
| **pipelined BF16→FP32 MAC** | **725 MHz** | **1,859** | 258 µm² |

**4.2× the frequency in fewer cells.** The critical path is 1.38 ns; the stages
are not yet balanced, so splitting the align/add stage should reach ~1 GHz.

The stages are:

1. unpack, exponent add, exact 8×8 significand multiply
2. normalise the product into a 24-bit significand
3. align the smaller operand to the larger exponent
4. signed add
5. normalise, round-to-nearest-even, pack

Nothing exotic. This is the textbook FMA pipeline, and it is what the repository
should have been built on.

## The full measured progression, and the method that found it

Four successive changes, each measured on the same ASAP7 view with the same
tools. Records under `results/physical_abi3/asap7/datapath_probes/`.

| Design | f_max | critical path | cells |
|---|---:|---:|---:|
| `fp32_add_rne` — unpipelined, 524-bit exact | 174 MHz | — | 2,458 |
| 5-stage pipelined FP MAC | 725 MHz | 1.380 ns | 1,859 |
| + carry-save accumulate (3:2 compressor loop) | 844 MHz | 1.186 ns | 1,143 |
| **+ resolve adder split across two cycles** | **1,469 MHz** | 0.681 ns | 1,287 |

**8.4× the baseline at roughly half the cells.**

### Calibrate the node before blaming the RTL

| Reference circuit | f_max | critical path |
|---|---:|---:|
| Flop → inverter → flop | 8,691 MHz | 0.115 ns |
| 8-bit registered add | 3,412 MHz | 0.293 ns |
| 40-bit registered add | 962 MHz | 1.040 ns |

ASAP7 and this flow have ample headroom. Any block below ~1 GHz here is limited
by its own logic depth, not by the node. Establish this first: it converts
"the PDK is slow" into a testable claim, and it was false.

### Measure each stage in isolation, then find what the assembly adds

| Stage | f_max | critical path |
|---|---:|---:|
| 1 — unpack, exponent add, 8×8 significand multiply | 1,642 MHz | 0.609 ns |
| 2 — exponent subtract, window compare, align shift | 1,478 MHz | 0.676 ns |
| 3 — carry-save accumulate (3:2 compressor) | 3,373 MHz | 0.296 ns |

Every stage ran at ≥1.4 GHz while the assembled MAC managed 844 MHz. That gap is
the whole diagnostic: it says the critical path is **not inside any stage**, so
looking for a slow adder or a slow multiplier is looking in the wrong place.

The culprit was the 40-bit carry-propagate add that resolves the carry-save pair —
1.040 ns on its own, which accounts for essentially the entire assembled path.
Registering its output was not enough; the adder itself is the depth.

The fix is free rather than clever: **that resolve runs once per dot product, not
once per MAC.** Split across two 20-bit halves with a carry register, it costs one
extra cycle amortised over K accumulations — 1/K of the throughput — and the MAC
then runs at 0.681 ns, which matches stage 2's standalone 0.676 ns. The pipeline
is balanced, and the next gain would come from splitting stage 2's align shift.

### The transferable method

1. Calibrate the node with a trivial flop-to-flop path.
2. Measure every stage standalone.
3. Compare the assembly against the slowest stage. Any gap is a path that
   crosses a boundary you thought you had.
4. Attack the widest carry chain first, and check whether it sits in the
   recurring loop or off it — off-loop chains can be split for free.

Two false starts worth recording, because they cost time: the first pipeline
attempt used a `while` loop for the leading-zero count, which Yosys rejects
outright (`While loops are only allowed in constant functions`), and the first
frequency sweep varied the synthesis target across 0.4–1.4 ns and produced four
**identical** netlists — the constraint was not the lever, the logic depth was.

## The array, place-and-routed: 1,117 MHz and 4.6x a same-node GPU's logic density

`rtl/proto/ot_mac_tile.sv` at 16 lanes, taken through **synthesis, STA and
place-and-route with clock-tree synthesis** (`results/physical_abi3/asap7/mac_tile/pnr_lanes16.json`):

| | |
|---|---:|
| f_max | **1,117 MHz** |
| setup WNS at a 1.2 ns target | **+0.305 ns** (meets timing) |
| hold violations | 0 |
| max-cap / DRC / antenna | 0 / 0 / 0 |
| max-slew violations | 13 (the only thing short of full closure) |
| instances | 92,660 |
| core area | 12,278 µm² |

### Synth-only measurement is invalid for this class of design

The same tile measured **128 MHz** through `synth,sta` and **1,117 MHz** through
`synth,sta,pnr` — a factor of **8.7**. The reason is clock-tree synthesis: without
it, every one of the tile's thousands of registers sits on a failing path, and the
violating-path count scaled with register count (255 at 4 lanes, 2,016 at 16,
8,384 at 64 — about 130 per lane, i.e. all of them).

This invalidates a measurement approach, not just a number. Three restructurings
were attempted against the synth-only figure and all three were wasted:
generate-local registers instead of module-level arrays (no change), a registered
operand broadcast tree (no change), and hierarchical module instances per lane
(made it *worse*, 97 MHz at 16 lanes). None of them were the problem, because the
problem was never in the RTL.

**Any frequency figure for a register-rich block in this repository that comes
from `synth,sta` alone should be treated as unusable.** The broadcast tree and the
lane-local registers are kept anyway — both are correct practice and neither
costs anything — but they were not what mattered.

### Density against the comparator

ASAP7 is a 7 nm predictive PDK, so the like-for-like part is the A100 (TSMC N7),
whose figures this repository already records: 312 TFLOP/s dense BF16 on an
826 mm² die. `tools/audit_mac_array_density.py` computes the comparison at three
levels of inclusion and refuses to collapse them:

| Level | TFLOP/s per mm² |
|---|---:|
| A100, whole die | 0.378 |
| A100, standard-cell logic only (die × 0.6) | 0.630 |
| **this array, placed core area** | **2.912** |

**4.63× the logic-level comparator.** The design target was to come within an
order of magnitude; the array is ahead of it, which is the margin a complete
design needs because register file, shared memory, scheduler and interconnect can
only spend density from here.

What this is not: a device claim. The array has no operand storage, no scheduler,
no interconnect and no memory controller, so its density is an upper bound on a
finished design. And ASAP7 is predictive and non-manufacturable while the
comparator is fabricated silicon — the node family matches, the confidence does
not. Both refusals are recorded in the audit artifact rather than left to a
reader's charity.

## Proposed precision set

Driven by what the models actually need, not by what is elegant:

| Use | Format | Significand | Why |
|---|---|---:|---|
| Weights, ROM-resident | MXFP4 / FP8 E4M3 | 3–4 b | The density argument for mask ROM only pays at low precision; this is the whole thesis. |
| Weights, HBM-resident | FP8 E4M3 / BF16 | 4–8 b | Match the comparator's real operating precision. |
| Activations | BF16 | 8 b | What the checkpoints ship and what the reference computes. |
| Accumulation | FP32 | 24 b | One rounding per step; the tensor-core contract. |
| Reductions/norms | FP32 | 24 b | Softmax and RMS norm need the headroom. |

### Measured multiplier cost per precision

Not estimated from significand widths — synthesised, one registered significand
multiply per format, same view and tools:

| Pair | f_max | crit | cells | area | ×MXFP4 area | MAC/s per µm² |
|---|---:|---:|---:|---:|---:|---:|
| MXFP4 × FP8 | **4,713 MHz** | 0.212 ns | 48 | 7.4 µm² | 1.0× | 6.4 × 10⁸ |
| FP8 × FP8 | 2,606 MHz | 0.384 ns | 94 | 13.3 µm² | 1.8× | 2.0 × 10⁸ |
| BF16 × BF16 | 1,541 MHz | 0.649 ns | 346 | 46.4 µm² | 6.3× | 3.3 × 10⁷ |
| FP32 × FP32 | **613 MHz** | 1.631 ns | 2,812 | 354.6 µm² | **48.1×** | 1.7 × 10⁶ |

Three conclusions follow, and the first two were predictions this measurement
confirms:

1. **FP32 multiply cannot reach 1 GHz here even standalone** — 613 MHz at
   1.631 ns, the only format in the set that fails to. Any datapath that must
   multiply in FP32 is capped below the others before anything else is designed.
   Supporting it in the shared array is the wrong trade; it belongs on a separate
   slow path if it is needed at all.
2. **Area scales roughly as the significand product**, as the significand-width
   argument predicts: FP32 measures 7.6× BF16 against a 9× prediction, and MXFP4
   measures 0.16× BF16 against 0.25×.
3. **Throughput per unit area spans 370×** across the set: MXFP4 delivers 370×
   the multiplies per second per µm² that FP32 does, and 19× what BF16 does.

That last number is the quantitative core of this project's own thesis. The case
for mask ROM rests on weight density, and the arithmetic density moves the same
way — for a fixed silicon budget you buy **48 MXFP4 multipliers per FP32
multiplier**. A design that stores weights at 4 bits and then multiplies them in
FP32 has thrown the advantage away in the datapath after paying for it in the
memory.

These are multiply-only and unpipelined, so they are a floor on achievable
frequency and a lower bound on the ratio, not a full MAC figure. The ratio is the
point.

## Array allocation

Replace the per-operator hand-written datapaths with **one pipelined MAC array**
issued by the existing lane machinery:

- A tile of `L` lanes × `D` depth of the MAC above, all five stages registered.
- `L × D` MACs retire one result each per cycle after the 5-cycle fill.
- The accumulator stays in FP32 in the array; only the final store rounds to the
  output format, preserving one-rounding-per-accumulation.
- Operand feed comes from a **RAM**, not a register array. The
  `ot_a3_vector_hadamard` measurement showed a 512-entry register array with
  dynamic indexing costs a 107 ns critical path and grows *linearly* with entry
  count (512 entries → 107 ns, 128 entries → 21.8 ns). That is a mux chain, not
  a memory.

Sizing follows from the target: at 1 GHz, a 16×16 tile of BF16 MACs delivers
256 MAC/cycle = 512 GFLOP/s per tile.

## Fairness: the comparator must get the same treatment

This matters more here than in most projects, because the repository's central
claim is a ROM-versus-HBM comparison and gate **C2** exists to ensure neither
side is handed an advantage.

If the ROM datapath is redesigned to a pipelined conventional array and the HBM
comparator is left as an analytical roofline, the comparison becomes
meaningless — the subject gets engineering attention the comparator never got.
Both sides must be modelled at the same fidelity and the same design style. The
existing asymmetry is already visible in gate **C3**: the cycle model reproduces
the HBM comparator to 1.5% and is 28.7× apart on the ROM side.

## Migration path

Ordered so each step is independently checkable:

1. **Pipeline `fp32_mul_rne` and `fp32_add_rne`** behind their current function
   signatures where possible, or introduce registered module equivalents.
   Verify bit-exactness against the existing scalar references before touching
   any consumer.
2. **Build the MAC array** as a new block with its own RTL campaign, sized per
   the table above. Do not wire it into a consumer until it passes.
3. **Convert one operator** — `TENSOR.MATMUL` is the highest value — to issue
   into the array, keeping the old path available for differential testing.
4. **Move operand storage to RAM** for every block with a dynamically indexed
   array above ~64 entries.
5. **Re-derive the cycle model** against the pipelined timing, then re-run the
   comparison gates. The analytical model's clock assumption must be replaced by
   measured f_max, not the reverse.

## What this invalidates

Stated plainly, because it is substantial: every frequency-derived figure in the
repository currently rests on unpipelined blocks. When the datapath is pipelined,
`results/physical_abi3/**` must be re-taken and the analytical studies re-run
against the new clock. That is a large cascade, and it is the honest cost of
having measured the current design rather than assumed it.

A useful precedent already exists: `rtl/abi3/ot_a3_lane_pipelined.sv` routes at
392.5 MHz where its unpipelined siblings sit at 243/84/455 MHz. The repository
has done this once already.
