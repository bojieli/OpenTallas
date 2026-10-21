SMXL cache-tail candidate, base fff9933b, 2026-10-20

Scope: mechanism repair only. No price, current-controller, physical, or
production-rate qualification. Preserve the original 15 failed production runs.

Observed original: xl_dsA_6a start4486bank2 -> start4567bank3 -> cachefault4569,
cache_ready01. Exact source3 cache/feed/producer/issuer hashes match fff9933b.
Real producer drain for64rows is272 sectors,80 stream edges. Producer clears
draining at its last sector; packed136 then still has its64th row to emit
and its running state to clear. The minimum actual cache+SRAM replay gives:
last sector received272/emitted63/running1; nextOPEN+1 rejected with running1.
This is an OPEN predicate failure, not a read tag or retire identity failure.

The candidate extends the already opt-in OPEN_IL admission in the feed, before
fixed programme GO: producer_ready AND NOT cache_busy AND NOT open_q. All
three signals and the consuming issuer run on stream_clk. There is no new
stream-to-HBM combinational path or relaxed clock/identity/fault check.
No programme word or GO is stalled; insufficient admission headroom still
causes the existing missed-slot fault. The extra boundary admission tail is
real (up to2 stream edges in the replay); it must fit/appear in the compiled
schedule and current-controller replay before any rate benefit is claimed.

Minimum mechanism proof:282 payload/tag reads at64/60/16/1 rows, both banks.
MUT1 early-open reproduces existing sticky OPEN failure; MUT2 wrong read epoch
and MUT3 wrong retire epoch fail for their own predicates. This is a cache
contract test; integrated guard qualification is the exact production replay.

Exact production replay uses original ing/xw/ids/mem and NI/NX/ND/END, pins
all source files/executable/arguments/event-file hashes, recovers original
fixture golden operands using original JSON operation windows, and decodes
expected GO slots from the ORIGINAL descriptor-table writes. It does not
recompile events, regenerate a price, or silently change HBM pacing. The
legacy SAFE controller in that replay precedes current MC3c; even a pass is
mechanism-only. Every driver<=32, registered boundaries/reach/storage checks
and current MC3c replay remain required before hardware promotion/gating.
