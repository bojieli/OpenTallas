# Interface-control specification

**Document:** SPEC-ICD 1.0

`interfaces.json` is canonical for widths, bit offsets, opcodes, status codes, and
the CSR address map. This document defines temporal and semantic behavior.

## ICD-1 Common conventions

### ICD-1.1 Bit, byte, and field order

Bit 0 is the least-significant bit of a record. Multi-bit integers are unsigned
unless a numerical payload explicitly declares a signed/float format. When a
record is serialized to bytes, bits `[7:0]` form byte zero, `[15:8]` byte one, and
so on. Memory addresses are byte addresses. DMA activation addresses in host
commands are expressed in 64-byte units and are shifted left by six after overflow
and range checks.

All reserved fields transmit zero and read zero. A nonzero reserved field in a
checked input record produces `BAD_FIELD`. Receivers must not infer future meaning
from a reserved encoding.

### ICD-1.2 Ready/valid contract

On a ready/valid interface, transfer occurs on a rising clock edge when both are
one. A producer may assert valid independently of ready and must hold valid and
the complete payload stable until transfer. A consumer may change ready while
valid is zero. Reset clears valid-producing state and does not require ready low.

No module boundary may create a combinational path from downstream ready to
upstream valid. Skid/elastic buffers break paths where necessary. Within one clock
domain, transferred records preserve order unless the interface explicitly permits
tagged out-of-order completion.

### ICD-1.3 Integrity algorithms

CRC16 records use CRC-16/CCITT-FALSE:

- polynomial `0x1021` (the x^16 term implicit);
- initial state `0xffff`;
- no input or output reflection;
- final XOR `0x0000`;
- cover every non-CRC bit in increasing byte order, most-significant bit first
  within each byte;
- the transmitted CRC is the final 16-bit value with bit 15 first in the CRC field.

The CRC field is zero while calculating a known-answer whole-record helper, but
normal hardware simply stops coverage before the CRC field because all records
place it last. The check residue over covered data followed by transmitted CRC is
zero.

Stage packets use CRC32C/Castagnoli over all retained packet bytes, including each
flit's CRC16:

- normal polynomial `0x1edc6f41`, reflected implementation `0x82f63b78`;
- initial state and final XOR `0xffffffff`;
- reflected input/output;
- little-endian transmitted 32-bit value.

CRC detects corruption; it does not authenticate a source.

### ICD-1.4 Error precedence

When multiple checks fail on one accepted record, status precedence is:

1. `BAD_CRC`;
2. `BAD_VERSION`;
3. `BAD_OPCODE`;
4. `BAD_FIELD`;
5. `IMAGE_MISMATCH`;
6. `EPOCH_MISMATCH` (including active schedule-ID mismatch);
7. `CAPACITY_ERROR` or `NO_CREDIT`;
8. operating-state errors.

All observed syndromes may still be counted, but one deterministic terminal status
is returned. Internal uncorrectable errors override a pending success response.

## ICD-2 Host command and response

### ICD-2.1 IF-HOST-CMD

`IF-HOST-CMD` is a 256-bit record on `aon_cfg_clk`. The frontend checks CRC before
any other field and allocates no state until the entire record is accepted and
validated.

`batch_size_minus_one + 1` names a homogeneous group of consecutive session IDs
starting with `session_id`. All lanes share image slot, context, position, schedule,
numeric mode, and layer interval. The activation address points to lane zero; lane
`i` is at `base + i × activation_stride`, where the manifest defines stride as the
64-byte-rounded hidden-vector byte size. The consecutive ID range and DMA range
must not overflow.

`context_tokens_minus_one + 1` allows exactly 1 through 1,048,576. `position` is
zero based and must be smaller than context length and match every session's
expected position. `first_layer` and `last_layer` are inclusive in the command;
the stage accepts only its manifest-owned interval. `draft_tokens` is zero for
ordinary decode and 1..15 for speculative verification.

Flag allocation is:

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `INTERRUPT` | request completion interrupt |
| 1 | `LAST_STAGE` | command expects terminal rather than stage-link result |
| 2 | `DETERMINISTIC` | required for this baseline; zero is rejected for service |
| 3 | `ALLOW_CORRECTED` | allow corrected ECC events without session abort |
| 4 | `DIAGNOSTIC` | legal only for diagnostic opcodes while quiescent |
| 5 | `FORCE_ABORT` | legal only with `ABORT_TRANSACTION` |
| 7:6 | reserved | zero |

The public numeric mode is stored in the configured image/session slot, not a
command flag, preventing an in-flight reinterpretation of data.

For every non-NOP command, `schedule_id` must equal the active schedule identity
published by the schedule controller as well as `epoch_id` matching the active
epoch. Either mismatch returns `EPOCH_MISMATCH` before session lookup, credit
reservation, or service launch. A schedule commit latches its requested ID and
publishes that exact value atomically with the active-bank/epoch change.

### ICD-2.2 IF-HOST-RSP

`IF-HOST-RSP` is 128 bits and returns one record per accepted command in command
acceptance order. Validation failures are accepted commands and receive responses.
Commands not transferred because ready was low receive no response.

The response echoes opcode, epoch, first session ID, common position, and user
cookie. `error_source` identifies host frontend, session, stage controller, HBM,
NoC, tile, stage link, power/thermal, repair, DFT, or internal control using the
source map in firmware headers. `syndrome_class` selects a detailed sticky/logged
syndrome; it is not enough by itself for repair.

Success means required state commits completed. An error means the whole homogeneous
batch did not commit unless the opcode is explicitly diagnostic/configuration and
defines a narrower side effect.

### ICD-2.3 ABI compatibility

Hardware exposes ABI major/minor in `SPEC_VERSION`. Major mismatch is rejected.
A requester minor above hardware minor is rejected unless the opcode is NOP or
capability discovery and all new fields are zero. A newer hardware minor preserves
all existing field offsets, encodings, status meanings, and reset behavior. A
meaning change requires a major increment.

### ICD-2.4 Host trust and DMA

The public reference assumes addresses were authorized by a trusted host/IOMMU.
The accelerator still checks alignment, overflow, stage-local aperture, and
manifest stride/length. It does not implement tenant page tables, encryption, or
host authentication. A product bridge must add those without changing accepted
record semantics.

## ICD-3 CSR interface and map

### ICD-3.1 IF-CSR-REQ/RSP

The 128-bit request supports 1-, 2-, 4-, and 8-byte naturally aligned accesses.
Operation encodings are `00` read, `01` write, and others illegal. A write strobe
bit corresponds to one byte of `write_data`; strobes outside the selected access
size are illegal. One response returns for each transferred request in order with
the original tag.

The response status uses the global status table. Read data outside the requested
byte lanes is zero. A bad request has no side effect. CSR CRC coverage follows
ICD-1.3 in both directions.

### ICD-3.2 Register behavior

The map in `interfaces.json` is a 4 KiB aperture:

- identity, version, capabilities, status, heartbeat, and image ID are RO;
- CONTROL is RW but state transitions remain guarded;
- ERROR_STATUS is RW1C and independent of ERROR_MASK;
- FIRST_ERROR is a windowed snapshot whose read sequence is atomic;
- SESSION_WINDOW accesses only quiescent/configuration metadata, not activation/KV
  payload;
- SCHEDULE_SHADOW_WINDOW and REPAIR_MAP_WINDOW reject active-bank mutation;
- RAS_DFT_WINDOW is RO in service and has explicit test-mode writes through JTAG/
  instrument access, never through ordinary host inference commands.

Multiword snapshot reads latch on the first word and release on the last or after
a bounded timeout. A new snapshot request while one is active returns BUSY.

### ICD-3.3 CONTROL and STATUS essentials

CONTROL bits request service enable, quiesce, resume, warm reset, clear counters,
schedule commit, repair commit, BIST, and safe shutdown. These are requests; STATUS
reports accepted/in-progress/complete/error and the power state. Software waits for
acknowledgement and never assumes a write completed a transition synchronously.

## ICD-4 HBM abstraction

### ICD-4.1 IF-HBM-REQ/RSP

Requests are 128 bits. Operation is `00` read, `01` write, `10` atomic prepare
metadata, and `11` illegal in the public baseline. Size denotes bytes per beat and
must equal 64 for the 512-bit data interface. Burst length is 1..65536 beats and
must remain inside the checked session aperture without 64-bit address wrap. The
16-bit field is a minus-one encoding, so every implementation counter and comparison
on the decoded length is at least 17 bits; `16'hffff` decodes to 65,536, never zero.

Responses are 608 bits. A read carries 512 data bits, one valid bit per byte, tag,
last, error, and CRC. A write acknowledgement carries zero byte-valid bits and
zero data. Error encoding is none, corrected, uncorrectable, poison, timeout,
protocol, or reserved. Reserved errors are treated as uncorrectable.

Responses may reorder between tags but beat sequence is in order within a tag.
There is exactly one terminal `last` per accepted request. The core holds response
ready low only at the async-FIFO boundary; tag/result capacity is reserved before
request issue. A terminal response and a different-tag admission may occur in the
same cycle and must compose to zero net change in outstanding reservations.

### ICD-4.2 Macro boundary

The HBM controller/PHY wrapper translates vendor-specific channels into this
interface. It publishes reset done, calibration done, per-channel capacity,
available bandwidth state, ECC class, temperature/voltage alarm, and BIST result.
Service enable requires all manifest-required channels. A reduced channel set is
legal only after capacity and schedule recomputation.

## ICD-5 Stage link

### ICD-5.1 IF-STAGE-LINK

The logical 288-bit beat contains one exact `IF-NOC-FLIT` and a packet CRC32C field.
Physical serialization is outside the public wrapper. A packet is 1..256 flits;
packet header metadata is carried in the first NoC payload and binds image ID
prefix, source/destination stage, epoch, transaction, packet sequence, flit count,
and virtual channel.

Packet credits count complete maximum-size receive buffers. The sender cannot begin
without a credit and retains the full packet until positive acknowledgement. CRC,
sequence, or framing error returns negative acknowledgement and does not consume
architectural data. Two retries are allowed. A third failure or retry timeout emits
`TIMEOUT`/`INTEGRITY_ERROR`, withdraws service credit, and poisons the transaction.

### ICD-5.2 Link bring-up

After either link-domain reset, both ends exchange protocol version, physical ID,
stage index, image ID, active epoch, maximum packet, credit depth, and BIST status.
Mismatch leaves service disabled. Counters and diagnostic loopback remain available.
Credits start at zero and are granted only after receive buffers and core CDC are
ready.

## ICD-6 Tile and NoC records

### ICD-6.1 IF-NOC-FLIT

The 256-bit flit has 176 payload bits plus type, 12-bit source/destination tile IDs,
epoch, transaction, sequence, terminal, poison, and CRC. Tile ID is stage-local;
the physical route/schedule supplies reticle/stage context.

Flit types are activation, route, partial, reduced result, control, credit, retry,
telemetry, BIST, and idle-reserved. Service schedules never use control/telemetry
types on a service data slot. Sequence starts at zero per packet/collective group
and increments modulo 256 only when the manifest proves the packet fits without
ambiguous wrap.

The static core has no ready. A schedule slot transports the expected flit or idle.
CRC/epoch/sequence/type mismatch poisons the reserved transaction and records a
schedule violation.

### ICD-6.2 IF-TILE-ROUTE

The 224-bit route record carries sixteen 10-bit expert slots. `top_k_count` is
1..16 for a routed operation; slots at or above the count are zero. Duplicate IDs
are legal and collapse to one enable. Any active ID at or above configured expert
count is illegal. Flags distinguish routed/dense, draft/target, and diagnostic;
the remaining flag encoding is reserved.

The route record transfers before activation sequence zero for the transaction and
remains bound until its terminal activation beat has issued or poison drain ends.

### ICD-6.3 IF-TILE-ACT and IF-TILE-RESULT

Activation payload uses the manifest numeric format and zero-pads unused high bits
of a final beat. `word_index` is a logical manifest index, not a physical ROM
address. Sequence is continuous and `last` appears once.

Tile result carries a 32-bit numeric partial in the selected mode plus tile ID,
sequence, terminal, poison, status, and CRC. Status distinguishes good, corrected,
numeric exception, ROM CRC, repair, protocol, and internal errors. Reserved status
is fatal. A producer holds records stable while stalled at the tile boundary.

## ICD-7 Telemetry, interrupts, and diagnostics

### ICD-7.1 IF-TELEMETRY

Telemetry is 128 bits with 48-bit always-on timestamp. Severity is informational,
correctable, uncorrectable, or fatal. Source IDs are stable across ABI-compatible
minor revisions. Fatal/uncorrectable records are never coalesced; informational and
correctable repeats may increment a saturating repeat counter in an accompanying
log entry.

The interface is ready/valid. If lossless storage is exhausted, inference admission
stops. Interrupts are level summaries and remain asserted until underlying sticky
state is cleared; masking changes only the pin/message, not capture.

### ICD-7.2 Diagnostic access

Diagnostics expose image/schedule/repair identities, first and recent error logs,
counter snapshots, BIST signatures, disabled resources, link state, power/thermal
state, and loopback control. Normal CSR access never exposes arbitrary KV or live
activation payload. Test access to representative data paths requires explicit
test mode with inference disabled and is governed by the DFT specification.

## ICD-8 Clock, reset, and test behavior

### ICD-8.1 Domain crossings

The clock on each interface is listed in `interfaces.json`. Cross-domain HBM and
stage-link records pass through async FIFOs; configuration commands/state changes
use async FIFOs or closed-loop acknowledged mailboxes. No valid/ready assumption
crosses a clock domain directly. Reset of either side withdraws credits and causes
a defined resynchronization before new transfers.

The stage integration schedule port is AON-clocked. `schedule_wr_valid` and
`schedule_commit_req` are independent request valids and must remain asserted with
their payload stable until the corresponding `*_ready` is observed. Commit has
priority if both are asserted. A transferred shadow write returns exactly one
one-cycle `schedule_wr_ack` or `schedule_wr_error` pulse after core-domain
validation. A transferred commit returns exactly one one-cycle
`schedule_commit_ack` or `schedule_commit_error` pulse; a legal commit may remain
pending until core quiescence and an epoch boundary. Reset can terminate an
in-flight local integration request; architectural firmware reaches this port
through the protected CSR/boot transaction layer, which reports reset-abort.
Every inactive-bank slot must have been written since reset or since that bank
last became shadow. `schedule_manifest_crc_ok` cannot override this completeness
check. `schedule_commit_id` is stable with the request and becomes the active
schedule identity only on the acknowledged atomic commit.

`image_slot_valid`, `abort_valid`/`abort_transaction_id`, service start/done, and
their payloads are core-domain stage-boundary signals. The 256-bit image-valid
bitmap is coherent core-domain state and is static while service is enabled; it is
not sampled through per-bit synchronizers. `stage_idle` is a core-domain output.
Only its separately qualified internal copy may control AON power/CSR logic.

The service-start payload contains transaction ID, full session ID, allocation
generation, owned layer interval, batch-minus-one, draft-token count, schedule ID,
command flags, and activation address. It remains stable while start valid is
stalled. The allocation generation accompanies all downstream HBM/link ownership
so a late response cannot alias a recycled session. `service_poison` is the OR of
transaction-controller poison and RAS poison and is monotonic for the active
transaction. Service completion is accepted only for the transaction whose
session table entry is busy under the matching generation/transaction ownership.

`boot_control_requests` and the `csr_schedule_window_*`/`csr_repair_window_*`
signals are AON-domain integration boundaries. Bits 0 and 1 of the control word
are consumed locally as service and quiesce requests; the platform boot/DFT owner
must qualify and consume any other implemented request. Window outputs are
accepted CSR transactions, not direct ROM writes. Leaving a platform-side owner
unconnected is an integration gap and cannot be promoted to product closure.

Changing core diagnostics reach AON registers only as one coherent 512-bit
mailbox snapshot. ERROR_STATUS RW1C is converted into an acknowledged AON-to-core
clear transaction; no unqualified clear pulse or independently synchronized
counter bits cross the boundary.

### ICD-8.2 Test access pins

The product boundary reserves TCK, TMS, TDI, TDO, optional TRST_n, scan enable,
test reset, test-mode straps, and per-domain test-clock controls behind a standard
test-access wrapper. The public proxy models instruction/data registers, bypass,
IDCODE, BIST invocation, and result access. Unsupported target scan-compression and
boundary-scan cells remain explicit black boxes, not inferred behavior.
