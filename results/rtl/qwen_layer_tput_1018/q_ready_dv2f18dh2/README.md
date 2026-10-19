# Production Q-prefetch readiness: BLOCKED

Read-only recovery of `ot-epyc6:/srv/opentallas-scratch/claude/mu-die-qw/dv2f18dh2/out/case`.
GEN source: `0d4c9808fe7d2370185a4313e831b6f59f7a2f75`. Original file SHA256 values are
in `production_q_readiness.json`; exact endpoint/relay and lane cuts are committed
under `../fixtures/dv2f18dh2_qready` with their original provenance in `source.json`.
The progressing physical chain was neither edited nor restarted.

The original GEN transport is proven: W5 `dd_wo` -> native59 `dd_i` has 26 frames,
E19/K2, **20 edges**. Sysface `q_slot` and `q_slot_beat` each have one landed frame,
E1/K3, **2 edges**. Counted relay hops (26/1) are not consumer ages (20/2).
The inspector checks actual endpoint nets, every relay connection, contiguous
frames, frame count, strapped K, GEN E/calendar, and equal slot/beat ages.

SAFE2 source `9f159ab98` (RTL `f8148e431`) requires only external Q prefetch
advance1; D2D CMD/Q output slots stay fixed. Qdd capture/write and prefetch
capture/read both add two internal edges, with same-edge forwarding, so for every
beat b the raw pin requirement is:

`old_qslot[b] - 1 + 2 >= max(W5_Qwrite[b,seat] + 20 for seat in 0..15)`

Equivalently `old_qslot[b] >= last_W5_Qwrite[b] + 19`, for all32 beats, all512 seats.
The current compiler at `4d2cb6301` explicitly lacks the production PW1024/DW8
compute image and the QSLOT relation (`bench_program()` is filler). Thus neither
side of this inequality has production event times. The original GEN also predates
the new SAFE2 native kit; source and physical binding need a successor GEN.
An accepted native CMD conditionally implies committed Q, but a conditional fault
check does not supply the missing production producer/request schedule.

`production_bound=false`, `advance_admitted=false`, `producer_ready=null` and
`request_ages=null` are intentional. This is a bound negative certificate, not an
admission record for calpipe. Synthetic bench events never fill those fields.
The compiler writes `compute_programme/q_readiness.json` before rejecting an
explicit `--q-prefetch-advance 1`; default advance0 retains the existing gaps.
No successful production certificate path is added until its missing compiler
and RTL evidence exists.

Fleet checks: six focused tests PASS (`tests.log`), source syntax checks PASS,
and both standalone inspector and actual layer compiler reject advance1 with
a committed failure witness (`advance1_fail.log`, `compiler_advance1_fail.log`).
All checks used admitted 1GB/1thread jobs on the fleet; no local simulation/build.
Full layer compilation was not rerun: this change does not change its calendars.
