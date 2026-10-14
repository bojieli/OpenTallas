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
not that HBM committed them. A visibility fence must count the contiguous issue prefix of real write
completions from controllers before forwarding fenced done.
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
per-source sequence47:32. STATUS carries tk140:48, raw kst150:141 and {boot_ok,boot_done}152:151;
COMMAND carries entire original hc229:48 (including original posted pw/dw).
Unused upper bits are zero. Die0 emits seven individually addressed copies of
each command, with the same sequence number; each recipient sees consecutive
commands. Nonzero dies send status changes to die0. Status low32 cycle counter
alone does not trigger traffic, but is preserved in every snapshot, including
final done. Initial sequence is0; replay/gap and wrong source/destination fault.
Initial receiver/transmitter/command credits are4. `seen[7:0]` must be all ones
before package-ready and boot-ok may assert. The existing sequencer `kst` is fault/fault_cause10, not boot state. It is
preserved separately in kst8. Boot2 must come from the actual per-die boot
checksum/visibility check, never from kst or an engine done level. Die0 reads
boot8[2d] as boot_done and boot8[2d+1] as boot_ok for the original reset sequencer.
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
Raw `physical_ack_n[7:0]` counts up to128 host-owned physical column
completion events per edge for diagnostics. Completions on different PCs may
overtake each other, so this total cannot qualify an earlier descriptor.
`qkd_host_commit_order` stores the PC of each admitted sector in a bounded
256-entry issue queue and tracks ordered physical ACKs separately per PC. Only
the contiguous retired issue prefix emits `prefix_v`; `ack_n[7:0]` is that pulse
with seven zero bits. Prefix pulses return ordering credits to the mapper. The
leaf uses control FFs and three registered read stages with at most8:1 selection.
It has its own compensated core clock entry,4639 FFs, and an unverified
129.6x172.8um outline request. Ghost ACKs, overflow and prefix wrap fault.

`qkd_host_visibility_fence` uses that contiguous-prefix count in ck and a held
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
ACK vectors into the completion-order leaf; the separate registered popcount
remains diagnostic. Required production proof
includes the actual32-hop chains and relays, hot-PC backpressure, boot checksum,
layer throughput and die timing. Short-loop component throughput is evidence
about the mapper only, not the full physical chain.

Production CTRL endpoint sets STRAPPED1 and captures die_id[2:0], stable for
the reset epoch, from the package identity strap. One die RTL/mask serves all
eight locations. Compile-time DIE is retained only as the bench/reset default;
STRAPPED0 is a fixed-role component option, not the production package binding.
Every live role decodes the same packet ABI, while only role0 aggregates ND8
and originates commands. Changing die_id during a live epoch is forbidden.

The original sysctl32-bit FAULT_STATUS layout reserves bits16..21 for package
faults and explicitly truncates c_fault_vec to16 bits. With D8 this drops
dies4..7 detailed diagnostics. A full TP8 composition must bank peer diagnostics
separately from global ctl faults; simply changing its D parameter is not a
correct TP8 CSR implementation. The independent qkd_host_ctl ND8 aggregate
and its120-bit result retain the actual package fault flags. This is a required
CSR binding task; component packet tests do not prove the full BAR reset/boot
namespace or host descriptor execution.

The physical HOST PHY binding from die generator T21 is **FDI_FW1043**, not
historical554. The adapter's actual typed flit is
`{valid1,DATA1024,credit_count10,sequence8}` (W1024,RXD512). The complete host
class word is528 bits: class527:524, reserved523:512=0, data511:0. Adapter
DATA1023:528 is zero padding, checked after a full pin capture by
`qkd_host_rx_pad`; a nonzero pad faults and the packet is withheld. The host
requires its own two W546 CDC leaves (528 plus18 known-zero bits), separate
from the ten allocated collective/UCIe XF leaves. TX constant extension is
478 zero bits above the complete CDC word546. All actual FDI fields retain
their original width and position. No real host W1024 view is currently bound.

Class0 carries AXI HOST,1 addressed CTRL,2 ingest CSR,3 ingest descriptor,4
full512-bit payload,5 completion64,6 IRQ level (bit0),7 logical-credit returns.
Class2/3/4 share the original ingest receive window16. HOST and CTRL receive
windows are4 each. Physical adapter credits are a separate window (IBUF4).
Class7 has three byte counts [7:0]HOST,[15:8]CTRL,[23:16]INGEST. Host-to-board
credit words replenish board's ingress windows4/4/16; board-to-host credit
words replenish host's outgoing HOST/CTRL/completion windows4/4/4. Credit
packets use only physical credits. IRQ level updates coalesce to the newest
level; MSI remains the original host_if DMA write. The board resets all
windows with the link epoch. `qkd_host_rx_class` preserves every original
512-bit ingest payload and class. `qkd_host_tx_class` arbitrates independent
four-entry source queues, prioritizes returned capacity, then IRQ changes,
then round robin data. These are separate clock-root leaves. They live on
core ck; the dedicated host CDC pair handles the FDI/core crossing.

Native prefill uses opt-in `NATIVE_ROWS1` on the original32-macro QPIPE2
provider. Original QKV descriptors still encode K/V bases and strides for
CTX8192,HD128,1/2heads. The K drain reads the two words of one token's32-byte
row sector, rather than two dimension bytes from16 different positions. It
uses the same registered macro read/capture stages and original quantization.
Native addresses follow qkd_kv_wq.sec_of exactly. Invalid partial-window rows
are not written, preserving older positions without RMW; completion marks the
last valid sector. The original default NATIVE_ROWS0 is unchanged. Reduced or
malformed descriptor layouts fault (code7) instead of being reinterpreted.

Measured native provider evidence: original BF16 production fixture2layers x
64positions x2heads x128dimensions,2048sectors,5117core cycles,exact. The
immutable QPIPE1 reference remains5105cycles (authoritative old QM report);
ratio1.0024. The old CLOSED QM also took5117, so native format conversion adds
zero cycles to that provider. One-head native exact864sectors; two-head edge
fixture exact1728sectors across layers0/17/35 and partial positions near8192.
The K-lane mutant fails, and default-off original generic image regression is
exact2048sectors/5117cycles. These results qualify provider behavior/cost only;
new NATIVE_ROWS1 physical view, mapper/station/actual-controller composition,
board PHY/CDC and host-end-to-end price remain required. No accepted-cost row
or changed price is implied.

The misleadingly named `qfd_link_adp512` already wraps W1024,RXD512,NG8 and
1043-bit FDI in r3b-io. Its current m5c job is preserved; do not duplicate that
adapter. Reuse its eventual CLOSED view when it fits, or the owning IO stream's
structural slice repair if it fails. The current237.6x777.6 adapter outline
cannot be assumed to fit the host777.576x518.376 reservation. Place it in an
explicit adjacent host adapter strip/slot request, then assign pins from the
actual PHY1043 face. Host CDC pair is additional to the ten collective XF
leaves. A typed1043↔1024↔546↔528 binding with zero-extension checks is mandatory.

The physical DATA face now binds the actual W1024 adapter (`FDI=1043` including valid/credit/sequence fields) through `qkd_host_phy_cdc`. This wires-only composition adds two dedicated W546 PIPE2 CDC leaves with separate writer/reader clock entry pins. It never borrows the ten collective CDC instances. RX captures all1024 bits before checking the upper496 are zero; the entire class528 word crosses as `{zero18,class528}`. TX extends the same546 word with another478 constant zeros. Asynchronous10ns/14ns tests preserve96 words each direction while holding downstream credits and then releasing them intermittently; a TX bit corruption mutant fails exact DATA1024 comparison. This test operates on the adapter's normalized DATA face and does not qualify physical SerDes timing or the NG8 adapter view.

All17 incoming AXI termination fields are sampled at the pin before control logic; all outgoing fields are launched from flops. The measured AXI leaf has3718 flop bits. The packet bundle has separate entry pins for RX class, TX class, AXI termination and CTRL transport, with no parent flops. These four clocks must belong to the same synchronous phase family with insertion compensation at each child. Unrelated clock domains require CDC; the dedicated PHY pair provides it at the PHY/core boundary.

The original default quantizer route is diagnostic evidence only: child_lint reports40728 upper-metal obstructions conflicting with the M5 PG window. Its clk_i22490 sinks have no boundary registers, and all-sink mean512.6ps/spread107.8ps cannot supply a boundary clock reference. Native prefill changes the RTL and requires a new physically partitioned variant, actual PG/window correction, clock entries, assigned pins and a fresh timing/DRC proof.

`qkd_host_ingest_chain` composes the mapper with four stacks of32 pin-registered stations and128 independent static-port arbiters. Each station and arbiter gets a child clock entry; the parent owns no flops or reductions. Reverse capacity-credit and actual commit vectors remain distinct. Separate clock entries serve the diagnostic ACK sum and the completion-order leaf. Only contiguous issue-prefix retirement reaches the mapper and visibility fence. Exact512-sector composition checks every payload, bank/column/row and PC ownership, rejects any visibility count ahead of modeled retirement, and releases the marker only after512 commits. The missing-host-ACK ownership mutant stalls at508 visible writes.

This composition bench uses a scheduler model returning capacity after3 edges and retirement after17 core edges, so its measurements are diagnostic rather than the actual JEDEC controller price. Balanced sectors have573 launch intervals including variable forward depth; a far-PC127-only burst has17151 intervals because four credits traverse the long round trip. The hotspot remains functionally credit-safe but cannot establish production throughput. The original controller's actual WDONE17 **HBM-clock** deadline and exact JEDEC/PHY behavior were independently proved by the controller observer bench. Production trace composition with the actual controller, delivery clocks and immutable5105 reference remains required before cost acceptance.

The visibility fence now captures ACK8, input-valid/data64 and returned output-credit pins before arithmetic or queue control. Its fault OR is registered at the output pin. The asynchronous completion gate and premature-release mutant pass/fail as required after this structural change; the measured fence census is771 flop bits. The extra capture edges affect completion visibility latency and do not change the distinction between queue capacity and physical retirement.

`qkd_host_control_prompt` now supplies the production five-entry wires-only host/CSR/reset/controller/prompt composition. It fixes the full context shape and binds the actual prompt leaf's three-edge response explicitly; the generic fullcontrol default remains available for its modeled fixture. The host leaf therefore uses PB_READ_PIPE4, with the same measured4157 sinks as the former latency1 fixture. Prompt requests and q/fault responses use their own hardened leaf:71 logic FF plus one physical macro clock sink, with an unverified220.08x110.04um outline enclosing the actual174.744x70.470um macro. Exact FMT1 ring and actual macro-cell correction pass through the production wrapper; payload, shortened response latency and disabled correction mutants fail. The original host-control leaf source is imported unchanged from d8f2dd48d so these gates have a durable same-tree dependency.

The static chain now also passes with all128 actual qkd_ctrl_pc_host controllers and their native core/HBM CDC, scheduler and17-HBM-edge retirement observers. All512 posted sectors preserve exact physical bank/column/open-row and independent SECDED PHY288 payloads. Balanced573 launch intervals end at marker cycle1023; the hotspot17748 intervals end at18279. Corrupting the farthest actual completion event's write polarity causes a chain fault, with issued310/landed184. These synthetic balanced/hotspot scenarios prove actual-controller composition; they do not replace the original production-prefill5105-cycle reference or qualify its throughput.

The source-exact banked completion-order gate passes the original BF16 native provider, all128 actual controllers and independent PHY SECDED payload/map checks:2048 sectors in5310 core cycles against the immutable5105 reference (+4.016%). Independent issue-ordinal assertions verify every descriptor sees all its earlier writes retired. One-head and two-head edge fixtures pass864 and1728 sectors in3256 and5560 cycles respectively; these edge workloads are functional diagnostics. The premature-prefix mutant fails the actual-retirement assertion. The earlier5307-cycle cumulative-total result is rejected: a target256 descriptor escaped with actual contiguous prefix255 while total retirement was316. This checkpoint has no accepted cost row: full PHY/class input transport and native QM clock/PG/physical qualification remain required. The ordered mapper census is4457 FFs; its original standalone ORDERED0 component mode remains available for diagnostic benches.

`qkd_host_hc_station` captures the original rawhc182 and CTRL-returned command credit before local decode; its registered cmd_v/hc pins feed CTRL transport. Bits38/113/181 are the unchanged start/PW/DW pulses, with simultaneous pulses carried atomically in one raw command. The source owns four command credits at reset and may issue one nonempty raw command per reserved credit; a source credit returns only after all seven remote copies have been emitted. Source available is registered and cannot authorize a same-cycle cross-block launch. This bounded metadata-source contract must be bound in full control assembly. Uncredited command events fault rather than silently disappearing. The captured runtime die_id permits only role0 to originate package commands; other roles receive hc from CTRL, and changing identity during a reset epoch faults. The376-FF leaf has an unverified64.8x86.4um request and its own core clock entry. Exact36 command events cover all seven pulse combinations, window exhaustion/return, nonzero role suppression and identity mutation; raw-payload mutation fails. Full production control/prompt/CTRL assembly remains a separate required gate.

Full prefill transport is now functionally composed and explicitly fails the unchanged throughput limit. The normalizedDATA1024/class/two-host-CDC path passes2048 sectors in7463 core cycles. The complete original BF16 fixture/driver/seed plus actual NG8/W1024/RXD512/SRAM1/PINREG1 adapters,1043-bit FDI,223-FDI-cycle one-way PHY delay, dedicated host CDC pair, class plane, native provider, four32-PC chains,128 actual controllers, independent PHY SECDED image and descriptor-prefix fence passes in70543 core cycles versus the fixed5105 reference. First/last sector cycles are8927/69682; all eight fences complete. The one-head edge workload passes864 sectors in30503 cycles. A real native quantizer K-lane mutant fails the independent BF16-native source check. These are functional proofs and measured throughput failures, with no accepted cost row or full HOST qualification. The original driver cadence/seed and workload remain; board transport adds physical-four-credit gating and completion-credit packets, and the behavioral board has its own CDC pair in addition to the die pair. Requested833ps core/FDI periods round to832ps in this1ps-resolution bench, matching its original half-period convention. The16-credit INGEST application window spans the full physical round trip and throttles input despite the physical adapter512-entry buffer. Any repair must add real bounded storage/credit termination and remeasure the declared original workload; simply inflating credits, ignoring host input credits or redefining the baseline is invalid. Evidence and exact IO source revision2aa3e0423 hashes are in physical/qkd_host_integration/evidence/transport. The actual control/prompt/ND8 assembly is independently being completed; these prefill gates do not establish it.
