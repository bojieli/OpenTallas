# Qwen TP8 HOST and CTRL transport, version 1

The merged TP8 die is replicated eight times. Package control remains on die 0,
with eight generation-qualified completion sources. A local `tk[92:0]` is a
status source; it is not an eight-die completion. The original `ot_qfd_sysctl`
contract is authoritative: AXI-Lite byte address 13 bits (bit 12 selects system
CSRs), 32-bit BAR data and four byte enables; DMA is single-beat 64-bit with
64-bit host addresses. `ot_host_if` remains FMT1, NW18, one context, PLB13,
CTX8192. No descriptor or CQ format changes.

No existing RTL defines an opcode layout for the board adapter's HOST class.
This document defines that missing endpoint ABI. It is separate from the
adapter's flit sequence and credit fields; the existing adapter remains the
only PHY/CDC transport. Payload words are 512 bits, little endian. HOST and
CTRL require independent receive credits and transmit arbitration; stalled
prefill must not block package completion. Adapter W must accommodate the
class bits as well as these 512 payload bits. An NG8 adapter configuration is
not proof that the integration exists.

Every packet has opcode in bits7:0, version1 in bits15:8, and BAR transaction
id in bits31:16. Unused bits must be zero. This is a wire ABI and must be
implemented at the board peer before hardware is released.

| Opcode | Direction | Fields |
|---|---|---|
| 01 BAR_WRITE | board to die0 | address44:32, data127:96, strobes131:128 |
| 02 BAR_READ | board to die0 | address44:32 |
| 81 BAR_B | die0 to board | echoed id, response33:32 |
| 82 BAR_R | die0 to board | echoed id, response33:32, data127:96 |
| 12 DMA_AR | die0 to board | id0, address95:32; len0, size3 are implicit |
| 13 DMA_R | board to die0 | id0, response33:32, last34, data159:96 |
| 14 DMA_AW_W | die0 to board | id0, address95:32, data159:96, strobes167:160; len0,size3,last1 implicit |
| 15 DMA_B | board to die0 | id0, response33:32 |

`qkd_host_axi_packet` captures link input directly into flops and stores four
receive words. Initial receive credits are four; a credit is returned when a
word leaves that queue. AXI AW and W handshake independently. DMA AW/W are
captured independently and combined only after both are present. DMA R/B
remain asserted until the AXI consumer handshakes. One outstanding DMA read
and write is supported, exactly matching the existing host engine. TX has
four initial peer credits. Invalid version, opcode, reserved bits, unsolicited
DMA response, non-last read beat, and receive or credit overflow latch fault.
Reset is a transport epoch: the board flushes outstanding packets at reset;
no old transaction may cross a new reset. Four initial credits apply again.

CTRL will use source-die and destination-die IDs and preserve `tk` exactly:
`{done,gen2,drained,fault,code4,collective_busy,kv_write_flush,token18,val32,cycles32}`.
Die0 snapshots all eight sources into `ot_qfd_pkgctl D8 DONE_REG1`. START
includes token18,position18,generation2,kv_base24. Receivers reject wrong
source/destination and stale sequence within an epoch. Completion still
requires all eight done, matching generation, drained, equal token and value;
errors are fail closed. A link delay or stale status cannot be substituted by
ND1. Reset/boot link-up and boot-ok also need peer reporting.

Prefill is the unchanged `ot_rom_host_ingest` class0 CSR / class1 descriptor /
class2 payload stream. Its sector output is `{data256,addr32,we,v}` (290 bits).
Its descriptor-done completion currently means the engine emitted sectors,
not that HBM committed them. A visibility fence must count real write
completion acknowledgments from controllers before forwarding fenced done.
Returning a queue credit is not a write-completion ACK. Static commands use
`qkd_ctrl_pc.es = {w_v,s_we,bank5,col5,row19,data256,v}`. Decode writes and
embedding static traffic are already users of that physical port, requiring
one bounded credit arbiter at each PC; ingest cannot drive a second port or
OR its valid with the existing source. Sector-to-PC map is low7 logical PC,
local sector address above bit6 for linear KV, with the contract's logical to
physical PC permutation. Static region bit31 and boot marker all-ones are
separate dispatches; exact embedding/rope address decoders remain required.
The four historical ing530 words cannot be tied off or called receivers.

Physical implementation is a wires-only host parent with per-child clock
entries: packet endpoint ck, original host_if ck, prompt SRAM/port leaf ck,
package ctl ck, CTRL endpoint ck, existing ingest clk_h/clk_i/ck, and static
arbiters at each destination PC. Every seam is registered at both pins and
die-placed relays bound reach to min(500um,pair budget). The existing host
777.576x518.376 reservation is a request, not proof of fit: no full-host view
is qualified until the full child census, geometry, assigned pins, CDC,
completion fence, ND8 integration bench and production throughput are proven.

Current delivered RTL implements HOST AXI termination, CTRL8 addressed transport,
sector dispatch, per-PC static arbitration, physical-column completion observer
and descriptor visibility fence. Remaining full wrapper, static receiver/credit/ACK
chains bound into the die, BOOT/reset binding, host_if prompt physical leaves
and complete production composition gates remain explicit.

The implemented CTRL v1 layout is opcode21 STATUS or22 COMMAND, version1,
source die18:16, reserved23:19=0, one-hot destination mask31:24,
per-source sequence47:32. STATUS carries tk140:48 and boot150:141;
COMMAND carries entire original hc229:48 (including original posted pw/dw).
Unused upper bits are zero. Die0 emits seven individually addressed copies of
each command, with the same sequence number; each recipient sees consecutive
commands. Nonzero dies send status changes to die0. Status low32 cycle counter
alone does not trigger traffic, but is preserved in every snapshot, including
final done. Initial sequence is0; replay/gap and wrong source/destination fault.
Initial receiver/transmitter/command credits are4. `seen[7:0]` must be all ones
before package-ready and boot-ok may assert. Shared boot10 bit assignment must
be bound to the existing sequencer `kst` and reset-controller meanings before
composition; this endpoint preserves the bits rather than interpreting them.
No arbitrary multicast delivery is assumed.

`qkd_host_static_pc` consumes unchanged embedding es288 and host write es288
under separate four-entry source credits. A registered pick arbitrates round
robin, then launches against four controller queue credits. Each launched
command records its source and write/read identity in a64-entry in-order FIFO.
Queue-credit returns release capacity; only an ordered physical static-column
event may retire ownership and raise host_ack. All static reads return to the
embedding source because QPIPE forbids host reads. A ghost or mismatched event
faults. `qkd_ctrl_static_commit` monitors actual col_v,col_sr,col_we, delays
ordered events17 HBM-clock edges (the unchanged controller WDONE), then uses
an8-entry Gray-pointer asynchronous FIFO into ck. Reads in this event stream
are ordering markers; write events use the existing native HBM write deadline.
`qkd_ctrl_pc_host` is a separate copied controller variant with that observer;
the original CLOSED qkd_ctrl_pc source/view is unchanged. Full gates must prove
its original scheduler/PHY pins remain exact and then route the new variant.
The ownership FIFO does not bypass any controller credit or completion check.

`qkd_host_ingest_map` uses the actual four-pin sector face, packed as
`{data256,addr32,we,v}` **290 bits** (289 bits is the request payload without
valid). It preserves the exact controller KV map: stack=a6:5, logicalPC=a4:0,
sec=a23:7, j={sec10:8,sec6:0}, bank={j9:7,j1:0},col=j6:2,row=64+sec16:11.
CTX8192 requires sec7=0 and layer<36. Static bit31 uses the original embedding
map for code/scales at ROW0=24427. No memory address is silently truncated.
An all-ones-address marker carries original data65:0 and waits for landed==
issued before leaving. QPIPE write-only and out-of-range addresses fail closed.
Each of128 logical PCs has four tracked source credits; four stack outputs
carry data256,row19,col5,bank5,lpc5,valid (291 bits). Each receiver uses its
logical lpc strap and returns its own credit in a32-bit per-stack chain. A
single global stack credit pool cannot protect a hot PC and is insufficient.
The historical ing530 contract must therefore change to actual291 forward and
32 credit bits per stack, plus128 physical ACK events aggregated at the host.
`ack_n[7:0]` counts up to128 actual host write ACKs in one core edge; it must
come from host-owned physical column completion events, never queue credits.

`qkd_host_visibility_fence` uses that actual ack count in ck and a held
snapshot toggle/ack CDC to clk_h, so multi-write increments cannot tear. It
retains incoming descriptor-done64 in an8-entry FIFO and forwards it only when
landed>=the descriptor's cumulative sector count. Host completion credits are
four. The source engine is unchanged. Queue overflow, completion-credit
oversupply and commit-counter wrap fail closed. Separate per-unit component
benches and an original ND8 package-controller composition bench exist; these
prove component behavior, not full host assembly, physical closure or priced
production layer throughput. Those gates remain required.

`qkd_host_ingest_station` is the actual291-bit receiver at each PC. It captures
the forward word and logical-PC strap without input logic, forwards the word
through registered pins, and emits static es288 only for its logicalPC. The
independent reverse32-bit queue-credit and physical-ACK vectors add the local
bit to the passed vector; duplicate logical-PC contributors fault instead of
losing a pulse through OR. Every direction is two registered edges. One station
plus one static arbiter belongs beside each controller, in logical-to-physical
PC order from the die contract. A credit returned by that station is the
arbiter's host_cr; its ACK is the arbiter's host_ack. The host reduces the four
ACK vectors with a registered popcount into ack_n. Required production proof
includes the actual32-hop chains and relays, hot-PC backpressure, boot checksum,
layer throughput and die timing. Short-loop component throughput is evidence
about the mapper only, not the full physical chain.
