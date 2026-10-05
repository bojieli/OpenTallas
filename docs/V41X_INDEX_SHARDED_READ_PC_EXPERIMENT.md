# Tagged per-PC index read experiment

`ot_hdc_v41x_idx_shard_reader_pc` is an isolated throughput experiment on the
compact four-stack image. It keeps two 64-key output beats in flight. Every
present key has two code-sector descriptors, and every eight-key group has one
scale-sector descriptor. A descriptor tag identifies its beat, quarter, lane
and code/scale part. Each of the 128 pseudo-channels can issue one sector
request per cycle; responses fill a two-beat reorder store, and completed
beats drain in quarter order.

The source-pinned gate passes the paired sharded writer, bridge and four
timed HBM models at N=1, 40 and 65. A separate NPC32×4 timed-HBM run checks
every key of a 1040-key scan, with exactly 2210 sector reads. It takes 1026
cycles: **2.154 sectors/cycle**, or **1.72% of the 125-sector/cycle target**.
The serial correctness reader took 7438 cycles in its short-latency fixture;
those fixtures have different memory timing and must not be compared as a
speedup ratio.

The experiment diagnoses insufficient lookahead. Two beats expose at most
272 sector reads to the HBM queues, while the target rate needs thousands of
outstanding sectors to hide controller and DRAM latency. Extending this
literal beat-by-beat descriptor arbiter to that depth would multiply its
large per-PC priority logic and 64-key reorder storage. A production reader
needs contiguous per-stack range generators with deep per-PC lookahead and a
separate quarter-order collector. The experiment has no physical route and
is not selected by the pooled adapter.
