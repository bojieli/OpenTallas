# HHP counterpart, same PC input event

KV owner approved qkd_kvs_pc_h_head_p in the same unsigned event. Current immutable HHPkit4 wrapper captures13functional ports/1502bits. CORE_CLOCK=1 leaf text and actualPC=0 parameter remain unchanged; no implicit parameter re-specialization. All incoming/core-input latency +1edge, boot+1, clock/FTclock and declaredstrap passthrough unchanged. One stage per changed master, not +2 simply because two master types change.

Actual qkd_kv_pc_chain_station_b_p at its current defaultPC=0, from the immutable HHP sources:4096edges0differences vs one-edge delayed reference; command-bit2 mutant caught4083edges, reset-bypass caught547;496boot/504writer/496issue. No wholeHHP netlist equivalence, placement or timing claim yet. Fresh HHP synth-only job was launched from a private copy of current kit4, without touching inherited formal runs.

Relaxed geometric feasibility on the existing normalPC full graph: hold2297outputface FF fixed, co-locate all other FF at centre;41928captures max370.58/0bad. New pin→oldinputcapture max377.784. This proves the former ABI span obstruction is removed by a collar; it is NOT an overlap-free floorplan. New synthesis/placement must supply actual legal body positions.
