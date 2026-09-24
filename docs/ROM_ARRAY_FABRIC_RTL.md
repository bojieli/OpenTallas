# ROM array fabric RTL: package controller and packet router

This document covers the communication and control logic of the
layer-per-package ROM array (docs/ANALYTICAL_REPORT.md, sections 1 and 9). A
token's hidden state moves from package to package over hardware links with
no software on the path. Until this change, each package's control was
testbench code in `rtl/test/tb_hdc_array.sv`: receiving the hidden state,
starting the decode core, sending the result, feeding the token back and
selecting per-user KV slices. That control is now synthesizable RTL, and a
packet router adds switched and multicast delivery:

| Block | File | Role |
|---|---|---|
| package controller | `rtl/rom/ot_rom_pkg_ctrl.sv` | message receive and send, core start/done, per-user context, job queue, argmax reduction, token feedback |
| packet router | `rtl/rom/ot_rom_fabric_router.sv` | N-port switch: credit-based input buffers, table routing, multicast |
| package link | `rtl/rom/ot_rom_pkg_link.sv` (unchanged) | cut-through credit link; the PHY is a delay-line stand-in |
| decode core | `rtl/hdc/ot_hdc_core.sv` (unchanged, a fixed block) | one token of the reduced Qwen3 per start |

The testbench keeps only the package memories behavioural: program, vector
memory, KV SRAM, and the shared weight and constant ROM images. It also
keeps the prompt table (the host) and the checking against the oracle.

## 1. Messages

A message is a run of flits. A flit is 512 bits, one vector-memory word of
16 FP32 elements, and each flit carries a `last` flag. The first flit is the
header. Unused header bits are zero.

| Bits | Field | Meaning |
|---|---|---|
| 7:0 | dest | fabric id: a package, or a multicast group the router expands |
| 15:8 | src | sending package |
| 19:16 | type | 1 = HIDDEN, 2 = RESULT |
| 31:24 | len | payload flits that follow |
| 39:32 | user | user (sequence) id |
| 55:40 | pos | token position of this step |
| 71:56 | idx | vocabulary row of the best logit so far |
| 103:72 | val | that logit (FP32 bits) |

* **HIDDEN** is the header plus 8 payload flits holding the 128-float hidden
  state. `last` is set on the final payload flit only. For a chained lm_head,
  the header's idx and val carry the running argmax of the earlier vocabulary
  parts.
* **RESULT** is a header only, with `last` set. It carries an lm_head part's
  (or the whole head's) best row and logit for (user, pos). Only package 0
  accepts RESULT messages.

## 2. Package controller (`ot_rom_pkg_ctrl`)

The controller does not contain the core. It drives the core's `start`,
`token` and `pos` and watches `done`, `next_token` and `next_val`. It reaches
the vector memory through one word write port and one synchronous word read
port. It outputs the running user's KV slice base (user × KVW words), which
the memory wrapper adds to the core's KV addresses. The KV ports themselves
never pass through the controller, so changes to the core's KV interface do
not affect it. Parameters set the package's role:

| Role | Receives | Sends |
|---|---|---|
| package 0 (`SOURCE`) | RESULT messages | HIDDEN to package 1 |
| body package (a layer or half-layer) | HIDDEN (X) | HIDDEN (X) to the next package |
| lm_head with the last layer, or on its own | HIDDEN (X) | RESULT to package 0 |
| chained lm_head part k < P−1 | HIDDEN (X for part 0, H otherwise) | HIDDEN (H) and the running argmax to part k+1 |
| last chained part | HIDDEN (H) | RESULT (combined argmax) to package 0 |
| multicast lm_head part | HIDDEN (X), from a multicast | RESULT (its part's argmax) to package 0 |

**Inbound, cut-through.** The controller takes a HIDDEN header as soon as it
arrives, even while the core is running, as long as no received job is still
waiting to start. The controller writes each payload flit into vector-memory
words `RXB`.. as the flit arrives. Writing begins on the cycle the core's
finished job is handed over. The core samples `start` on the same clock edge
that writes the last payload flit, so the core starts with no extra cycle.

**Outbound.** On the cycle the finished job is taken, the controller queues
the header and issues the read of payload word 0. The remaining words follow
one per cycle while a 4-flit queue has room. When the package sends both
messages, the RESULT header follows the last HIDDEN payload flit. The queue
drains into the link, and `out_ready` is the link's credit check.

**Read/write interlock.** A body package receives the next user's X into the
same words it is still sending. The controller writes a payload word only
after the outbound message has read it. When the two regions differ, the
core's start waits until all outbound reads have been issued. Because of
this interlock, receiving the next user overlaps sending the previous one.

**Per-user context.** Every package keeps each user's next expected
position. A HIDDEN message whose position is not the expected one latches
`proto_fault`. So does a wrong `last` flag, a RESULT at a package other than
package 0, or an unknown type. Package 0 also keeps, for each user, the
position of the step in flight, the partial argmax reduction, and the prompt
token of the next position. It prefetches that token from the prompt port
when the step starts.

**Token feedback and job queue.** Package 0 always accepts RESULT messages,
so a reduction never waits for the core. It registers the header, then
combines the result with the user's partial argmax. A larger logit wins;
equal logits keep the lower row, as numpy's argmax does. The rule does not
depend on arrival order. When all `RESULT_PARTS` results have arrived, the
reduced token is reported (`tok_valid`). The user's next step,
{user, pos + 1, the next prompt token or the reduced token}, then either
starts directly or enters a ready-job queue. New users go first, then queued
steps, then a step completing in the same cycle. A user stops after
prompt + generated − 1 steps.

## 3. Packet router (`ot_rom_fabric_router`)

* **Ports and buffers.** The router has NP ports. Each input port has a
  BUF-flit buffer. An upstream sender uses the buffer in one of two ways. A
  remote sender holds BUF credits, spends one per flit and gets one back per
  `in_credit` pulse. An adjacent sender watches `in_ready`, which is decoded
  from registers only. A flit sent with no credit latches `overflow`.
* **Routing table.** The table has DESTS entries. Each entry maps a
  destination id to a set of output ports. Reset loads the table from a
  parameter, and a write port can change it. The destination set of every
  flit is looked up when the flit enters the buffer, so the allocator never
  decodes a header. An id with an empty set, or at or above DESTS, is
  drained and counted (`drops`).
* **Wormhole switching with atomic multicast.** The allocator grants a
  packet all of its output ports in one cycle or none of them, and the
  packet holds them until its last flit. A flit advances only when every
  port in its set can take it, so all copies leave in lockstep.
* **Allocation.** The allocator makes one grant per cycle. A round-robin
  pointer names the priority input. While that input waits, the ports in its
  set are reserved, so unicast traffic cannot starve a multicast packet. The
  pointer moves on only when its input is granted or has nothing to send.
* **Outputs.** Outputs are registered and use valid/ready. In an empty
  router, a header written into a buffer leaves three edges later. Body flits
  follow one per cycle.

## 4. Credit flow

| Hop | Mechanism |
|---|---|
| controller → link | `in_ready` of `ot_rom_pkg_link` is its credit count ≠ 0. The link's receive buffer returns one credit per flit it drains. |
| link → router input | The router's `in_ready` (a free slot, from registers). |
| router output → link | The registered output holds `out_valid` until the link's `in_ready`. |
| link → controller | The controller's `in_ready`. A HIDDEN payload waits in the link buffer until the core is free. |
| router → remote router | Credit counter initialised to BUF, with a registered `in_credit` pulse per freed slot. |

The link models its credit return as immediate. A real return crosses the
channel, so the credit count must cover the round trip for full rate. The
link's own campaign checks this.

## 5. Ordering

* Messages from one source to one destination arrive in the order they were
  sent. Links are FIFOs. The router keeps each input's packets in order and
  never interleaves two packets on one output.
* A multicast packet reaches every port of its set in the same order
  relative to that input's other packets.
* Different sources are not ordered with respect to each other. The only
  consumer that merges sources is package 0's reduction, which is
  order-independent.
* Each user's positions arrive in strictly increasing order at every
  package. The controller checks this in hardware.

## 6. Deadlock freedom

**Inside one router.** A packet holds its outputs only after it has been
granted all of them (no hold-and-wait between ports of one router). The
reservation pointer bounds how long any input waits, provided every output
drains.

**Message-dependent deadlock at the packages.** A package can hold a HIDDEN
payload in its link buffer, but only until its core finishes. The core runs
from local memories and does not need the network. The finished job is sent
as soon as its link has credits. RESULT messages are always consumed. The
remaining risk is a cycle of full buffers, where every package in a ring is
blocked sending into a full buffer. A ring (or the star's up- and
downlinks) whose buffers hold C flits in total can fill only if C flits are
in flight. Each user has one step in flight, which is at most one 9-flit
HIDDEN copy per destination plus the RESULTs. So an array is deadlock-free
when the flits all users can have in flight (nine per HIDDEN copy) are fewer
than the buffer capacity of its smallest cycle. This bound holds for every configuration in the campaign,
including the stress runs with twice as many users as packages.

**2-D mesh (wafer).** For unicast traffic on a mesh of these routers,
program the tables for dimension-order (XY) routing. The channel-dependency
graph is then acyclic (Dally and Seitz). Multicast needs a rule because
lockstep replication couples branches. Here is an example. Package A, at
column x, injects a packet whose set is {east, north}. Package B, at column
x+1 of the same row, injects a packet whose set is {east, west}. B's west
branch turns north at column x. A holds the north port at x and waits for
the east port at x+1, which B holds. B holds that east port and waits for
the north port at x, which A holds. The rule for a mesh, without virtual
channels, is one of the following:

1. Replicate only at the local ejection port, with at most one network port
   per router. The multicast becomes a path through its destinations, and
   the path must follow one dimension order.
2. Have the source send one unicast per destination. This costs the source's
   injection bandwidth but not the network's.
3. Replicate asynchronously with virtual cut-through. This is a future
   router mode. Buffers must hold a whole message. A packet is admitted only
   when the next buffer can hold all of it, and each branch drains
   independently. Waits are then on buffers, not held channels, and XY-tree
   multicast is deadlock-free.

The array configurations in this document use only the point-to-point ring
and a single switch. They need none of these rules.

## 7. What the PHY stand-in abstracts

`ot_rom_pkg_link` implements only the digital framing, the credit flow and
cut-through forwarding. Its `CHANNEL_CYCLES` delay line stands in for:

* the SerDes: serialisation, clock and data recovery, equalisation, lane
  deskew;
* forward error correction: encode and decode latency. The stand-in link is
  error-free;
* link-level retry: CRC, a replay buffer, and acknowledgement. The
  controllers and the router assume a lossless, in-order link, which a retry
  layer provides at the cost of the replay buffer and added latency on an
  error;
* the credit return channel, which is modelled as immediate, and clock
  domain crossing.

The prompt port (the host), the routing-table write port, and the extra
vector-memory word ports are interfaces, not implementations. The vector
memory's two 512-bit ports exist in the behavioural memory only.

## 8. Verification

`tools/rtl_hdc_array_campaign.py` (record: `results/rtl/hdc_array_campaign.json`)
runs every configuration under Verilator, token-exact against the torch
oracle. In each run, every user starts from an empty KV cache, runs the
16-token prompt and generates 3 tokens:

* **Point-to-point:** 4, 5, 6, 10 and 12 packages, as before, now under the
  RTL controller. Each configuration takes the same or fewer cycles than the
  behavioural control it replaces. The record lists the cycles.
* **Switched through one router:** the 6- and 12-package arrays with the
  lm_head parts chained, and with the last body package multicasting its
  hidden state to all parts at once. The parts then run in parallel, each
  applying the final norm itself. Each configuration runs with every user
  and with one user.
* **Stress:** twice as many users as packages, so messages queue at every
  package, with every controller link port held off at random. This runs
  point-to-point and switched with the multicast lm_head.

**Multicast effect.** With one user, multicast shortens each token step by
the chained parts' serial compute and hops: from 32,681 to 28,461 cycles at 6
packages, and from 34,045 to 27,529 cycles at 12. With every package busy, the ring
is limited by its slowest stage. Multicast then changes throughput only
slightly, because the parts' extra final-norm work is off the critical
stage. Moving the norm onto the last body package instead would make that
package the new bottleneck. That variant was measured and dropped. The
record's `multicast_effect` table gives the ratios.

`tools/rtl_rom_fabric_campaign.py` (record: `results/rtl/rom_fabric_campaign.json`)
lints both blocks. It then runs the router's random-traffic testbench
(`rtl/test/tb_rom_fabric_router.sv`) over 3, 5 and 8 ports, buffers of 1 to
4 flits, receiver readiness down to 30 in 100 cycles, and the routed 512-bit
width. Each run checks credits, payload integrity, wormhole contiguity,
per-input order on every output, exact multicast delivery sets, and drops.

`tests/test_rom_fabric_rtl.py` checks that both records pass and are current
against the source hashes. It also checks that the ASAP7 records were routed
from the same sources.

## 9. Physical

Both blocks were routed on ASAP7 with `tools/run_abi3_physical.py` at a
0.9 ns target with block I/O false-pathed. The records are under
`results/physical_abi3/asap7/rom/<top>/`.

* `ot_rom_fabric_router`: 5 ports, 512-bit flits, 4-flit buffers, a 32-entry
  table. It closes at 1,195 MHz with a 40 in 100 slew margin
  (`--slew-margin-percent 40`); without the margin it reached the same clock
  but left max-slew violations. Standard-cell area is about 10,100 µm², of
  which the five input buffers and output registers are most of the 13,226
  flip-flops. The critical path runs from a buffer read pointer through the
  allocator to the drop counter.
* `ot_rom_pkg_ctrl`: the superset configuration (package 0 reducing four
  parts, sending HIDDEN and RESULT, combining a running argmax), with the
  core as an external port bundle. It closes at 1,162 MHz with no margin
  options, at about 3,400 µm². The critical path is the reduction: the
  registered RESULT's user selects that user's partial argmax, compares it,
  and writes it back.

Both records are acceptance `pass`: setup and hold met, and zero DRC,
antenna, max-slew, max-cap and max-fanout violations.

## Reproduce

```
python3 tools/rtl_rom_fabric_campaign.py
python3 tools/rtl_hdc_array_campaign.py
python3 tools/run_abi3_physical.py --view asap7 --top ot_rom_fabric_router \
    --source rtl/rom/ot_rom_fabric_router.sv --clock-period-ns 0.9 --false-path-io \
    --slew-margin-percent 40 --stages synth,pnr --output <dir>/physical.json
python3 tools/run_abi3_physical.py --view asap7 --top ot_rom_pkg_ctrl --source rtl/rom/ot_rom_pkg_ctrl.sv \
    --param SOURCE=1 --param RESULT_PARTS=4 --param SEND_HIDDEN=1 --param SEND_RESULT=1 \
    --param COMBINE_IN=1 --param ROW0=1024 --param TXB=8 \
    --clock-period-ns 0.9 --false-path-io --stages synth,pnr --output <dir>/physical.json
python3 -m pytest tests/test_rom_fabric_rtl.py tests/test_hdc_rtl.py
```
