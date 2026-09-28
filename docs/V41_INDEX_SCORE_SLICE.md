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

## First integrated gates

The [real checkpoint score/select gate](../results/rtl/v41_idx_score_select_checkpoint.json)
uses two reduced-shape layer indexer calls from the released checkpoint.
All 80 BF16 scores and 16 top-8 indices/values match the golden under
ready/valid stalls. A source-pinned turnaround sweep found that the current
single query register requires two idle clock edges between the previous
segment's last accepted key and the next query load. Zero or one edge
corrupts an in-flight score. A double-buffered query register remains open.

The [timed reader/score/select gate](../results/rtl/v41_idx_reader_score_select.json)
joins the four-stack reader to one `NK=4`, 32-head × 128-dimension scorer
and one exact top-8 selector. It checks all 1,040 keys and 2,210 sectors at
the reader boundary, scores quarter 0's 256 keys, and selects the exact
eight lowest indices from the all-zero fixture. It takes 417 cycles, with
48 collector stall cycles. The other three quarters are not scored in this
gate, so this is an integration milestone rather than a full-index service
rate.

The [all-quarter composition gate](../results/rtl/v41_idx_reader_score_select_all.json)
uses the same timed reader and a bounded 64-key beat buffer to serialize all
four quarters through one exact full-dimension `NK=4` scorer. Four separate
W4 selectors choose the local top eight. All 1,040 keys and 2,210 HBM
sectors are checked; all 1,040 scores and 32 local winners are exact for the
all-zero fixture, including the 272-key final quarter. It takes 634 cycles,
with 240 collector stall and 213 stream stall cycles. The final top-32 merge,
checkpoint key image, shipped shape and routed physical path remain open.
This bounded single-slice gate does not establish a production token rate.
