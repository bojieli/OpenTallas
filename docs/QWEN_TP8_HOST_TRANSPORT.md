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
class2 payload stream. Its sector output is `{data256,addr32,we,v}` (289 bits).
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

Current delivered RTL implements only HOST AXI packet termination. Remaining
CTRL/start/status, BOOT reporting, ingest dispatch/arbiters/real controller ACK,
host_if prompt physical leaf and full composition gates remain explicit.
