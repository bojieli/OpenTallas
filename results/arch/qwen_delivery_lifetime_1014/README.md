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

The recipient expectation is 768 tiles ×4 quads =3072, pending binding to the
actual native tile/cache event topology. Sixteen banks of192 recipients keep
the declared state below15000 per root: 7346 bits per bank and1985 controller
bits, total119521. These are analytical RTL register counts, not synthesis or
mapped area. Separate child clocks must belong to the live base phase family;
no loader/core domain merge or hierarchy CTS is implied.

Each accepted query creates one obligation carrying a recipient and monotonic
sequence16. Its actual consumer retirement removes one obligation. Retirements
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
unit `oth-ubuntu-1649381-1791965584`, exit0. Twelve held operations cover three
reduced-width token wraps, offered-IB changes before actual acceptance, VM
reservation delay, partial recipient/source drains, ordinary request backpressure,
and an old-version late ACK. Four independently mutated source copies fail the
observed assertions: version check, source drain gate, accepted context check,
and accepted IB check. Source hashes and raw logs are in receipt.json.

This is a lifetime component gate, not actual tile+VM composition or a throughput
qualification. The controller serializes whole operations until full drain and
adds reservation/acceptance/release handshakes plus wrap/reset fences. Their
native stall cost has not been measured or accepted. Tile a778c2ba6 supplies the
production accepted IB seam; tile/VM owners are implementing actual event and
snapshot adapters. Full-key cache metadata and its physical status path remain
separately required. No149-bit root ABI, dictionary reinterpretation, all-field
ACK, version-retention adoption, or final v5 fit is claimed here.
