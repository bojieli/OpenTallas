# V4.1 index stack-major ingest prototype

The sharded key image places each 16-key group on one HBM stack. Within a
stack, local rank `j` maps to global index `64*(j>>4)+16*s+(j&15)` for stack
`s`. A contiguous per-stack reader can therefore stream one range without
holding four quarter contexts in its HBM request arbiter.

`ot_hdc_v41x_idx_stack_major_ingest` atomically fans each 16-key beat to four
score lanes, four keys per lane. It carries only stack ID and the first local
rank of each four-key group; the score output can restore every global index
from that metadata. Backpressure holds the whole beat until every lane is
ready. The module does not buffer raw keys beyond the upstream reader's beat.
It checks the valid-prefix rule and commanded key count.

The current four-quarter index selector cannot consume stack-major scores
directly. Its ports represent *contiguous global-index ranges*, whereas
consecutive stack-local ranks skip over three other stacks. Exact selection
requires four independent local top-512 selectors followed by a global
top-512 selection over their at-most 2,048 survivors. The local selectors
preserve ascending global index within each stack. The global comparison is
`(score descending, global index ascending)` with `-0 == +0`; the final
selected indices are emitted in ascending global index. Any global winner is
in its own stack's local top-512, so this bounded union is exact. Survivor
score/index storage is at most 94,208 bits (11.5 KiB) before implementation
overhead, instead of context-length raw key buffering. Layer-20 candidate
block selection needs a separate analogous merge; each eight-key block is
wholly within one stack's 16-key group.

The standalone [record](../results/rtl/v41_idx_stack_major_ingest.json)
checks 1,040 and 262,144 global keys and the bounded top-K union with ties.
The ingress synthesizes to 814 Yosys generic cells and 88 reset flops. This
does not include score arithmetic, selector memories, HBM controller, or
routing. Its 16-key beat interface is a local tile interface, not 8,704 new
die-boundary pins.

## Throughput boundary

The measured direct contiguous reader gives 28.74 sectors/cycle on one
stack at 65,536 keys (139,264 sectors). The four-context sticky reader was
reported at about 20.08 sectors/cycle on the same one-stack length; its
source-pinned campaign is still pending. These are reader measurements, not
end-to-end token rates. Both explored high-rate variants use about 2 MiB of
four-stack reorder storage; stack-major ingest does not by itself save that
memory. The current reduced `G=4,M=2` pooled score tile needs two result
events per key and is a correctness vehicle. Four direct streams would
require roughly 54 scored keys/cycle, so score replication, selection merge,
HBM contention and routed timing must be measured before crediting a rate.
