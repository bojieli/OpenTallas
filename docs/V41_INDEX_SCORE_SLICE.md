# V4.1 full-dimension pipelined index score slice

The old pooled score bridge accepts one 64-key beat every at least 130 cycles
and writes one vector-memory score per cycle. The new
`ot_hdc_v41x_idx_score_slice` sends BF16 scores and global indices directly
to a ready/valid selector port. It reuses the source-matched exact index
arithmetic already gated against the golden: four 32-element FP4 blocks for
each of 32 heads, sequential binary32 block additions, BF16 ReLU-weight
terms, chunk-8 head sums, and a fixed pairwise tree. The new logic provides
finite metadata credit so backpressure holds the score and its index together.
Refused keys fault and output zero; candidate-masked keys output `-inf`.

One slice at `NK=4` accepts four keys per cycle after query load. It uses
512 parallel FP4 block-dot units, or 16,384 logical FP4 MACs per cycle, and
17,920 query-register bits. The input key bus is 2,176 bits per cycle. Four
slices form the 16-lane quarter beat expected by the existing selector;
four quarters would use 16 slices for 64 scores/cycle. The structural quarter
module preserves the reader's position order and uses an atomic beat
handshake across its four slices. A cheaper eight-slice arrangement would
score 32 keys/cycle and needs a two-cycle 64-key-beat packetizer before the
selector.

The [standalone gate](../results/rtl/v41_idx_score_slice.json) exercises full
32-head by 128-dimension arithmetic. `NK=4` passes 512 keys with one beat
accepted per cycle, 48 cycles to first output and no input stalls. `NK=1`
passes 128 keys while the sink stalls; all indices, BF16 scores, candidate
masks, refusal faults, and last tags remain aligned. The exact real-vector
arithmetic gate is the source-matched
`results/rtl/hdc_v41x_idx_campaign.json` (16,384 back-to-back keys, zero
errors). Four-slice quarter elaboration is checked only at `NK=1`; a
Verilator 4.038 full `NK=4` quarter lint grew to about 58 GiB RSS and was
stopped before a verdict. There is no assembly timing or routed area claim.

At 262,144 keys per die, score-only compute floors are 8,192 cycles for 32
keys/cycle and 4,096 for 64 keys/cycle. The latest four-stack reader measured
9,278 cycles for that key count (28.25 keys/cycle mean). Thus eight slices
could keep up with that reader on average; a faster reader would benefit from
more slices. The selector's 8,270-cycle measured tail and the physical cost
of the score slices remain separate bottlenecks. Final choice of eight or
sixteen slices needs a same-controller reader/scorer/selector gate and a
representative slice route.
