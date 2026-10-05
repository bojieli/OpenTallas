# V4.1 probability producer contract

Status: architecture input, executable Python transport/banking model, not an RTL
cycle measurement or a proposed engine modification. Base main `04e32f09`.

## Actual connection

`ot_hdc_v41x_att_adapt.sv` lines 135, 407–422, 500–518 establish this path:

1. `A_LDX` requests **G scalar FP32 elements** each cycle via `x_re/x_addr/x_q`.
2. Results are rounded into `xbuf[head][row]` (BF16). The adapter drains `l1_v`
   and `l2_v` before starting its attention job.
3. In `A_RUN`, `p_w` gathers two rows across 16 heads from that already resident
   buffer: 32 BF16 values = 512 bits. It holds the row counters when not ready.

Thus the 512-bit P input is NOT the SU-to-VM bandwidth. It is a local readout of
preloaded storage. G=4 at H=16,T=640 requires **2,560 VM issue cycles** before
streaming, even assuming no arbitration stalls. At T=128 it requires 512.
Drain, job startup, actual VM service, QK and softmax latency are additional.

`hdc_replay_v41.py` lines 530–559 emit scale/max, then exp/sum, then PV reading S;
the final denominator and division occur after PV. The so-called probabilities
at this interface are unnormalized exponentials, not final normalized softmax.
The dependency scheduler's wait masks must preserve completion of S writes
before PV loads them. A fused producer that streams before the max is complete
would change the arithmetic/operation schedule and is not approved here.

## Proposed PWORDS2 producer budget

A 1024-bit output needs four rows per head each cycle. This can be supplied by
an **explicit proposed** head × (row modulo 4) organization: 64 banks, 16 bits
per read, each bank depth160 at T640. Existing head-major scalar preload makes
four consecutive writes hit distinct row banks. Load and stream phases do not
overlap. Storage remains20 KiB for this xbuf; this is separate from the engine's
proposed +64 KiB stationary-bank allocation.

This bank topology is a contract candidate, not the physical structure inferred
by current register-array RTL. Current RTL only specifies a combinational gather.
Wires, muxes, SRAM sizes, clock-to-output and broadcast to64 tiles are unpriced.
Two row banks with one read port each cannot provide four rows/head: the executable
model detects5,120 duplicate-bank accesses for a640-row operation. Four banks
have zero conflicts for this access pattern. Other overlap schedules need new proofs.

## Executable results and scope

`tools/v41_pv_producer_contract.py` source-pins the adapter, core and emitter.
Tests use distinguishable nonzero finite BF16 payloads, partial final blocks,
consumer stalls, and a negative insufficient-bank case. These are transport
model tests, not softmax arithmetic or RTL tests.

At640 rows, ideal preload-plus-stream bounds are2880cycles(P1) and2720(P2):
only160cycles saved before additional compute/handshake/softmax cost. This is
**not** a cycle-exact prediction (the actual P1 controller measured312 issue-window
cycles has startup/overlap accounting different from this320 accepted-beat count).
No full-layer speedup is claimed. A pair buffer fed by G4 scalar VM data cannot
produce sustained1024bits/cycle before the preload fence without a different design.

## Decision requested from architecture owner

Prioritize actual VM preload service and the full composed timeline before adopting
PWORDS2. The engine ingress widening may improve a local phase, but does not solve
2,560-cycle scalar preload or SU dependencies. If PWORDS2 is adopted, require:
explicit64-bank xbuf implementation and physical budget; four stationary engine
banks with the proposed guard; exact producer/engine test; and joint cycle accounting.
No core, adapter, engine or SU RTL is changed by this report.
