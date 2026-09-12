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

## Proposed precision set

Driven by what the models actually need, not by what is elegant:

| Use | Format | Significand | Why |
|---|---|---:|---|
| Weights, ROM-resident | MXFP4 / FP8 E4M3 | 3–4 b | The density argument for mask ROM only pays at low precision; this is the whole thesis. |
| Weights, HBM-resident | FP8 E4M3 / BF16 | 4–8 b | Match the comparator's real operating precision. |
| Activations | BF16 | 8 b | What the checkpoints ship and what the reference computes. |
| Accumulation | FP32 | 24 b | One rounding per step; the tensor-core contract. |
| Reductions/norms | FP32 | 24 b | Softmax and RMS norm need the headroom. |

Every multiplier array is then sized by its **significand product width**, which
is the quantity that sets both depth and area:

| Pair | Product width | Relative array |
|---|---:|---:|
| MXFP4 × FP8 | 3×4 = 12 b | 0.25× |
| FP8 × FP8 | 4×4 = 16 b | 0.25× |
| BF16 × BF16 | 8×8 = 64 b | 1× |
| FP32 × FP32 | 24×24 = 576 b | 9× |

This is why a tensor core is built around BF16/FP8 and not FP32, and why
supporting FP32 multiply in the same array is the wrong trade.

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
