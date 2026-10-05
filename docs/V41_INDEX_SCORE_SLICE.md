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
ready/valid stalls. The slice now exposes `ql_ready` and rejects any query
load while an earlier score is still in flight. The checkpoint bench waits
for this permission before loading the second query. A fixed-gap probe shows
that the tested gaps from 0 through 40 clocks are unsafe for this case; 48 passes. The
protocol, rather than that case-specific gap, controls query lifetime. A
double-buffered query register remains open for overlapping segments.

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
W4 selectors choose the local top eight; a bounded 32-candidate buffer and
fifth W4 selector merge them into the global top eight. All 1,040 keys and
2,210 HBM sectors are checked; all 1,040 scores, 32 local winners and eight
global winners are exact for the all-zero fixture, including the 272-key
final quarter. It takes 720 cycles, with 240 collector stall and 213 stream
stall cycles. The checkpoint key image, shipped shape and routed physical path remain open.
This bounded single-slice gate does not establish a production token rate.

## Service and storage contract before replication

The measured four-stack reader delivered 262,144 keys in 9,278 cycles
(28.25 keys/cycle mean), or 557,056 32-byte sectors (60.04 sectors/cycle)
with an always-ready sink. Its output is a 64-key burst, so its mean is not a
per-cycle arrival bound. The N=1,040 combined gate observes 240 collector
stall and 213 stream stall cycles with one 4-key/cycle score slice; its 720
cycles include the local and global top-K tails. No wider reader/scorer
composition has been measured.

Each `NK=4` slice accepts one four-key beat per cycle with no sink stalls in
the standalone test, first output at cycle 48. It contains 512 32-element
FP4 dot units, equivalent to 16,384 logical FP4 MACs/cycle, plus 17,920
query bits and a 64-entry score-metadata FIFO (2,240 bits at IW=30). It
requires 2,176 key bits/cycle. Its query RAM is single-buffered: `ql_ready`
permits a new query only after outstanding scores drain; violating that
protocol is a simulation fault. The real-checkpoint two-query gate passes
with this handshake, while fixed early reloads fault.

The 64-key reader beat needs a 34,816-bit (4.25-KiB) staging buffer if a
downstream slice cannot accept the whole beat. Eight slices would provide a
nominal 32-key/cycle service (8,192 cycles for 262,144 keys) and need 17,408
key bits/cycle, 4,096 dot units and 17.5 KiB of replicated query storage.
Sixteen slices would provide 64 keys/cycle (4,096 scan cycles), with 34,816
key bits/cycle, 8,192 dot units and 35 KiB of query storage. These are
logical lower bounds before routing, bank conflicts, HBM timing, head-sum
tails and selector service. The existing four-stack range streamers already
reserve 2 MiB of reorder storage per die at the measured configuration.

The proven selector evidence is separate: this gate has four local W4/K8
selectors and a W4/K8 final merge. The wider candidate-selector campaign
ingested 64 scores/cycle without input stall for N=262,144, then spent 8,270
cycles in its tail (12,366 total), but that block and K configuration are
not this local/global selector chain. A shipped top-K service rate needs the
actual K, candidate format, finite queues and a same-controller integration
gate. The measured reader and scorer imply that a 32-key/cycle assembly is
the smallest *throughput candidate* at the current reader mean; only a
physical and whole-layer schedule can justify allocating eight slices.
