Production core/cache seam proof (2026-10-13)
============================================

Run tools/qwen_kv_die/xcache_core_bench.sh. It records source hashes and git
HEAD, then compiles the real unmodified ot_qwen_w12_matvec_part twice,
PART1/G4/W16/GT3072/FAST_ISSUE1. This is a production core arithmetic test,
not the entire hardened tile/ROM parent and not native token qualification.

Reference serves synchronous x reads from deterministic finite FP32 VM
values using its actual x_re/x_addr ports. Candidate loads address/value
records, then looks up its actual x_re/x_addr ports, with one registered
response edge. Both use the same synchronous INT8 weight image. Every valid
512-bit t_out arithmetic word and every request is compared exactly.

Profiles include native TP8 QKV/O/GU/down, SMAX11 with k=3 and xjs17, and
split6 with k=9,xjs29, multiple rounds and changing group base. Tile IDs span
source alias/replication boundaries. MEM_EXTRA0 and8 exercise matching data
and tag pipeline delays. Reset interrupts an actual in-flight instruction;
clear invalidates prior records before each new preload.

Fallback proof: core clock is paused when a requested address is absent.
Loader continues on the base clock and fills the exact requested operands.
Both cores, weight service, cache read-response register, and operand extra
stages use the same paused clock. Freezing only issue counters or advancing
cache response on the base clock is incorrect: mq_x can then capture a
response one logical edge before its tag. The candidate response register
uses core_clk and preserves the ordinary one-edge memory return semantics.
Bench includes arbitrary manual pause pairs and126 reactive cache misses,
then compares actual arithmetic throughout. Each positive must produce exactly680 arithmetic words, preventing a
clock-stop or dropped-work subset from passing. A mutant selecting the adjacent
cached data row must fail arithmetic comparison, not just a packet check.

The ot_qwen_xcache_seam associative lookup is a proof vehicle, not a physical
release. DEPTH256 with96-bit address tags exceeds the sink budget and would
need indexed cache leaves or SRAM; do not submit it as one tile. Its interface
establishes the real seam: load clk remains live, read response advances
with the complete core clock, actual read address selects data, and hit
participates in a global pause protocol before the next core edge.

Production integration still owed:
 - Production NW18 requires full18-bit K/issue epoch tags in any general
   fallback; the earlier16-bit epoch helper is bounded native evidence.
 - Native cache tags may be registered alongside x_addr from the pre-update
   k/j state. Sampling u_me.k after the address edge is off by one on wrap.
 - Export currently discarded u_me.x_re/x_addr from the tile logic/control
   leaf and map its native xks/xjs=0 requests to a small epoch-indexed cache.
 - Align the cache's one-edge read response with xl's existing ME_EXTRA path.
 - Build a base-clock scheduler that collects all participating tile hits
   and distributes one coherent, glitch-free core clock enable. The core,
   ROM capture/return pipeline, lane arithmetic, node/tree tags and cache
   response must advance together. No independent per-tile pause is allowed
   while a shared tree combines their results.
 - Use measured ICG/related-clock views and ordinary same-domain checks;
   this functional proof grants no STA exception or forwarded-clock model.
 - For arbitrary legal split/k/j streams, fetch the next required addresses
   into bounded storage, pause the entire pipeline when not ready, and
   resume only after matching tagged data is present. This trades time for
   correctness without reducing SMAX or imposing a new ISA limit.
 - Preserve VM producer ordering and freshness. Native snapshot reuse assumes
   the repeated operands stay stable across eight J slots; qualify this against
   actual SU writes/chase progress. For arbitrary concurrent writes, invalidate
   caches by source version or fetch each real read, preserving its original
   ordering. This bench uses immutable input images.
 - Price the fallback on the actual immutable native program. Native32root
   pingpong mode should not pause after startup; initial preparation and
   real die/VM path delays still require full end-to-end measurement.

The bench's combinational hit -> falling-edge clock mask is simulation
control only. It is not a synthesized clock controller or an inferred ICG
implementation. No claim that the global physical pause network is closed.
