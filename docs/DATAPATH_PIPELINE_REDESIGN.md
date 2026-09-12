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

### The device claim, now that there is one

The paragraph above ends "what this is not: a device claim", because an array with
no operand storage cannot make one. That gap is now closed from both ends.

**A complete compute unit.** `ot_compute_unit` is the tile plus two ganged
`fakeram_256x128` weight macros, an activation register file and a sequencer,
place-and-routed to status pass with clean signal integrity
(`results/physical_abi3/asap7/compute_unit/pnr.json`): **1,290 MHz in 31,525 µm²**,
which is **1.309 TFLOP/s per mm² — 2.08× the A100 at logic level**, with its
operand memory counted.

**A whole chip.** `tools/audit_chip_level_density.py` instantiates each
capability's declared engine counts out of blocks that have actually been routed --
compute units with their SRAM, vector units, reduction units, cluster dispatchers
and the control plane -- and compares summed throughput over summed area against
the A100's **whole 826 mm² die**:

| capability | tensor lanes | chip area | clock | TFLOP/s | per mm² | vs A100 device level |
|---|---:|---:|---:|---:|---:|---:|
| `hbm_sram_single_chip` | 256 | 0.783 mm² | 1,174 MHz | 0.60 | 0.768 | **2.03×** |
| `rom_qwen3` | 512 | 1.402 mm² | 1,174 MHz | 1.20 | 0.857 | 2.27× |
| `rom_deepseek_v4` | 8,192 | 20.384 mm² | 1,174 MHz | 19.23 | 0.943 | 2.50× |

Device level on **both** sides, worst case 2.03×. That is the comparison the
array-level number could not support, and it is the one the design target was
written against.

### And on energy it loses

The area table above was measured before the power term, which the audit itself
named as probably the largest unmodelled one. ORFS reports it and the runner already
recorded it, so it was measurable and merely unmeasured:

| capability | area vs A100 | power | TFLOP/s per W | **energy vs A100** |
|---|---:|---:|---:|---:|
| `hbm_sram_single_chip` | 2.23× | 1.833 W | 0.360 | **0.46×** |
| `rom_qwen3` | 2.49× | 3.334 W | 0.395 | **0.51×** |
| `rom_deepseek_v4` | 2.74× | 52.493 W | 0.402 | **0.52×** |

A100 reference: 312 TFLOP/s inside 400 W = 0.780 TFLOP/s per W.

**The design is 2.23–2.74× ahead on area and 0.46–0.52× behind on energy.** Both
are inside the one-order-of-magnitude bar, but the sign flips between the axes, and
every area figure in this document should be read next to that. A single compute
unit is the clearest case: 1.309 TFLOP/s per mm² is 2.08× the A100 at logic level,
while 0.634 TFLOP/s per W is 0.81× its energy efficiency.

It is worse than it looks, not better. **ORFS power comes from the routed netlist
under the flow's DEFAULT switching activity**, not from a workload trace, and a MAC
array running a dense GEMM switches far more than a default assumption. So these
watts are an optimistic lower bound and the energy ratios are *upper bounds* on this
design's advantage. Nothing here checks power density, IR drop or thermal
feasibility either.

This matters for the thesis, not just the scoreboard: part of the ROM argument is an
energy argument, and on the only energy number this project has actually measured,
the design is behind a 2020 GPU.

### Where the energy goes, and why packing harder will not fix it

`tools/audit_energy_attribution.py` attributes the deficit instead of caveating it.

**Accumulator sharing is an area optimisation, not an energy one.** The packed
lane's 10.0 TFLOP/s per mm² and 5.15 per W are **MXFP4 weights**, and setting those
against the A100's dense BF16 rate would credit a format change as a structural win.
Measured at matched precision — BF16 weights, so the only difference from an
unpacked BF16 lane is the sharing:

| lane | fmax | area | power | TFLOP/s/mm² | TFLOP/s/W |
|---|---:|---:|---:|---:|---:|
| BF16 unpacked ×1 | 1,358 MHz | 649.6 µm² | 1.02 mW | 4.181 | 2.674 |
| BF16 packed ×8 | 1,030 MHz | 2,500.4 µm² | 5.85 mW | 6.591 | 2.819 |
| MXFP4 unpacked ×1 | 1,388 MHz | 530.4 µm² | 0.73 mW | 5.234 | 3.797 |
| MXFP4 packed ×8 | 1,063 MHz | 1,697.6 µm² | 3.30 mW | 10.016 | 5.154 |

At matched BF16: **area 1.58×, energy 1.05×.** Sharing the accumulator buys area and
is essentially energy-neutral; the 1.36× that appeared at MXFP4 is mostly the
narrower multiplier, not the sharing. So the honest figure for this optimisation is
1.58×, not 1.91× — the larger number compares two different arithmetics.

**The arithmetic is not the problem.** The BF16 packed lane is 10.5× the A100 on area
and **3.6× on energy**. The complete compute unit is 0.81×. Subtracting 16 routed
lanes from the routed unit says where it went:

| | power | share |
|---|---:|---:|
| compute unit, total | 65.08 mW | |
| arithmetic (16 lanes) | 16.25 mW | **25%** |
| operand delivery + sequencer | 48.83 mW | **75%** |

**Three quarters of a compute unit's power is moving operands, not multiplying
them.** That is what the accelerator literature says, and it is what the ROM thesis
claims to address. It also means the obvious next optimisation — pack the
multipliers harder — is the wrong one: it cannot touch 75% of the energy.

The 25/75 split is an *attribution by subtraction*, not a per-component measurement:
a lane inside the unit has different placement and loading from one routed alone.

### The inclusion list, which is the rest of the honesty

The **area is incomplete**: no KV-cache SRAM, no global activation buffer, no HBM
PHY or controller, no ROM array for the ROM variants, no clock or power
distribution, no pad ring. All real silicon, so the area density overstates a
finished product. And the A100's 400 W is a package TDP that *includes* the HBM and
PHY the area list excludes — so the two sides are not charged for the same
components on either axis.

The single-clock assumption is also load-bearing: the chip clock is the minimum over
instantiated **datapath** blocks, and the control plane is excluded and charged its
own 265 MHz. That is only legitimate because `ot_cluster_dispatcher` decouples the
domains and the control audit measures 99.1 % array utilisation across it. Wired
directly, the chip would run at 265 MHz and the table would read 0.46×. See
[`CONTROL_PATH_DESIGN.md`](CONTROL_PATH_DESIGN.md).

## Every precision lane closes at ~1.37 GHz, and the density argument does not survive contact

All three weight formats, each through synthesis, STA **and** place-and-route,
each **fully closed** -- zero max-slew, zero max-cap, zero DRC, positive slack
(`results/physical_abi3/asap7/mac_lanes/`):

| Weight format | f_max | setup WNS | instances | core area | slew | DRC |
|---|---:|---:|---:|---:|---:|---:|
| BF16 E8M7 | 1,358 MHz | +0.264 ns | 5,637 | 650 µm² | 0 | 0 |
| FP8 E4M3 | 1,371 MHz | +0.271 ns | 4,801 | 571 µm² | 0 | 0 |
| MXFP4 E2M1 | 1,388 MHz | +0.280 ns | 4,418 | 530 µm² | 0 | 0 |

All three are qualified bit-exact against `runtime.reference.mac_tile` by
`rtl/test/tb_mac_lane_fmt.sv`.

### The correction this forces

Earlier in this document the measured multiplier costs were used to argue a 370×
throughput-density spread across precisions. **At lane level that argument is
wrong**, and these numbers are why:

| Format | multiplier | whole lane | multiplier's share |
|---|---:|---:|---:|
| BF16 | 46.4 µm² | 650 µm² | **7.1 %** |
| FP8 | 13.3 µm² | 571 µm² | **2.3 %** |
| MXFP4 | 7.4 µm² | 530 µm² | **1.4 %** |

The multiplier is a rounding error in a lane. The 40-bit accumulator, the align
shifter and the split resolve dominate, and **none of them shrink with the weight
format**, so the 6.3× multiplier saving from BF16 to MXFP4 becomes an **18 %**
lane saving. Quoting the multiplier ratio as an architectural advantage charges
the accumulator to nobody.

### What actually cashes it: share the accumulator

`rtl/proto/ot_mac_lane_packed.sv` puts PACK multipliers behind **one**
accumulator, summing their aligned products in an exact fixed-point tree -- the
same thing a tensor core does, and for the same reason. The tree introduces no
rounding because the terms are already integers in a common window, so the result
does not depend on association order.

At PACK=8 with MXFP4 weights the lane is qualified bit-identical to the reference
and retires a K=32 dot product in **4 cycles instead of 32**:

    PASS PACK=8 E2M1: bit-identical to the reference (ffffffc320), 4 cycles for K=32

Sizing the array by multiplier area alone would have produced a design whose
accumulators dwarfed its multipliers, and no amount of re-measuring the multiplier
would have revealed it.

**But the first packed lane does not close, and the gain is 2.1× not 8×.**
Place-and-routed (`lane_mxfp4_packed8.json`): 717 MHz at setup WNS **−0.394 ns**
in 1,975 µm², against the unpacked lane's 1,388 MHz *closed* in 530 µm². Eight
MAC/cycle for 3.7× the area.

The cause is the adder tree: summing eight 40-bit aligned terms with `+` builds a
chain of carry-propagate adders — the identical carry-chain mistake already fixed
once in the accumulator loop, reintroduced one level up. The tree has to be
carry-save too: 3:2 compressors reducing eight terms to a (sum, carry) pair, then
a 4:2 compression against the accumulator pair, with no carry propagation
anywhere in the recurring path.

So the direction is confirmed and the implementation is not finished. Recorded
that way rather than quoting the 8× the idea promises.

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

## The comparison, at equal fidelity, measured

`rtl/proto/ot_compute_unit.sv` is **one RTL used for both sides**: same MAC tile,
same SRAM-backed operand delivery, same place-and-route, same gates. The only
structural difference between the ROM design and the HBM comparator is where a
weight column comes from when it is not already in the local buffer, and that is
modelled as backpressure on `refill_valid` rather than as an assumption fed into
a spreadsheet. The cycle count is therefore the comparison, not an input to it.

`rtl/test/tb_kernel_rom_vs_hbm.sv`, same operands, same expected results:

| refill period | cycles | stall cycles | result |
|---:|---:|---:|---|
| 1 (on-die ROM, never starved) | 46 | 0 | correct |
| 2 | 78 | 31 | correct |
| 4 | 142 | 95 | correct |
| 8 | 266 | 219 | correct |

Correct at every rate is the load-bearing part: the accumulators hold across a
stall instead of drifting, so a unit that only worked when fed would have failed
here.

### What the bandwidth actually implies, and why it cuts against the thesis

`tools/audit_kernel_refill_regimes.py` turns a bandwidth figure into the refill
period it implies. A100 HBM at 2.0 TB/s over 108 compute units is **16.9 bytes
per cycle per unit** at 1,117 MHz. One weight column of this 16-lane tile is 32 B
in BF16, 16 B in FP8, 8 B in MXFP4:

| Weight format | reuse 1 | reuse 8 | reuse 64 |
|---|---:|---:|---:|
| BF16 | **1.89** | 0.24 | 0.03 |
| FP8 E4M3 | 0.95 | 0.12 | 0.01 |
| MXFP4 | 0.47 | 0.06 | 0.01 |

A period below 1.0 means the memory keeps up and the array never stalls. So at a
reuse factor of 8 or more — any batch above a handful — **HBM bandwidth is not the
bottleneck at compute-unit level, and the ROM store buys nothing here.** The
measured advantage exists only at reuse 1: BF16 weights from HBM need period 1.89,
which costs 78 cycles against the ROM path's 46, a factor of 1.7.

That is a narrower claim than "ROM is faster", and it is the one the measurement
supports. It also agrees with what this repository's own
`COMPARISON_FAIRNESS_AUDIT.md` says about single-session versus multi-session
comparisons, and with the README's batch-1 framing being the regime where the
advantage lives.

The audit refuses to emit a single headline for exactly this reason: the refill
period depends on reuse, reuse depends on batch, and a one-number comparison
silently picks a batch and flatters whichever side has the cheaper weight store.
The HBM figure is also a peak-rate divide with no DRAM page behaviour, refresh or
inter-unit contention, which is generous to the HBM side.

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
