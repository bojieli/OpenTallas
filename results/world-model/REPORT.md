# Oasis causal frame state, MiniMax-H3, and immutable ROM

> **Result class: deterministic analytical study, not video execution or
> silicon evidence.** OpenTallas cannot currently compile or run either
> model. Every absolute rate below is a tensor-path envelope with omitted
> work; use the storage-attribution ratios to answer the ROM question.

## Executive answer

DiT is not fundamentally incompatible with ROM. The decisive quantity is
how many activation rows reuse each immutable matrix service:

- Released Oasis at a 32-frame window is prefill-like: each of 10 calls
  applies the token matrices to 4,608 patch rows. Its central-envelope
  ROM-only gain is 1.000×.
- A source-derived *candidate* causal temporal-KV transformation reduces
  each call to the current frame's 144 patch rows. It cuts the central
  modeled frame interval by 25.618×;
  that is primarily an algorithmic cache gain, not a ROM gain.
- Once caching removes the full-window recomputation, immutable weights
  become material. With the optimistic current batched-ROM service law and
  spatially local KV, ROM contributes another 2.225×
  over the *same compute and NoC* with weights in HBM. If every cache byte
  crosses the global bisection, that falls to 1.128×;
  under a one-row/per-stream ROM service proxy it falls to
  1.086×.
- A recent public full-clip model such as MiniMax-H3 is much
  less favorable. Even after giving it the official
  inference-only AdaLN precompute and a deliberately favorable four-call,
  90%-sparse control, its ROM-storage attribution stays in
  1.000×–1.000×.
  Dense full-clip arithmetic and sequence communication dominate; there is
  no persistent autoregressive KV cache to turn it into decode.

The user's prefill intuition is therefore correct for **ROM as immutable
storage**: moving a matrix out of HBM adds little when thousands of rows
already amortize one weight read. A hardwired compute-in-ROM datapath is a
different physical claim; the row-reuse sweep shows that its activation
ports and concurrency must be proved rather than inferred from ROM bandwidth.

## Identity and evidence discipline

| Input | Pinned identity | What is actually known |
|---|---|---|
| Oasis source | `etched-ai/open-oasis@f59deef2…` | Public Python architecture and schedule; checkpoint headers unavailable to this study |
| Oasis weights | `Etched/oasis-500m@4ca7d2d…` | Repository revision pinned; payload not profiled |
| MiniMax-H3 source | `MiniMax-AI/MiniMax-H3@d21241f…` | Vendor architecture/model card |
| H3 FL2VA transformer | `MiniMaxAI/MiniMax-H3@42ed227…/FL2VA/transformer` | 535 public tensor headers across 13 shards; 66.280 GB transformer payload |
| Diffusers H3 graph | `huggingface/diffusers@bda3386…` | Forward graph, packed sequence, and denoising schedule |
| Hardware | `leading_node_market.json@8426951…` | Existing assumed/derived N4-class ROM envelopes and published/derived B300 profile |

Local input and executable-source SHA-256 identities are in
`analytical.json.input_identity` and `analytical.json.producer`; the
inventories carry cited external file hashes, and the human source
register is [SOURCES.md](../../docs/SOURCES.md).

## Workload derivation

One fused multiply-add is two operations. Norms, softmax, nonlinearities,
RoPE, scheduler logic, kernel launches, codec work, and I/O are unpriced.

```text
Oasis full axial attention/call = 4 L D (F S² + S F(F+1)/2)
Oasis temporal KV(F)            = 2 · L · F · S · D · 2 BF16 bytes
H3 main linears/call            = 2 N Pmain
H3 dense attention/call         = 4 L N² Iattn
phase time                      = max(compute, storage) + NoC cut floor
ROM attribution                 = Tsame-compute-HBM / TROM
```

For Oasis, `S=144`, `D=1,024`, and `L=16`. The released reference
generator performs ten full-window calls. The cache candidate performs ten
current-frame denoise calls plus one conservative cache-fill call at the
fixed context timestep. The extra pass matters: the final denoise call does
not leave a cache at the timestep used for subsequent context frames.

| Workload | Rows/call | Calls | Tensor operations | Immutable reads | Mutable reads+writes |
|---|---:|---:|---:|---:|---:|
| Oasis reference W32 | 4,608 | 10 DiT + 1 VAE | 37.928 TOP | 12.464 GB | 0.000 MB |
| Oasis causal cache W32 | 144 | 11 DiT + 1 VAE | 1.490 TOP | 13.680 GB | 3.228 GB |
| H3 dense 5.17 s | 38,222 | 49 transformer | 174.796 POP | 1.973 TB | favorable zero-service assumption |

The persistent Oasis temporal cache is 301.990 MB;
31 past frames are read on each cached call. H3 instead materializes Q/K/V
again on every bidirectional denoising call. The 5.17-second case has an
8.055 TB
Q/K/V write-plus-read floor, which is deliberately *not* charged to its
HBM time here.

## What binds at the central W32 point

All entries below are for the DiT phase; VAE decode is added in the total.
NoC is serialized after the overlapped compute/storage core, so the largest
single term and the total need not be the same concept.

| Workload / storage | Compute | Weight | Mutable KV | Storage core | NoC floor | DiT total | Largest term |
|---|---:|---:|---:|---:|---:|---:|---|
| Reference / ROM | 4.501 ms | 0.006 ms | 0.000 ms | 0.006 ms | 7.660 ms | 12.161 ms | noc_serialization_floor |
| Reference / same-compute HBM | 4.501 ms | 0.541 ms | 0.000 ms | 0.541 ms | 7.660 ms | 12.161 ms | noc_serialization_floor |
| Causal cache / ROM | 0.155 ms | 0.006 ms | 0.144 ms | 0.144 ms | 0.263 ms | 0.418 ms | noc_serialization_floor |
| Causal cache / same-compute HBM | 0.155 ms | 0.596 ms | 0.144 ms | 0.739 ms | 0.263 ms | 1.003 ms | storage |

The released W32 path is communication/compute dominated and ignores
where weights live. The cached path exposes a three-way balance:
current-frame compute, mutable KV bandwidth, and placement-dependent
communication. ROM helps only because HBM weight service becomes the
largest counterfactual core term after recomputation is removed.

## Window-length result

| Window | Reference ROM | Cached ROM | Cache gain | Reference ROM attribution | Cached ROM attribution | B300 cached |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.439 ms | 0.477 ms | 0.920× | 1.914× | 1.926× | 2.733 ms |
| 8 | 3.098 ms | 0.477 ms | 6.499× | 1.000× | 1.994× | 2.880 ms |
| 16 | 6.138 ms | 0.477 ms | 12.873× | 1.000× | 2.071× | 3.048 ms |
| 32 | 12.220 ms | 0.477 ms | 25.618× | 1.000× | 2.225× | 3.385 ms |

At W1, the conservative cache-fill pass makes caching slower. As the
window grows, the released path scales with all past patch rows while
the cached path stays nearly flat. That is the causal-frame-state
opportunity; ROM does not create it.

## Global NoC critical-cut sensitivity

This sweep keeps temporal KV local and varies the fraction of modeled
attention injection serialized across the global bisection. Zero is an
ideal placement floor; one is the deliberately pessimistic endpoint.

| W32 path | Critical-cut fraction | Frame interval | ROM attribution | Largest main-phase term |
|---|---:|---:|---:|---|
| Reference recompute | 0% | 4.524 ms | 1.000× | compute |
| Reference recompute | 25% | 8.372 ms | 1.000× | compute |
| Reference recompute | 50% | 12.220 ms | 1.000× | noc_serialization_floor |
| Reference recompute | 100% | 19.916 ms | 1.000× | noc_serialization_floor |
| Causal cache | 0% | 0.178 ms | 4.286× | compute |
| Causal cache | 25% | 0.327 ms | 2.785× | compute |
| Causal cache | 50% | 0.477 ms | 2.225× | noc_serialization_floor |
| Causal cache | 100% | 0.776 ms | 1.753× | noc_serialization_floor |

The reference path remains at 1.000× ROM attribution throughout:
removing weight traffic cannot shorten its compute/NoC critical path.
The cached path exposes weight service, so its ROM attribution ranges
from 4.286× at the ideal cut to 1.753× at the full-cut endpoint. A ROM
claim without a placement and communication claim is therefore incomplete.

## Cache placement and ROM service semantics

This is the central W32 cached workload. `whole_call` is the optimistic
OpenTallas batched ROM-as-storage interpretation: each distinct matrix
is served once per call and all rows reuse it. Integer `R` means a
matrix must be re-served after `R` rows. `R=1` approximates a per-stream
fixed-weight traversal, but it is not a cycle model.

| Cache crossing global cut | ROM row reuse | Frame interval | ROM attribution | Main ROM array bytes |
|---:|---:|---:|---:|---:|
| 0% | whole_call | 0.477 ms | 2.225× | 13.375 GB |
| 0% | 64 | 0.477 ms | 2.225× | 31.106 GB |
| 0% | 8 | 0.477 ms | 2.225× | 164.090 GB |
| 0% | 1 | 0.977 ms | 1.086× | 1.281 TB |
| 25% | whole_call | 1.497 ms | 1.390× | 13.375 GB |
| 25% | 64 | 1.497 ms | 1.390× | 31.106 GB |
| 25% | 8 | 1.497 ms | 1.390× | 164.090 GB |
| 25% | 1 | 1.997 ms | 1.042× | 1.281 TB |
| 50% | whole_call | 2.518 ms | 1.232× | 13.375 GB |
| 50% | 64 | 2.518 ms | 1.232× | 31.106 GB |
| 50% | 8 | 2.518 ms | 1.232× | 164.090 GB |
| 50% | 1 | 3.018 ms | 1.028× | 1.281 TB |
| 100% | whole_call | 4.558 ms | 1.128× | 13.375 GB |
| 100% | 64 | 4.558 ms | 1.128× | 31.106 GB |
| 100% | 8 | 4.558 ms | 1.128× | 164.090 GB |
| 100% | 1 | 5.058 ms | 1.017× | 1.281 TB |

The cache should therefore be sharded by spatial patch and retained
beside each temporal-attention lane. Sending temporal K/V over the
global bisection on every denoise call erases most of the storage gain.
Likewise, the claim requires a physical activation-broadcast/reuse path;
a ROM bitcell's bandwidth number alone does not prove whole-call reuse.

## MiniMax-H3 control: why current clip DiTs are less favorable

H3 is an intentionally strong control. The official transformer has
66.280 GB of weights, but approximately 26.021 GB of AdaLN branches can
be precomputed for a fixed inference schedule. The model therefore
charges only 40.260 GB per transformer call—already giving H3 its
vendor-described inference optimization. The 50 main blocks contain
19.268B modeled matrix parameters.
The complete payload fits one conservative stage (101.111 GB
available, 1.525× margin), so this result neither hides
a multi-stage capacity penalty nor invents a multi-stage ROM benefit.

The accelerated control is deliberately more favorable than a literal
FastH3 graph: its 10% residual density scales both attention arithmetic
and modeled attention NoC, including text/audio paths that are not all
sparse in the published method.

| Clip / variant | Packed N | Calls | Tensor operations | Attention share | Weight reads | QKV floor (not charged) | Central ROM time | Output fps | ROM attribution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5.17s / base_dense | 38,222 | 49 | 174.796 POP | 58.7% | 1.973 TB | 8.055 TB | 23.830 s | 5.20 | 1.000× |
| 5.17s / accelerated_best_case | 38,222 | 4 | 6.729 POP | 12.4% | 161.038 GB | 657.541 GB | 0.827 s | 149.94 | 1.000× |
| 10.12s / base_dense | 73,898 | 49 | 523.145 POP | 73.3% | 1.973 TB | 15.573 TB | 68.162 s | 3.57 | 1.000× |
| 10.12s / accelerated_best_case | 73,898 | 4 | 14.522 POP | 21.6% | 161.038 GB | 1.271 TB | 1.779 s | 136.57 | 1.000× |
| 14.38s / base_dense | 104,478 | 49 | 964.063 POP | 79.5% | 1.973 TB | 22.018 TB | 123.140 s | 2.80 | 1.000× |
| 14.38s / accelerated_best_case | 104,478 | 4 | 22.364 POP | 28.0% | 161.038 GB | 1.797 TB | 2.734 s | 126.19 | 1.000× |

The 1.000× entries above assume every matrix is served once for the
whole call. The following accelerated-case sensitivity asks what happens
if a fixed-weight datapath must instead re-serve it for every activation
row (`R=1`):

| Accelerated clip | Whole-call time | Whole-call ROM attribution | R=1 time | R=1 ROM attribution | R=1 ROM array service |
|---|---:|---:|---:|---:|---:|
| 5.17s | 0.827 s | 1.000× | 2.888 s | 0.286× | 6,155.197 TB |
| 10.12s | 1.779 s | 1.000× | 5.583 s | 0.319× | 11,900.391 TB |
| 14.38s | 2.734 s | 1.000× | 7.894 s | 0.346× | 16,824.934 TB |

For dense 5.17-second H3, the central phase is
20.850 s compute plus
2.980 s of modeled
NoC floor, versus only
0.918 ms of ROM service.
For the deliberately favorable long-clip accelerated case, compute is
still 2.668 s and the
ROM service is 0.075 ms.
Moving those weights into HBM cannot change the maximum.
Under R=1, however, ROM becomes slower than the same-compute HBM
counterfactual (0.286×–0.346× attribution in the accelerated
cases). Thus H3 is not merely unable to exploit ROM-as-storage; a
per-stream fixed-weight implementation can make service the bottleneck.

H3's released full attention is bidirectional over the packed text,
video, and audio sequence. Past positions change as the noisy clip
changes, so Q/K/V from one denoising call cannot be installed as an
autoregressive persistent cache. Approximate cross-step feature caches,
step distillation, and sparse attention can accelerate H3, but those are
algorithm/model changes—not benefits from immutable ROM storage.

## Calibration and the meaning of real time

The official SGLang benchmark reports 19.04 s for one warm BF16
1344×768, 124-frame H3 request on 8×B300. This study's transformer-only
roof model gives 23.66 s,
or 1.24× the
published latency. That is a useful order-of-magnitude check, not a fit:
the discrepancy is left visible and no ROM parameter is rescaled.

FastH3 demonstrates the difference between playback throughput and an
interactive world model. Its published 8×B200 median generates 345
frames (14.38 s of playback) in 12.88 s, but the user still waits for a
full clip and cannot inject a new action before each generated frame.
Oasis must close a 50 ms action-to-next-frame loop continuously.

The Oasis site reports 20 fps for its proprietary demo. The public-code
W32/B300 tensor-path model here gives 24.35 fps,
but the demo checkpoint, exact hardware, runtime, and auxiliary work are
not sufficiently identified to call that a validation. The cached
central value of 2,096.4 fps
is a service-envelope diagnostic, **not** a prediction that an
OpenTallas video system would run at that rate.

## Cache correctness conditions

The candidate cache is exact only if all of the following hold:

1. Temporal attention remains strictly causal, so a past frame never
   depends on the current frame.
2. Past latent values, actions, and their context timestep stay fixed
   across the denoising calls whose K/V are reused.
3. Sliding-window rollover uses position-stable global indices or
   correctly re-rotates cached keys; naively shifting RoPE indices is
   not cache-safe.
4. The completed frame receives the modeled extra pass at the fixed
   context timestep before its layerwise temporal K/V are committed.
5. Dynamic noising never mutates a cached past state without explicit
   invalidation and refill.

The public code satisfies the causal-attention premise but does not
implement or validate this transformation. A byte/flop derivation is
not an exactness proof.

## What OpenTallas supports today

OpenTallas currently supports neither model. There is no video/world-
model ABI, 5-D latent layout, axial-attention lowering, diffusion
scheduler, temporal-cache lifetime rule, action-conditioning operator,
VAE backend, video compiler image, RTL execution, or cycle evidence.
This study adds only a deterministic analytical workload model and
checked artifacts. It does not turn the README's Oasis horizon into an
implementation claim.

## Highest-value gates

1. Implement the layerwise temporal cache against the pinned Oasis code
   and compare every latent bit/code through denoising and W32 rollover.
2. Trace actual matrix calls, activation rows, transient bytes, and
   kernel time for both released paths; replace the unpriced auxiliaries.
3. Map the cache and axial attention onto a concrete floorplan and
   measure which bytes cross each physical cut.
4. Resolve the batched-ROM versus per-stream compute-in-ROM activation
   service with RTL and placed/routed port/timing evidence.
5. Profile the authenticated Oasis checkpoint and execute H3 to replace
   code/header inventory with checkpoint- and runtime-derived evidence.

## Reproduce

```bash
make world-model
PYTHONPATH=src pytest -q tests/test_world_model_study.py
```

Inputs: [study config](../../configs/studies/world_model_rom.json),
[Oasis inventory](../../data/inventory/oasis-500m-code.json),
[H3 inventory](../../data/inventory/minimax-h3-transformer.json), and
[analytical implementation](../../src/opentallas/world_model.py).

## Evidence boundary

- Analytical and deterministic only: no Oasis/H3 checkpoint execution, compiler lowering, cycle simulation, RTL, physical design, or fabricated ROM measurement.
- The causal Oasis cache is a derived transformation. Exactness still requires implementation and latent-output comparison through timestep changes and sliding-window rollover.
- The tensor-operation model omits norms, softmax, nonlinearities, RoPE, scheduler work, kernel launches, host/control paths, codecs, and I/O.
- Transient H3 Q/K/V traffic is retained as a byte floor in workload metadata but deliberately excluded from HBM service, making H3 favorable.
- Service for the precomputed H3 AdaLN output table is also unpriced, making the H3 control favorable.
- The accelerated H3 control applies its 10% residual attention density to both attention arithmetic and modeled attention NoC, an intentionally favorable lower bound rather than a reproduction of the FastH3 graph.
- The NoC term is a critical-cut serialization floor from assumed placement fractions; it omits propagation, routing contention, multicast realization, and endpoint overhead.
- The integer ROM row-reuse sweep is a service-byte proxy. It does not establish the timing, port count, or activation concurrency of digital compute-in-ROM.
- OpenTallas currently has no video/world-model ABI, compiler path, scheduler, causal frame-state operator, or video RTL backend.
