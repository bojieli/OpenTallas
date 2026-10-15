# Default-off delivery lifetime component

This candidate holds IB379 and mode while the VM source reserves a snapshot,
then publishes context16/version32 and requires acceptance of that exact IB by
every participating tile. Offered descriptors cannot overwrite the held one.
VM release requires every recipient bank to be drained and the source's output
and replay transport to be drained. A cache capture is not a retirement event.

`ot_qwen_xdelivery_lifetime_ctrl` and `ot_qwen_xdelivery_ack_bank` default to
ENABLE=0. Historical production masters and views are unchanged. These are
separate prospective hardened leaves, not a flat physical parent. Neither has
an assigned outline, pins, clock delivery, CTS, or exported timing view.

The actual event cache produces one128-bit response for one96-bit packed
four-address query per tile. The four32-bit operands share that capture and
downstream pipeline. It therefore creates one obligation per tile query,
recipient=tile_id, for768 expected tile instances. No four fabricated quad ACKs
are created. Actual full-field straps/events still require composition.
Current seq40/count7 scalar banks have4322 bits each and1985 controller bits,
total71137 for16×48 recipients. Independent admitted Yosys0.52 proc/opt/memory_map censuses
confirm those counts. The old16×192/119521 estimate is superseded; it counted
four independent recipients for a single tile query.
They do not establish mapped area or CTS. Separate child clocks must belong to the live base phase family;
no loader/core domain merge or hierarchy CTS is implied.

Each accepted query creates one obligation carrying a recipient and monotonic
sequence40. Its actual consumer retirement removes one obligation. Retirements
must be in order within each recipient. Duplicate/stale/out-of-order events
fail closed. Full counters provide backpressure. Sequence exhaustion blocks
further issues; it never wraps silently. A recipient seal means that the
producer can generate no future query and all its consumer/replay stages have
been accounted for. Outstanding obligations still block release after sealing.

The producer of a seal must prove the pipeline drain predicate. `core_idle`,
`response_produced`, and `fill_accept` alone do not supply that proof. One cached
word reused by several arithmetic edges cannot be charged as several new
source transactions. Production request/retire and seal wiring remains open.

Actual events use valid/ready or an event queue/toggle crossing. Registered
`op_accept` or response levels held while core clocks pause must be deduplicated
before entering these leaves. The component bench uses accepted one-shot events;
it does not prove that crossing. Reset and context16 wrap require an explicit
transport/replay flush acknowledgement before allocation reopens. The fence
also clears ACK-bank state. A raw reset without a transport fence is insufficient.

The component gate ran via ot-run1GB/1thread on EPYC1,
units `oth-ubuntu-1649381-1791965584` and expanded-mutant
`oth-ubuntu-1735618-1791966295`, both exit0. Twelve held operations cover three
reduced-width token wraps, offered-IB changes before actual acceptance, VM
reservation delay, partial recipient/source drains, ordinary request backpressure,
and an old-version late ACK. Independently mutated source copies fail the
observed assertions: version check, source drain gate, accepted context check,
and accepted IB check, context wrap fence, and outstanding retirement gate.
Source hashes and raw logs are in receipt.json. Independent EPYC4 census units
`oth-ubuntu-1224398-1791966074` (bank) and
`oth-ubuntu-1224399-1791966074` (controller) both exited0.

This is a lifetime component gate, not actual tile+VM composition or a throughput
qualification. The controller serializes whole operations until full drain and
adds reservation/acceptance/release handshakes plus wrap/reset fences. Their
native stall cost has not been measured or accepted. The current serial acceptance
port costs at least768 live base edges to acknowledge768 tiles; this is a
component interface, not a proposed final parallel delivery price. A spatial
acceptance reduction with actual tagged child receipts is required before a
production topology can be qualified. Tile a778c2ba6 supplies the
production accepted IB seam; tile/VM owners are implementing actual event and
snapshot adapters. Full-key cache metadata and its physical status path remain
separately required. No149-bit root ABI, dictionary reinterpretation, all-field
ACK, version-retention adoption, or final v5 fit is claimed here.

The scalar ACK bank also has a capacity gap:48 tiles can issue queries on one
native coherent edge but its port accepts one event per base edge. The distinct
`ot_qwen_xdelivery_ack_vector` alternative captures48 independent issue and
retirement tuples in parallel. Its exact current-source generic census is4370
bits per bank, total71905 with the controller. Its component burst test passes
48 simultaneous requests and48 simultaneous issue/retirements; replacing it
with one-lane capacity or ignoring one stale version fails. Current v3 gates
and censuses ran EPYC1 units1786042/1786073/1786072/1786041, all exit0.

Parallel capacity comes with11094 exact port bits per bank, including all
provenance and ready/status. Registered wide-face transport, source/consumer
event crossing, and physical pins remain unassigned. This alternative cannot
claim full-field routing, cost or48-way throughput from a selected-tile proof.
Tile source b646b9303 bounds legal FAST1/NW18/IL8 operations by2^39 queries,
including direct ROM i_k and zero-encoded full-wrap loop periods. Forty-bit
identity avoids a mid-operation rollover fence; narrowing to32/16 would require
an unsupported ISA constraint. The source emits one query per active coherent
edge. Fifteen outstanding slots could freeze the49-step retirement pipeline;
count7 instead provides127 slots. The actual field/event transport peak and
capacity proof still require measured traces.

Current v4 gates cover48 parallel recipients with49 outstanding queries each,
ordered drain, full40-bit identity and ten observed mutants, including
high-bit truncation and reverting the counter to15 slots. All12 cases pass
their expected positive/rejection checks. Current census/gate units
1408830/1408832/1408829/1408831 ran on EPYC4 with exit0; full unit names and
admission parameters are in admission.json. The earlier seq16 and quad-count
receipts are component history only. Single-unACKed mailboxes still impose
round-trip credit stalls on hits; queued/pipelined actual event transport must
be built and measured before native performance can be adopted.
