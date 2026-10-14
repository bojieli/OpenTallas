The default-off streaming queue takes an actual coherent output step, registered
numeric word512 and registered {has_query,context16,version32,queryseq40}. It has
no output publication toggle or one-unacknowledged mailbox. A live base edge
copies the previous producing edge's word and tag before the source's next NBA
update. This is an explicit same-family phase requirement, not a CDC guarantee.
The source must stop before a producing edge when credit is low; credit reserves
queued entries plus the produced but unposted word. Posting transfers ownership
into durable queue state; retirement occurs only when the downstream accepts the
real queued numeric word. Queue empty alone is not a global quiescence proof.

Four 192-word component scenes each deliver128 query and64 non-query words.
D8 no-stall producer interval191 is one word/base; D2 interval286 retains the
conservative reservation bubble. Full sink stalls reach capacities8 and2 and
recover. No retirement occurs during the initial35 blocked edges. Reset flushes
old queued frames before fresh non-query traffic. Actual minimum produce-to-pop
is two base edges. The component rejects stale prior-edge tags, corrupted tags,
forced query masks, high40-bit truncation, posting-as-pop and missing unposted
reservation. Exact Yosys logical census is1208 Q atD2 and4820 Q atD8.

This source is separate from the frozen mailbox-based queue. It is awaiting the
tile-owned streaming46 metadata source and actual936-word/872-query arithmetic
and ledger binding. No physical phase, native clock ratio, pin/CTS, HOST token,
provider, all-consumer lifetime, or performance qualification follows here.
