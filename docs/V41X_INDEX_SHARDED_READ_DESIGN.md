# V4.1 pooled index read path: sharded key image

## Address and order contract

The adopted four-stack image assigns every global key to exactly one stack in
16-key stripes:

```
stack = (global_key >> 4) & 3
local_key = ((global_key >> 6) << 4) | (global_key & 15)
```

Each stack stores its local keys in the existing compact 68-byte format. A
1024-key superblock has 128 scale sectors (eight four-byte scales per sector)
followed by 2048 code sectors (two 32-byte sectors per key). Given a per-stack
base sector and local key `i`, its addresses are:

```
super = i >> 10; within = i & 1023
scale_sector = base + 2176*super + (within >> 3)
scale_slot   = within & 7
code_sector  = base + 2176*super + 128 + 2*within
```

The batch engine's 64-key input stays in quarter order. For a scan of `N`
keys, `Qs=8*floor(N/32)`, quarters 0–2 have `Qs` keys, and quarter 3 has
`N−3*Qs`. Output beat `b`, quarter `q`, lane `l` denotes global key
`q*Qs+16*b+l` when that key is within its quarter. Because `Qs` can be 8
modulo 16, a 16-key output group can straddle two stacks. A group starting at
an 8-key offset needs an eight-key segment from each stack. This is why the
existing round-robin `ot_hdc_v41x_idx_kmerge` and replicated-image
`ot_hdc_v41x_idx_pool_replica` cannot be repointed at the sharded image.

`ot_hdc_v41x_idx_shard_addr` implements the address and quarter mapping. The
source-pinned address campaign checks 8,640 RTL vectors, every key of 21
complete scans, the 8-key offset crossings, local superblock boundaries and
sampled one-million-key positions. A complete scan requires exactly `2*N`
unique code sectors and `ceil(N/8)` unique scale sectors across the stacks.

## Scheduler and collector required for a token gate

For each output beat, form four quarter groups and intersect each group with
16-key stripe boundaries. Each resulting segment has 1–16 keys and maps to one
stack. Issue its two code sectors per key, plus each needed scale sector once;
tag every response with beat, quarter, lane and code-half/scale identity. A
collector joins the two code halves and the scale slot, then releases a
64-key beat only after every present lane is complete. It must keep the
existing `o_kv`, `o_last` and key-refusal semantics.

The stack has 32 pseudo-channels. At 1 GHz, a design that issues only one
32-byte request per stack per cycle would deliver at most 128 GB/s across four
stacks, far below the 4 TB/s modeled aggregate ceiling. The implementation
therefore needs per-channel request queues and multiple outstanding tagged
bursts, like `ot_hdc_v41x_idx_kstream`. It also needs multiple in-flight
output beats: restarting a streamer at every 16-key group would repeatedly
pay HBM latency and re-read the superblock prefix. No throughput or full-token
claim is made until the scheduler/collector is integrated, source-pinned,
bit-exact against the golden, and its physical and HBM timing is measured.
