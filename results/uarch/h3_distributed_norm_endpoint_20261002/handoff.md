# Selected native H3 implementation proposal and executable distributed command IR

Active worktree: `/tmp/h3-distributed-endpoint/worktree`, base `de7e9e2bdf57c72cd5df91fd5b2595453e959a7b`. The original66c452 worktree and outputs are untouched. This added compiler implements the next dependency: RF word movement and INT/BF16 operations for Qwen RSTD4096 and DeepSeek HC-pre/RMS5120, with source-owned distributed homes and finite retirement. There is no new RTL/build or live-job change.

## Concrete output

Both compressed target files replace the SM0 diagnostic placement with whole32SM assignments for every transient version. Each256-word block owns32 complete chunk8 leaves; HC residual planes share the same dimension block/SM. Rank pattern groups preserve individual rank demands and partial-output source ranges. Native RF slots0..31 remain kernel workspace; macro operands use32..511. Every proposed home has a lifetime and source version; the verifier rejects simultaneous RF/spill ownership. This is a candidate compiler ABI, not an adopted deployment mapping.

`selected_command_bindings.bindings` covers all72 Qwen RSTD PCs and80 DeepSeek HC-pre PCs. Participant bindings reference immutable command templates containing concrete integer RF addresses, opcode/phase/active-lane fields, expected operand versions, output versions and prior-retirement dependencies. Every rank/SM instance scopes those local versions independently. Inputs come from actual macro version homes, not hard-coded32/33 across layers. Output homes are also emitted; x and attn_x/ffn_x outputs require their own mirrored commits rather than a free alias.

The HC sequence uses four products followed by three ordered adds starting atp0, then source bit-exact BF16 round instructions. Norm gathers lane8*c+j from two RF vectors, squares, and accumulates sequentially from+0. Five local pair levels reduce32 chunks; the collector tree reduces16 Qwen roots or32 padded DeepSeek roots. Qwen gets exactly four global tree levels, not an extra padded level. DeepSeek's twelve constant-zero root slots are explicit. Root insertion is a full-vector RMW under the same RF lease and commits before producer ACK; it preserves every other root's ownership.

The executable U32 endpoint semantics cover GATHER8, PAIR_EVEN/ODD, SPLAT, ROOT_INSERT, FILL_ZERO, SHR, AND, XOR, wrap-IADD/ISUB, RF_COPY and PACK_BF16. PACK_BF16 only moves upper16 bits from already-rounded source values. It introduces no extra rounding. These software bit tests are an implementation specification, not a timing oracle or RTL qualification.

## Model-bound selected endpoint

Planned new default-off endpoint: `ot_gpu_rf_word_int_candidate`, integrated into the actual `ot_gpu_full_sm_service` RF arbitration. Command ports: valid/ready, opcode4, phase3, RF a/b/dst9, active-lanes8; held done/ready/fault. One accepted command leases the whole RF through read consumption, full mirrored write ACK and done. It uses the existing two4096-bit read operands and4096-bit write, not a new multiport RF. Source parent and RF hashes are pinned in model.json.

The root route carries F32data32+SM5+closed-exchange token1+valid/ready/commitACK3 =41tracks.64-byte shared staging remains a local packet allocation; it does not imply a512-bit external root wire. One lease per source and one collector insertion are outstanding; all accepted roots retain ownership until collector mirroredACK. Two-entry forward/reverse CDC FIFOs are priced at128DFF bits perSM including pointer/synchronizer state. Source clock-phase latency remains an explicit term.

No wider version serial is placed on wire. Observer identities contain program/version/SM scope. Token reuse requires exact root count, both queues empty and a provider fence certifying no old deliveries. A wire-identical ghost after reuse cannot be detected by the one-bit token; restart is refused without that closed-provider certificate. Root logical completion is not causal PHY write visibility.

The unified-model entry states all RF/boundary bits,32replicas/rank, FIFO/DFF/mux cost, fanout and route reservation. It uses the existing analytical DFF0.2916um2, mux-bit0.2um2 and50%utilisation proxies. Integer logic and mode muxes are explicitly proposed proxy costs, not mapped SS/FF area. The wide8192/4096 RF interface stays inside the SM macro cluster; it cannot be sent down the old3200-track payload corridor. Extra41-track root corridors are priced against the existing floorplan geometry and tracks/um, with no free existing tracks or new signal layers claimed. Macro abstracts remain unhardened; physical slot fit is not asserted.

`selected_flow` separates the conditional19-cycle native FP transaction budget from MOVE/INT, DIV, root/CDC, source staging and scalar delivery terms. Native FP-only critical-path candidates are760functional edges for Qwen and1102 for DeepSeek. Neither is full kernel latency or native GPU nanoseconds. H1 alias-driver source evidence remains the calibration authority; no tens-of-nanoseconds launch or ideal32SM overlap is assumed. Concurrent local work is allowed only after all participating input/constant/gamma versions are staged and every SM has a separately priced RF endpoint.

The consumer boundary also counts actual x-store fanout: DeepSeek5120 outputs require2,621,440 broadcast bytes/10,240 native256-byte beats across32NC8 targets; Qwen4096 requires4,194,304 bytes/16,384beats across32NC16 targets. Packing uses a two-entry512B queue. Output source groups remain ordered; first matrix issue requires complete xw staging, x_rdy, barrier release and native weight readiness. These costs cannot disappear behind a root reduction estimate.

## Finite homes and spill/refill

The distributed layout gives DeepSeek zero transient spill and a peak67 RF vectors perSM including workspace. Persistent KV/index/selected histories remain separate provider obligations. Qwen's decoded-cache transient demand remains32MiB/rank; its existing activation_scratch extent is704,512bytes at source base4714740864. The resident address mapper refuses this spill allocation. It does not invent a new base or silently borrow state/weight storage.

Spill/refill ABI is bound to the retained backend candidate's AW34/LENW6/BEATW5/TAG16, four-stack128B stripes,32B sectors, one outstanding read and one write in this selected adapter. A512B RF vector uses16sector obligations. Accepted write intent persists until actual causal visibility; read leases and reverseACK must retire before overwrite. An executable lease model rejects ACK-as-visible, wrong-version completion and early reuse. The provider candidate remains unqualified hardware; no fixed visibility timer is added.

## Exact next ownership split

Peirce owns this distributed address/command compiler and proposed gather/INT/RF-lease integration. Before writing its off-by-default HDL copy, Maxwell must admit the priced within-SM branch, extra root corridor, replica/fanout budget and composed service terms. This is the concrete review dependency, not a request to broaden scope. Future added paths are named in endpoint_ABI.

An independent owner can implement/model the exact DeepSeek DIV endpoint and Qwen reciprocal/Newton semantics without touching this compiler. DIV must preserve the pinned scalar rounding contract; an approximate reciprocal is not interchangeable. H2 owns causal spill visibility and delivery-fence qualification. Goodall retains sole H1 runtime ownership; no binary is rerun here. The whole32SM lowering remains a proposed layout, not final GPU software feasibility or full-token execution.

## Tests and replay

```
python3 -m pytest -q tests/test_h3_distributed_norm_endpoint.py
python3 tools/h3_distributed_norm_endpoint.py --verify --out results/uarch/h3_distributed_norm_endpoint_20261002
```

Eleven tests cover full32SM partition conservation/HC plane co-location, all gather phases and pair levels, wrap integer/BF16 bits, neighboring-root preservation, duplicate/stale/premature root ACKs, spill causal visibility/retirement, exact global tree size, live-RF alias rejection, default-off/physical admission guards and BF16 packing/x-store demand. Exact replay regenerates the whole distributed layout and command/model objects. No numeric tensor, compiler build, P&R, hardware/provider or clock qualification is claimed.
