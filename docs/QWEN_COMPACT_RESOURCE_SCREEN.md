# Qwen3-8B compact design: equal-area ROM versus HBM

Status: analytical resource screen, 2026-09-23. No RTL, workload simulation or
physical implementation. It replaces the unfinished v1 screen preserved in the
handoff, which compared ROM only with its own bandwidth sensitivities.

> **Read with [the HC1-referenced design](HC1_REFERENCED_ARRAY_DESIGN.md).** This
> screen prices ROM as storage read into separate MACs under the shipped BF16
> contract. Taalas HC1 shows the organization that actually exceeds 10K tokens/s on
> an 8B model: one die, ≤4-bit select cells, quantized weights. That design reaches
> 15–17K tokens/s for Qwen3-8B and is 7.6–8.4× an equal-area HBM die with the same
> format. The verdict below still holds for the BF16/sequential contract.

## Verdict

**Under the shipped numerical contract, a compact ROM array gives no single-sequence
advantage over an HBM array of the same die area.** Both machines hit the same
888.832 µs sequential whole-K RNE recurrence floor once ROM delivers ≥18 TB/s and
HBM uses at least four 4.5 TB/s dies. The ratio is exactly 1.0 in every feasible row.

Relaxing association (not admitted; the committed BF16 witness gives sequential 0
versus blocked 1) exposes the memory term. Even then, **at the ROM density that
published compiler-class evidence supports, ROM is 0.85–1.38× an equal-area HBM
design that is allowed to choose its own compute/SRAM-cache split.** The 2.0–3.7×
rows exist only at the unqualified 9.38 MB/mm² planning density, and only when ROM
is also granted SRAM-like delivered bandwidth per stored byte.

Aggregate throughput favors HBM further: the ROM dies hold 8K KV SRAM for one
sequence, while the HBM stacks leave room for 738–1,935 concurrent 8K sequences.

## Resources before rates

Each candidate is an array of 815 mm² dies. Per die, the fixed caps from
`rom_hbm_review_v3` (exact functions, reduction, fabric, control, clock/power
reserve) take 270 mm². 8K BF16 KV is 1,207,959,552 B, placed in SRAM at the
config density and split across dies. ROM area per die is 300 or 400 mm²; the die
count is the minimum that holds the full 16.38 GB BF16 checkpoint at each density
class. All remaining area becomes MAC lanes at the unqualified legacy tile area,
which also caps how much weight stream the die can consume (one BF16 weight per
lane-cycle at 65%). A 4×500 mm² ROM layout leaves −33 mm² for compute and is refused.

The HBM counterpart uses the **same dies and area**. ROM area becomes a 50 mm² PHY
plus SRAM; the "optimized split" row lets HBM trade lanes against weight-cache
SRAM to minimize its own floor. HBM delivers an assumed 4.5 TB/s per die; cached
weights get the fabricated GC200 rate per stored byte (47.5 TB/s over 900 MB).
HBM stacks are extra silicon outside this die-area total and are listed as such.

ROM density classes come from the new
[evidence register](../configs/architecture/rom_density_evidence.json):

| Class | MB/mm² | Basis | Min ROM area for checkpoint |
|---|---:|---|---:|
| Compiler, N7, no scaling | 4.30 | TOM Table II compiler ROM, 2048×64 | 3,887 mm² |
| Compiler, N5 bitcell scaled | 5.53 | × 0.027/0.021 µm² HD bitcell ratio | 3,024 mm² |
| Planning (beyond compiler) | 9.38 | Existing assumption; no supporting macro | 1,782 mm² |

The same paper's figures imply only 2.73 MB/mm² for standard compiler ROM, so
4.30 is the favorable end of that source. A fabricated 7 nm UHD SRAM macro reaches
3.65 MB/mm². **Compiler-class ROM is therefore about as dense as SRAM**, which is
why an SRAM-cached HBM design keeps pace with it.

## Results at SRAM-matched ROM delivery

| Density class | Dies × ROM mm² | Lanes/die | Sequential ratio | ROM floor (relaxed) | Optimized HBM floor (relaxed) | ROM/HBM (relaxed) |
|---|---|---:|---:|---:|---:|---:|
| Compiler N7 | 13 × 300 | 48,551 | 1.00 | 24.3 µs | 26.9 µs | 1.10 |
| Compiler N7 | 10 × 400 | 24,997 | 1.00 | 61.4 µs | 52.4 µs | 0.85 |
| Compiler N5 | 11 × 300 | 47,591 | 1.00 | 29.3 µs | 40.4 µs | 1.38 |
| Compiler N5 | 8 × 400 | 23,282 | 1.00 | 82.5 µs | 102.2 µs | 1.24 |
| Planning | 6 × 300 | 42,395 | 1.00 | 60.4 µs | 224.5 µs | 3.72 |
| Planning | 5 × 400 | 18,138 | 1.00 | 169.4 µs | 337.1 µs | 1.99 |

In the relaxed rows ROM is arithmetic-bound: its floor is set by lanes, not by
ROM. The fixed 4.5/18/72 TB/s ROM sensitivities are also in the record. At 72 TB/s,
ROM loses to the optimized HBM design in every compiler-class row (0.13–0.49×);
the planning-density rows need roughly 41–44 TB/s aggregate ROM delivery merely to
break even with the unoptimized twin.

These floors are maxima of independent bounds: tokens/s values are ceilings, not
constructive schedules. A one-die HBM design needs 3,364 µs just to read weights,
so "ROM is 3.8× faster" is true only against a smaller machine than ROM itself.

## What would change the verdict

1. **A numerical contract that admits reassociation.** Without it both designs are
   recurrence-bound and equal. This is a model-quality decision, not a hardware one.
2. **Qualified ROM density materially above SRAM** at an organization that still
   feeds local lanes. Only then does ROM free area that HBM must spend on cache.
3. **Per-lane compute area.** The legacy tile area sets the arithmetic floor on both
   sides; a qualified lane changes absolute times but not the equal-area ratio much.
4. **Energy.** Not priced here. HBM interface energy per bit is several times on-die
   SRAM/ROM read energy; an equal-power comparison may favor ROM and needs its own
   register before it is quoted.

Reproduce with `python3 tools/audit_qwen_compact_resources.py`; tests in
`tests/test_qwen_compact_resources.py`. The
[record](../results/architecture/qwen_compact_resources.json) carries all rows,
assumptions, limits and input hashes.
