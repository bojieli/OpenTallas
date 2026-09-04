# Performance design post-mortem: how the accelerator came to be 44,000x too slow

**Post-mortem ID:** TA-PM-PERF-1

**Status:** findings established; corrective decisions open

**Issue date:** 2026-09-04

**Occasion:** a cycle-accurate Qwen3-8B batch-1 decode at context 8,000 was found to
deliver 0.225 tokens per second. The session producing it was stopped.

**Scope:** why the modelled machine is four to five orders of magnitude below this
program's own stated target, why roughly 457 million agent tokens and 340 agent-hours
of work did not surface it, and what rule changes follow.

This document is deliberately unsparing. Every number in it was recomputed from the
repository during the investigation and every claim carries its source. Where something
is an inference rather than a record, it says so.

---

## 1. The number

Two artifacts, one token, one process view (SKY130), one prompt position:

| artifact | cycles | seconds | tokens/s |
| --- | --- | --- | --- |
| `results/abi3/cycle/qwen3_hbm_exact8k_b1_sky130_decode_pos8002_rowfold_v1.json` | 172,357,340 | 4.4414 | 0.2252 |
| `results/abi3/cycle/qwen3_rom_exact8k_b1_sky130_decode_pos8002_rowfold_depthfix_v1.json` | 148,108,696 | 3.8165 | 0.2620 |

Both retire the real model. The counters say so: `tensor.multiplications` is
7,568,097,280 and `tensor.additions` is 7,566,544,512, for 15,134,641,792 work units,
and the HBM lane moves 17.66 GB. The program is not a stub and the arithmetic is not
faked. The machine executing it is simply very small.

`docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md:66` states the target:

> The aspirational north star remains **10,000 generated tokens/s, equivalent to
> 100 microseconds per output token**.

The delivered figure is 0.225 tokens/s. The gap is **44,414x**.

## 2. The gap, decomposed

The tempting reading is that the machine is badly scheduled. It is not. Charging each
target's own advertised tensor width against the work its own counters retired:

| | HBM single chip | ROM single chip |
| --- | --- | --- |
| advertised tensor lanes | 256 | 512 |
| measured rate, work/lane/cycle | 0.34588 | 0.34588 |
| fabric peak | 3.436 Gwork/s | 6.872 Gwork/s |
| tensor-bound floor | 170,926,140 cycles | 85,463,070 cycles |
| actual / floor (scheduling loss) | **1.008x** | 1.733x |
| model-FLOPs utilisation | **99.17%** | 57.70% |
| compute shortfall against the north star | 44,045x | 22,023x |
| total gap | 44,414x | 38,165x |

The products reconcile exactly: 44,045 x 1.008 = 44,414, and 22,023 x 1.733 = 38,165.

**The HBM accelerator runs at 99.17% model-FLOPs utilisation.** There is no scheduling
problem on that target at all. Every cycle the machine could have used, it used. It is
a 3.4 Gwork/s machine asked to do a 151.3 Twork/s job.

That is the central finding, and it inverts the intuitive diagnosis. The design is not
inefficient. It is small, it is efficient at being small, and its efficiency is exactly
what made the smallness invisible: every utilisation metric the program tracked was
excellent right up to the moment someone divided by wall-clock seconds.

For scale: reaching the north star at one BF16 fused multiply-add per lane per cycle and
a 1 GHz clock needs **75,673 tensor lanes**. At the SKY130 clock of 38,807,100 Hz it
needs 1,949,984. The design has 256 and 512.

## 3. Six mechanisms that hid it

### 3.1 The performance gate was defined so that it could never fail

`docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md:66-70` sets the north star and then,
in the same paragraph, removes it from the gates:

> It is not a release pass criterion. The release SLO is still unfrozen for each model,
> target role, context length, process view, PVT corner, batch size, and concurrency
> point. Until those budgets are frozen in the comparison contracts, performance can be
> measured but the TPOT gate can only be `not_evaluable`, not `pass`.

And later, at line 637:

> The 10,000-token/s north star is shown alongside the frozen budget but does not
> silently populate it. A comparison with a missing budget remains `not_evaluable`; a
> measured number alone is not a passed requirement.

Each sentence is individually defensible. Together they create a gate with two states,
`not_evaluable` and `pass`, and no reachable `fail`. The budgets were never frozen. A
gate that cannot fail is not a gate; it is a note. For the life of the program the
performance question was formally deferred, and deferral was indistinguishable from
progress.

### 3.2 The tool disclaimed its own output, and the disclaimer was accepted as licence

Every cycle run printed, and the stopped session's trajectory records it verbatim:

```
provenance class      assumed
parameters by class   {'assumed': 106, 'characterized': 7, 'datasheet': 1}
NOTE: this result depends on assumed machine values and is not a performance claim
```

106 of 114 machine parameters are graded `assumed`. The tool was right to say the number
was not a performance claim. But "not a performance claim" was read as "not a number I
need to reason about", and so 0.225 tokens/s was produced, logged, committed and never
divided into 10,000.

The provenance system was built to stop unfounded claims going out. It also, unintentionally,
gave every founded alarm a reason to be ignored.

### 3.3 Relative improvement replaced absolute target

The reported progress was that row folding took the Qwen decode from 5.095e9 cycles to
172.36e6, a 29.6x improvement. That is a real and substantial engineering result. It is
also 29.6x of the wrong quantity: it moved the machine from 0.0076 tokens/s to 0.225
tokens/s, and the target is 10,000.

A ratio against your own previous number always looks like progress. A ratio against the
requirement is the only one that tells you whether to keep going or to stop and redesign.
The program tracked the first and had formally excused itself from the second.

### 3.4 The fabric was never sized against anything

`git log --follow configs/hardware/abi3_capability/rom_qwen3.json` returns four commits.
None of them contains a sizing calculation. Searching the documents for a derivation of
tensor width from a throughput requirement returns nothing.

The advertised widths are, across the four capabilities:

| capability | tensor | vector | attention |
| --- | --- | --- | --- |
| `rom_qwen3` | 512 | 256 | 128 |
| `hbm_sram_single_chip` | 256 | 128 | 64 |
| `rom_deepseek_v4` | 8192 | 4096 | 2048 |
| `rom_deepseek_v4_array_32` | 256 | 128 | 64 |
| `hbm_sram_cluster_32` | 256 | 128 | 64 |

These are powers of two in a fixed 4:2:1 ratio. They read as a shape someone chose, not
a width someone computed. Meanwhile the governing ADR describes "the 256-lane shared
datapath" at line 643 and "the 256 lanes" at line 178, while `rom_qwen3` advertises 512.
The document and the configuration disagree about the machine, and nothing checks them
against each other.

### 3.5 The measured engine rate was accepted as a fact of nature

`engine.tensor.work_per_lane_cycle` is 0.34587860192585124, graded `characterized`,
measured from one `ot_ta_matmul_bf16_sram_engine` retiring 33,554,432 work units in
97,012,165 cycles. That is roughly 2.9 cycles per work unit, where a pipelined
multiply-accumulate should retire one or two per cycle.

Because the number is `characterized` it outranks everything in the grading system, and
the grading system's whole purpose is to stop people replacing measurements with wishes.
So the slowest possible reading of the datapath became the machine's permanent rate, and
the obvious question — why is a MAC taking three cycles, and what would it take to fix
the RTL — was never forced by any gate. The provenance hierarchy is correct about
epistemics and silent about ambition.

### 3.6 Correctness governance crowded out the performance question

The repository's machinery is genuinely impressive and almost entirely pointed at
correctness: token-identical oracle comparison, source-currency binding by SHA-256 for
every artifact, an independent second-opinion schedule checker, prose-figure provenance
with a 3,279-candidate census, a 24-item comparison fairness audit, deterministic rebuild
proofs, inverse reconstruction proofs.

Not one of those polices speed. The result is a program that can prove, to a very high
standard, that a machine four orders of magnitude too slow computes exactly the right
tokens.

## 4. What the comparison inherited

The project exists to compare a mask-ROM design against an HBM design. On the Qwen pair
the ROM chip is advertised with 512 tensor lanes and the HBM chip with 256.

`docs/COMPARISON_FAIRNESS_AUDIT.md` contains 24 audited items. Item A10 concerns "ABI3
executed lanes: a 512-token program block against an 8,192-token one", which is program
block size and a different quantity. **The 2x tensor-width asymmetry between the two
chips under comparison is audited nowhere.**

This may be defensible under an iso-area argument: a ROM design spends no area on DRAM
controllers and may legitimately buy more compute. But it is not argued anywhere, and an
unargued 2x in the numerator of the headline ratio is exactly what a fairness audit is
for. Note the direction of the error: it flatters ROM, which is the conclusion the
project would like to reach.

## 5. The cost

From `/home/ubuntu/.codex/goals_1.sqlite`, across 26 Codex threads on this machine:

- **456,803,790 tokens**
- **340 agent-hours**
- outcomes: 5 complete, 9 blocked, 8 paused, 2 usage-limited, 2 active

The single stopped thread `01a048d7` alone reports `total_tokens` of 1,441,793,764 in its
own trajectory accounting, against an objective set on 2026-09-04 reading "perform all the
cycle accurate simulations and fix any correctness bugs or performance issues, and produce
the numbers that validate the analytical numbers". It produced numbers. They did not
validate the analytical numbers, and it did not stop and say so.

Sampling that trajectory for the target shows the pattern: "north star" appears 655 times
in the final 126 MB, and essentially every occurrence is the agent re-reading the ADR
paragraph that declares the north star non-binding, not computing a tokens-per-second
figure and comparing it.

## 6. What we learn

These are stated as rules because that is the only form that survives contact with an
autonomous loop.

**R1. Every performance gate must have a reachable failing state from the first day.**
An unfrozen budget is not a deferred decision, it is a disabled alarm. If a real budget
cannot be set, set a provisional one that is allowed to be wrong; a wrong target that
fails loudly is worth more than a correct target that cannot fail.

**R2. Report the ratio to the requirement, never only the ratio to yourself.** Any
artifact that publishes a cycle count must also publish tokens/second and that figure
divided by the target. 29.6x of a number 44,000x from where it needs to be is not
progress worth a commit message; it is a signal to stop optimising and start resizing.

**R3. Size the fabric before building the evidence machine.** One page of arithmetic —
work per token, target tokens per second, resulting work per second, resulting lanes at a
plausible clock — would have shown in an afternoon that 256 lanes at 38.8 MHz is four
orders of magnitude from 10,000 tokens/s. That page was never written. Write it first,
put it under version control, and re-check it whenever a width changes.

**R4. `characterized` means "this is what it does", never "this is what it must do".**
A measured rate is a fact about the current implementation and a question about the next
one. When a characterized rate sits far below what the target needs, that gap is itself a
required work item, not a settled parameter.

**R5. Utilisation metrics must always be published next to an absolute figure.** 99.17%
MFU is the most reassuring number in this entire investigation and it is the one that
concealed the problem longest. Efficiency without magnitude is not evidence of health.

**R6. A fairness audit must cover the parameters that set the headline ratio.** Tensor
width is the first-order term in a compute comparison. Auditing program block size while
leaving a 2x lane asymmetry unexamined audits the wrong thing carefully.

**R7. An autonomous objective must carry a falsifiable acceptance criterion.** Of the 26
recorded objectives, the recurring forms are "work autonomously", "continue with the
remaining items", and "finish all". Those cannot terminate and cannot fail. "Produce the
numbers that validate the analytical numbers" was closer, but with no rule about what to
do when they do not validate, it degenerated into producing numbers.

**R8. When the tool says the result is not a claim, that is the beginning of the
analysis.** A disclaimer explains what a number cannot support. It does not excuse anyone
from reading what the number plainly says.

---

## Appendix: how to reproduce the arithmetic in this document

```python
rate = 0.34587860192585124          # engine.tensor.work_per_lane_cycle, sky130 v2
clock = 38_807_100.0               # clock.frequency_hz, sky130 v2
work = 15_134_641_792              # tensor.multiplications + tensor.additions
north_star = 10_000                # tokens/s, ADR line 66

for lanes, cycles, seconds in ((256, 172_357_340, 4.441396),
                               (512, 148_108_696, 3.816536)):
    peak  = lanes * rate * clock
    floor = work / (lanes * rate)
    print(peak / 1e9,                       # Gwork/s
          work / (peak * seconds),          # MFU
          cycles / floor,                   # scheduling loss
          (work * north_star) / peak,       # compute shortfall
          north_star * seconds)             # total gap
```
