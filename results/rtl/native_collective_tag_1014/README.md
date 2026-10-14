# Native collective identity audit

This is a blocking source audit, not a transport qualification. Exact file SHA256 values and commits are in `source_inventory_and_collisions.json`.

The native controller instantiates `ot_qwen_tp_seq_w12_vrl` with NW18, DAW6 and TAGW32. The sequencer's concatenation `{tok_r, pos_r[7:0], {(8-DAW){1'b0}}, seg}` has 34 bits. Assignment to 32 bits drops the top two token bits. Tokens 0, 65536 and 131072 therefore have identical tags for identical position/segment, although all are within the 151936-token vocabulary.

Removing the two padding bits preserves the complete token, but provides only eight position bits and no layer or epoch identity. Positions 0/256 and 255/8191 collide. The pre-existing `ot_qwen_tp_seq_w12_fs` source explicitly describes this position and layer alias class; its token8/segment3 encoding cannot substitute for a complete native token contract.

The collective compares complete opaque input tags at both its package pairing and four-package agreement stages. Those checks compare participating inputs to each other; they do not compare a result to the consumer's active full context. The tag is discarded from both engine result paths: peer results contain data512/last/error, and local results contain data512/last/rank3/error. The native FIFO transports that untagged 517-bit local return. The sequencer consumes returns in `S_COLL`, using receive count, last and rank. It has no return tag or context check.

The generic FIFO has configurable WSQ/WCQ widths. A new functional transport can therefore carry explicit identity, but the current collector's WT1 physical column implementation requires TAGW32. Any wider successor needs its own source, tests and fresh physical views. The existing CLOSED profiles remain unchanged.

Complete explicit token18/position13/segment6 identity requires 37 bits; stage6 raises that to 43 bits. Generation width additionally requires an actual lifetime and wrap rule. Neither an arbitrary width nor a source-unproven drain fence is adopted by this audit. The current C++ whole-layer runner drains its orchestrated operations, but that is not an RTL proof against queued context slips or late untagged returns.
