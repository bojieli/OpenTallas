# Direct-start compact index range streamer

The existing contiguous V4.1 HBM index streamer approaches stack bandwidth,
but its command starts at the first key of a 1024-key superblock. A sharded
quarter stream often starts eight keys into a 16-key stripe. Restarting at
the superblock base would read preceding code and scale sectors again.

`ot_hdc_v41x_idx_kstream_range` adds a 10-bit `cmd_skip` in the first
superblock. Its per-PC generators intersect each four-sector column with the
requested scale/code sector interval. The two-bit start offset travels in the
request tag so returned beats land at their original ROB positions. The
unchanged kstream datapath can then join each code pair with the correct
scale. The raw output still includes placeholder keys before `cmd_skip`;
the caller must discard and shift those positions. No HBM sectors are read
for those placeholders.

The source-pinned timed-HBM gate checks every requested key and exact sector
count for starts at 0, 8, 56, 1,000 and 1,016, including a 1024-key
superblock boundary. A 100,000-key range beginning at offset 1,000 reads
212,500 sectors in 7,205 cycles: **29.493 sectors/cycle on one 32-PC stack**,
94.4% of its 31.25-sector raw peak. Four stacks at the same independent
rate would give 117.97 sectors/cycle, an arithmetic projection only.

The next integration needs four virtual quarter ranges per stack, a physical
per-PC arbiter with deep lookahead across them, and a collector that emits the
four quarter groups in beat order. Duplicating all 16 streamers would also
duplicate their ROB memory; the area and route cost must be measured before
such an implementation is selected. No full-token or four-stack throughput
claim follows from this single-range gate.

`ot_hdc_v41x_idx_quarter_ranges` computes the 16 virtual ranges required by
that next stage. For stack `s`, the count of assigned keys before global key
`x` is `16*floor(x/64)+clamp((x mod 64)-16*s,0,16)`. Applying this rank to
each quarter's start and end gives contiguous, disjoint local intervals;
their first local key yields the superblock base and `cmd_skip`. The RTL
geometry gate checks 16 contexts across 138 scan lengths, exhaustively
checking ownership for lengths 1–128 and sampling the one-million-key case.
