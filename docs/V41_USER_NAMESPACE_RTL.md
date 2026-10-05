# V4.1 package-controller user namespace

The full-shape controller profile uses `MAXU=866`, `USER_W=10`, `AW=30`,
and a vector-memory word address width large enough for per-user staging.
The reduced profile keeps its existing 8-bit user ports and header layout.

The low eight user-ID bits remain in header bits 32–39. The remaining bits
follow the address field, at bit `40 + 3*NW + 32 + 16` (bit 136 for `NW=16`,
bit 151 for `NW=21`). Later header fields move with `NW` so the full-shape
position, argmax index, token, address, and user extension do not overlap.
`core_user` is the registered user of the running core job, valid with
`core_busy`; the die can use it to select that user's packed-KV and index
regions. A bad inbound ID is faulted and cannot write a valid user's SIDE
staging slot or update its state.

The [source-pinned controller gate](../results/rtl/v41_user_namespace.json)
runs both `NW=16` and `NW=21`. It distinguishes users 1 and 257 (same low
eight bits), checks user 865 and the 866-user source schedule/completion
counter, and rejects invalid user 866. This establishes controller namespace
behavior only. Die host wiring, index sharding, packed-KV physical placement,
HBM capacity, scheduling, and throughput require separate gates.
