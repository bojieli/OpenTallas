# Native PV256 raw-row parallel candidate

This is an opt-in new module pair, not a modification or adoption of the accepted
hstack or hub. Instantiate `ot_qwen_tp8_pv256_pair` with PAIR 0 and 1. Each pair
accepts raw FP8 V[128] and BF16 e[4] plus registered row metadata. Pair 0 owns c
0..127, pair 1 owns c128..255. Issue n-major, c-minor: t=128*PAIR+c+256*n.
The four query heads each have eight independent 16-lane slices. Each slice uses
16 real `ot_qwen_nearhbm_prod` instances, 16 LAT7 FP32 RNE adders, and two actual
128x256 feedback SRAM macros. A feedback address is revisited after128 accepted
rows; the implementation retires after12 cycles. A pending-address scoreboard,
epoch, expected t/c and first/last checks fail closed. The output reads final leaf
sums from the same SRAM after draining. Every512-word leaf is stable under
backpressure; no flop-array feedback or giant output FIFO substitutes for SRAM.

The source-bound EPYC4 run in `/srv/opentallas-scratch/codex/pv256-parallel-1013`
was admitted via ot-run with24GB/4threads and completed exit0. Verilator built
9.52MB C++ per pair. Products use real bit-level RTL; FP32 add uses the existing
LAT-exact IEEE RNE DPI stand-in, whose function and pipeline qualification are
established by the near-HBM unit gates. SRAMs use the provider128x256 simulation
model. Never use DPI modules for synthesis.

At native context8192, the two pairs consumed8192 actual RAW FP8 rows and
performed4,194,304 products and the corresponding canonical serial adds. All
131,072 FP32 leaf words match the golden bit for bit. Each pair accepts/commits
4096 rows; steady feed4096cycles plus initialization/drain and384cycle readout
finishes at4496 cycles. Explicit input/output stalls finish at5196cycles. Peak
inflight is11 steady/10 stalled. Contexts256,257,511,513,8191 also match all leaf
words, including partial final rounds. Epoch, t-order, first, last, busy-start,
and invalid-context mutants trigger actual fault; raw-data corruption causes
four observed wrong leaf words per pair. Individual JSON results, full build
logs, input/source/binary/positive-output SHA256 digests are committed under
`results/arch/qwen_tp8_pv256_parallel_1013`.

This component does not yet contain canonical128-residue tree reduction or
pair0+pair1 addition. It does not prove actual QK/exp e generation or actual HBM
row routing, since e is golden provided here. Its SRAM state is512KiB for both
pairs, excluding reduction storage. Clock, pins, area, routing, and production
whole-attention throughput remain unqualified. Contexts missing an entire owned
residue are explicitly refused: current input contract requires
context_len>128*PAIR+127. No performance ledger or physical adoption is changed.

Optional TREE=1 now reduces128 leaf residues canonically, reusing the same
feedback SRAM and the same LAT7 adders. It reads adjacent source addresses,
issues a node every3cycles, writes its result to a lower address after the
source is consumed, and drains the pipeline between levels. Output out_leaf is
then one512-word pair partial with out_c=0, retained under backpressure. All
1024 native pair partial words match the canonical golden tree. Steady complete
pair computation measures4543 cycles, stalled5225. The same partial contexts
and protocol/data mutants pass. The default TREE=0 full leaf profile was rerun
on this exact source and still matches all131072 words. Results and positive
pair-partial binary fixtures are in the `tree` proof subdirectory. There is no
additional reduction SRAM. Pair joining and reciprocal normalization remain
outside this component.

The production pair now exposes32 separate `slice_clk` entry pins plus the
small controller clock. Each slice's SRAM, products, and adders use its own
entry. A common-clock adapter exists only in the simulation TB. Arithmetic
runs use synchronous related roots; routed insertion, skew, boundary hold,
reset release, and per-entry physical qualification remain outstanding.
