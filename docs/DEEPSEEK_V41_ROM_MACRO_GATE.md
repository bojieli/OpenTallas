# ROM macro gate: density, bank ownership and arithmetic must agree

**Current verdict: the available evidence does not qualify a numeric physical
ROM-array throughput ceiling.** We can derive conditional bounds and reject
inconsistent layouts, but cannot yet attach a demonstrated local ROM service rate
to the proposed N5 capacity. This is a feasibility finding, not a conclusion that
ROM cannot work. It prevents an unsupported comparison with the HBM baseline.

## Evidence that is available

| Source | What it supports | What it does not establish |
|---|---|---|
| `technology_inputs.json`, fabricated density anchor | A cited 28 nm ROM-CIM storage density | Proposed N5 density with wide pooled ports |
| Same file, ROM bandwidth anchor | Simulated 28 nm in-array operation rate, converted to encoded-weight-equivalent service | External digital read bandwidth into separate compute; a matching fabricated density/rate point |
| IHP SG13G2 routed macro | 130 nm drawn array and routed standard-cell periphery area evidence | N5/N4 density, timing or power; memory-compiler periphery; silicon qualification |

The IHP contract explicitly prohibits target-node extrapolation. Its report also
shows why array-only density is insufficient: at the tightest tested successful
routing, the bit array occupies only 14.42–30.89% of total signal-routing die area
for the two small macros. Those percentages are specific to that implementation;
they are not N5 factors to multiply into a new model. Power-distribution overhead
is excluded from that experiment as well.

The technology helper converts CIM operations into encoded-weight-equivalent
service using operations/weight and bits/weight. That is useful for an algorithm
supported by the in-array arithmetic. It does not create a conventional read port
or establish the FP32 rounding/scale contract of this accelerator. Do not combine
CIM bandwidth with unrelated digital compute and storage density as if they were
one qualified macro.

## Bank ownership can dominate the result

Consider a chip that holds R equal expert shards across its assigned layers.
Let its routed-ROM region have aggregate bandwidth B, and let q shards be selected
at the current layer. Two different organizations have very different service:

- **Fully pooled:** all B is usable by those q selected shards. Per-layer read
  time is `q × shard_bytes / B`.
- **Uniform dedicated banks:** each resident shard has B/R bandwidth, which other
  shards cannot borrow. The q selected banks run concurrently; per-layer read time
  is `R × shard_bytes / B`, independent of q.

A real organization may fall between these cases. Pooling requires conflict-free
striping, decoder/mux wiring, ports, buffers and matching compute service. The
fixed-bank case is not a universal property of ROM; equally, perfect pooling is
not a free property of a wide aggregate bandwidth number.

For the 80-chip map with four-chip islands, twenty layers/stage and up to 39
experts/layer/island, a chip has **780 resident expert shards**. Assign a hypothetical
72 TB/s to its routed region solely to isolate bank organization:

| Route | Fully pooled reads across forty layers | Uniform dedicated-bank reads |
|---|---:|---:|
| One selected expert in the hot island | 2.611 µs | 2,036.736 µs |
| Six selected experts in the hot island | 15.667 µs | 2,036.736 µs |

The isolated bank rate is only `72/780 TB/s` per expert shard. The apparent 780×
difference on a spread route is not an achieved architectural speedup: it is the
cost of an unproven pooling assumption. Both numbers exclude compute, fabric,
dense weights and other service. The same 72 TB/s region is hypothetical in both.
A source that counts every installed bank must identify how much of its service
is available to the current token.

The existing analytical framework already discusses a full-array sweep for a
bank-local ROM organization. The new expert-group proposal introduces pooled
service as an alternative; it must demonstrate that alternative physically before
replacing the framework's locality assumption. Neither model is automatically
applicable to every ROM architecture.

## Required architectural resolution

For each candidate region, specify a joint contract:

1. Stored bits, exact format and scale layout, number/depth/width of banks.
2. Which banks serve each output/K tile and which ports can be shared across
   experts and layers, including concentrated routes.
3. Delivered bytes or native arithmetic results per cycle, latency and valid
   numerical semantics. Distinguish in-array arithmetic from digital reads.
4. Total macro/periphery/routing area and compute area with no double counting.
5. Energy per active access/operation, inactive power and physical operating range.

Use the existing small-macro evidence to identify missing costs, not to extrapolate
unsupported advanced-node performance. Continue analytical mapping with labeled
pooling and rate sensitivities while investigating source-supported macro options.
No implementation or simulation should be selected merely because the pooled
sensitivity looks fast. A ROM/HBM several-fold advantage remains unproven.

Reproduce the ownership sensitivity with
`python3 tools/audit_v41_rom_service_ownership.py`; see
[results and input hashes](../results/architecture/v41_rom_service_ownership.json).
The relevant physical evidence is
[the IHP macro report](../results/spice/ihp_sg13g2_rom_macro/REPORT.md) and
[its claim-boundary contract](../physical/ihp_sg13g2_rom_macro/macro_contract.json).
