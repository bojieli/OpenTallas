# Native B2 SM/VM adapters: prebuild contract

Source baseline ff87cf69f; selected SM 49b00f711, native VM component e9e5498fc,
retained VM8 CP composition 2370c0876. This specification precedes adapter RTL.
All gates for integrated native SM/VM/VM8/quant/router remain OPEN.

The native SM weight request is NOT a VM byte address: req_addr32 indexes
160-byte HBM lines (five 256-bit sectors); req_tag10 is the native 1024-slot
staging ring identity, with MAX_OUT512. Return rsp_data1088 unchanged after
checking the high192 padding bits of the five-sector assembly. Production
REQCR1 permission arrives two edges before req_v. Existing weight_read and
sector_read implement that contract. No VM alias may replace the HBM service.

Normal activation/publication service requests use {we, byteaddr32,
wdata256, bytemask32, tag16}, plus valid (338), and responses
{tag16, we, data256}, plus valid (274). A native hub client has FOUR
outstanding permissions, in-order responses, no combinational ready and no
response backpressure. An adapter multiplexes K ready/valid service issuers
onto ONE hub client, records issuer/tag/echo in a four-entry ownership FIFO,
and restores the exact issuer on return. Four such adapters fit NC4; ownership
must persist until every response returns. No response tag bits are repurposed.
No buffer may be silently overwritten. An unsolicited or mismatched response
faults and suppresses new issues. K=2 is the first minimum test vehicle;
allocation of xload/publication/other users across all NC4 ports is still OPEN.

Wide xload BW8 reads use only eight lanes of the legacy 32x16 interface.
A lane is {valid, sector15}; native VMS needs {valid, mirror, sector15}.
The bridge exposes a LOCAL OFFSET aperture to the legacy client: owned
byte offsets [0,262144), mirror offsets [0,131072). Commands must first be
validated and rebased into that aperture; emitted sectors are translated to
{mirror, mirror?0:sid, offset_sector13}. Upper24 lanes and out-of-aperture
requests are refused. Read credits and responses bind lane b to bank b with
no permutation. VMS RRS3 has exactly10 credits/lane; xload MUST instantiate
W8LQ10, not its default16. Burst ownership and command-aperture retention must
last through request, credit, and response drain. The source BW8 baseword18
cannot address mirror word262144 directly; truncating that bit is forbidden.
Source BF16 WVM32 is NOT an eight-lane implementation and stays unqualified.

VM8 stores opaque2063-bit payloads plus owner192. The NEW payload ABI is
{xw_en1, xw_addr7, xw_grp7, xw_data2048}. This is explicitly packed by a native
producer and decoded by a native sink; width alone does not establish legacy
ABI equivalence. A sink needs an installed expected_owner192 and reserved
SM mask8. It drives actual native SM xw ports from registered outputs and ACKs
only after the SM sampling edge. Permission remains valid through that edge.
Wrong owner, missing permission, invalid group, or nonzero fragment padding
faults. Existing CP wrapper ties tap_ready high, discards tap_owner, and
serially shifts ACKs through cfg; it must NOT be used as the native join.
The NW-W quant/router feeds copy f_su_NE placeholders and require separate
actual source/consumer adapters, not renaming. Their full integration is OPEN.

## Physical and analytical model, before RTL

All new logic defaults to M5 signal/PG cap, face pins M4/M5, parent M6 straps;
no M6 grant exists. Target stage reach <=500um and last die pin segment<=100um.
Each ownership queue and arbitration port is a separate local clock/reset
island (<=15000 sinks); native sink broadcast is eight local registered
stations, never one physical 2063-bit global combinational fanout. A clock
must be locally buffered at each stage and cold reset release coordinated;
no asynchronous reset of payload storage. Added RTL latency: packet issue1,
packet return1; sink output1 and ACK1 after sampling. Extra wire relay stages
must be priced and inserted in real RTL, and credits resized at the owner.

Packet adapter K2 controls <=64 bits/queue plus16 tag+1echo per four entries,
roughly700 registered payload bits, one337-bit issue/cycle and273-bit return.
One local bus crosses a 500um cut: 338+274=612 bits. At M4 pitch0.048um,
500um*(1/0.048)*0.9=9375 directional tracks; single-layer conservative
bidirectional sum ratio0.0653. Wide native read seam has8*(17+257)+8=2200
bits (credit included), ratio0.2347 on that same cut. VM8 payload+owner/ACK
seam2063+192+192+3=2450bits, ratio0.2614. An eight-SM fork multiplied
8x2063=16504 bits is ratio1.7604 and is REFUSED on one such channel:
use shared trunk followed by local eight-way stations with cuts recounted.
These are prebuild local adapter budgets, not a die-wide cut proof. Actual
site locations, relays, fork cuts, clock insertion, SRAM placement and full
native integration must be supplied by the die compiler before route/adoption.

Peak service rate one32-byte sector/cycle/client subject to the four-credit
round trip: min(1,4/RTT) sectors/cycle. No peak line rate or token claim follows.
Wide reads peak256bytes/cycle/group at eight banks, shared among KE5/6 burst
owners; root VM8 serialized readback/publication latency must also be measured.
The production bench must include actual VMS bank/hub memory timing, native
xload conversion, VM8 memory verification/ownership and real destination
ACKs; minimum packet and sink mock tests establish only boundary mechanisms.
No whole-array RTL simulation, ETM placeholder or historical benchmark may
satisfy those remaining gates.

The corresponding eight-lane write translator maps legacy local-offset
{v,sector15,data256,wordmask8} to native {v,mirror,sector15,data256,wordmask8}
(281). Credit and done are separately returned unchanged; a mirror local done
is NOT the global visibility fence (ring mirror_busy/drain is still required).
Its 500um local cut is8*(281+2)=2264bits, ratio0.2415 at the same conservative
M4 capacity. This translator is provided for an actual selected write client;
it does not invent a native SM wide publication source.

Before adding the selected no-ready peer bridge: each of K packet producers
already has four credits per logical port. Reserve four337-bit queued entries
per producer and retain all producer permissions through the return edge.
Queue depth K*4 absorbs simultaneous native valid pulses, while the shared
hub still has only four outstanding. Added ingress storage K*4*337 bits
(K2=2696), local sink count below15000, one additional queue traversal edge.
The service-ready mux above is internal to this bridge; directly connecting
an unstalled native vmq pulse to its req_r would be a data-loss bug. A producer
fifth request before a response faults, never silently overruns. No producer
may release its transaction allocation based on queue dequeue or hub credit.

## Retained xload command aperture (next prebuild step)

A command seat validates GLOBAL WORD base40 / stride32 / n21 / p4 / space2
before translating to the legacy LOCAL WORD aperture. Owned slice window is
[sid*65536,(sid+1)*65536); mirror is[262144,294912). Require p1..8, n>0,
base/stride8-word alignment, spaceVM1, stride<=65536words and the complete
span base+(p-1)*stride+n within one window. Reject cross-window commands,
high-bit aliases, and mirror overflow; P8*K7168=57344 does NOT fit mirror32k.
Native block-dot n must be32-aligned; output fragment-slot allocation must
also fit the actual128-address store (BF16 groups ceil(n/512), FP8 ceil(n/1024),
FP4 ceil(n/2048); groups*8+x_xb<=128).

One command seat captures payload (~115bits), sid/mirror and full owner192;
state tracks SEND then RUN then DRAIN. The lease is retained until native
x_done AND packet/wide/VM8 completion returns home. No next command changes
an aperture while old traffic is in flight. This adds a registered command
edge and serializes command leases (cost must be charged, not hidden).
Fits one local M5/M4 station: <400 clock sinks, <=500um reach, command+owner
~320bits/500um cut ratio0.0342; reset only state/valid, no payload reset.
Caller must obtain real lane-burst and SM publication reservations before
command acceptance; this seat does not invent those allocations. No changes
to golden arithmetic/layout, no global barrier, no queue or response omitted.

## Pipelined native sink, prebuild 2026-10-13

The default sink remains PIPE0 (one outstanding, one beat/3edges). Opt-in
PIPE1 accepts one beat/edge and retains two local stages: xw launch then
boundary-sampling ACK. Add explicit tap_ticket16 / tap_ACK_ticket16 alongside
UNMODIFIED opaque owner192. The root service allocator owns32live entries
(16/bank); ticket={generation11,bank1,slot4}, checked for collision and wrap
reuse. Root matches BOTH owner and ticket and rejects duplicate/stale/per-face
unissued ACKs. The sink never repurposes any of the192owner bits. No published
source field map for those bits exists; a constant command owner alone cannot
identify multiple concurrent beats.

At acceptance edge t the sink registers payload+owner+ticket and launch mask;
at t+1 the real native SM input samples that xw pulse and the sink launches
matching owner/ticket ACK; the root observes the registered ACK at t+2. This is
SM-boundary acceptance, NOT x-SRAM readback. Selected SM front_n has internal
wl/wm/w0 and branch pipelines; its source-defined commit/launch safety remains
a separate gate and must be priced before engine start. Permission and owner
lease remain installed through the sampling edge and final ACK drain.

The additional state is two16-bit ticket registers; one sink's payload+owner
and controls remain below2500sinks, localM5signal/PG, M4/M5faces, independently
buffered localclock/coldreset. No added payload reset. The forwarding channel
is2063+192+16+valid/ready, reverse192+16+ACK, total2482bits: on500um M4 with
9375usabletracks ratio0.26475. Every extra physical relay must preserve ticket,
owner and valid together and be priced in the32-ticket release window. The
flat eight-SM fork is still refused; real local stations/cuts are required.
PIPE1 boundary throughput target1664beats in1664accept edges (plus2drain);
positive gate checks every native sampling/ACK edge and equal-owner distinct
tickets, and payload/ticket/early-ACK mutants must fail. Production native
root memory/SMstore price and physical closure remain OPEN.
