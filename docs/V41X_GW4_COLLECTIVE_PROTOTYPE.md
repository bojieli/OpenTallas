# V4.1x four-word collective prototype

This prototype increases the full-shape all-gather engine from one to four
64-byte VM words per cycle. A two-tile transpose converts each index-major
four-rank beat to rank-major destination addresses. Four consecutive VM word
addresses have distinct low two bits, so the prototype writes one word to
each static bank per cycle. The four write ports carry **4 × 512 = 2,048 data
bits per cycle**, plus four word addresses and enables. The reduced-shape die
retains its one-word interface and 16-entry receive depth.

The adopted-link exact stage gate at 256 receive entries, two queued transmit
words, one produced word per cycle, pairwise reduction order and blocking
COLL-v1 gives 471 cycles for the 266-flit activation gather and 251 cycles
for the 80-flit output gather. All four die outputs match bit for bit with
zero faults. The previous one-word/depth-128 gate measured 1,220 and 476
cycles on the same payloads. The four-word stage includes the pipelined transpose drain;
an engine-only sink measured 463 and 236 cycles. The stage records are
[`v41_collective_gw4_banked.json`](../results/rtl/v41_collective_gw4_banked.json),
[`v41_collective_gw4_campaign.json`](../results/rtl/v41_collective_gw4_campaign.json)
and the historical one-word reference
[`v41_collective_depth_campaign.json`](../results/rtl/v41_collective_depth_campaign.json).

The focused [DMA and transpose gate](../results/rtl/v41x_coll_gw4_gate.json)
checks 266 and 80 words per rank, one-, two- and five-word partial tiles,
rotating rank bases, backpressure, simultaneous source reads and destination
writes, and completion after a modeled two-cycle bank selector. It checks
every final rank-major word. A simulation assertion rejects package-controller
VM accesses while full-shape COLL owns the VM.
The [back-to-back descriptor gate](../results/rtl/v41x_coll_transpose_reuse.json)
checks a five-word descriptor followed by a 266-word descriptor without reset;
all 1,084 writes and both completion markers are exact.

The tile VM remains a flat behavioral array. Its four write ports are a
functional boundary, not a SRAM implementation. The original 2,048-bit
post-tile bank selector failed pre-route timing at 0.92 ns (−1.498 ns WNS).
The revised transpose stores words by destination bank, so each output lane
is statically assigned to one bank. Its local 16-bit write enables and input
data are registered to avoid shared high-fanout enables. The full-shape die
also registers each bank's output beat and uses bank-local encoded selectors;
its bank sink must remain ready every cycle. The reduced configuration keeps
the elastic output. A separate full-width
static-bank output register passed pre-route timing (+0.807 ns WNS). The
complete pipelined transpose now misses pre-route timing at 0.92 ns by
15.5 ps (75,250 cells, 12,636.4 µm²); its full-width route is running.
The SRAM macro boundary, full die placement and route, and a full-shape token
have **not** passed. The modeled V4.1 token rate must
not be promoted from this stage result alone. The index scan and other
full-token gates remain independent blockers.
