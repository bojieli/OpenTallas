# HBM accelerator: SM → SU result contract (2026-10-07)

`tools/hbm_sm_su_result_contract.py` produces [`contract.json`](contract.json). It is an executable inventory with 25 fail-closed checks. Every input is pinned by repo path and sha256. It uses only the standard library, and `--check` reproduces the contract byte-identically from a clean `git archive` with `HOME` unset.

Scope: DS-V4.1 at 1M context on the HBM accelerator, using the r23 die generator and the matched AR walk (343 SM handoffs per token). The Qwen 8K HBM rows price no result gather, because the W12 vehicle carries its own tree, so they are unaffected.

## Finding

The composition prices the SM → SU result handoff at **343 cycles/token**. That is 0 exposed wire, because the wire is hidden under the barrier round trip, plus the +1 gather-station register (`stations gather a2 +1`) per barrier. This is the cost of a native level-2 edge, and that edge does not exist:

- **Die view (E4).** The path is 32 SM `r` faces (270 b) → 36 gather/waypoint stations → 4 `hfd_su.r` inputs (2,165 b). The wires and stations exist. `hfd_su` is the generator's PHYSICAL ENVELOPE: it registers `r` twice and XOR-folds it into its result chains (2,165 XOR terms). There is no valid/ready, no merge and no SU controller. The status is *exists-only-in-die-view*.
- **RTL.** `ot_hbm_accel_su_parent_exec` has one data interface, a memory request/response (337 b / 273 b). It has no SM-result, collective-delivery or attention ingress. In the integrated DS cluster:
  - W2 results enter from top-level pins into one `w2_result_sink` per die.
  - That sink writes the results through shared-provider port `p_req[2]`.
  - The SU reads 256-b sectors through `p_req[1]`.
  - Both ports cross `ot_gpu_mreq_cdc` (AW3) into `ot_gpu_memsys_adapter`, the xbar → L2 → HBM model of the GPU-organised comparator, with one request outstanding.
  - The cluster's SM is the SIMT `ot_ds_hbm_simt_sm20`, not `ot_hbm_accel_sm_v`.

  The native result store `ot_hbm_sm_result_provider` passes as a component, but only against test memory, and has no floorplan fit. The status of this store-and-forward path is *implemented-in-RTL*, on the comparator's backend.
- **`gather_bridge`** is a 512-b score/ID memory. It is not on this path.

## Edges

| id | producer → consumer | bits / protocol | latency | die route | credit | area | status |
|---|---|---|---|---|---|---|---|
| E1 | `sm_v` rv/rrow/rdata/fault → result store | 270 / 269 b; one-way, **no ready**, ≤1 row/cycle, reservation before start | PIO 2, inside the measured start→done; capture +1 | none (no store block on the die) | reservation (op_rows) | 40 × 512x64 macros = 0.182 mm² per 4096×256 store (5.84 mm² if one per SM; count owned by SM control) | store RTL component; join to `sm_v` missing; die missing |
| E2 | store → shared service, write + readback | 312 / 344 b request, 276 b response; valid/ready, one outstanding | 6.68 cycles/row at test memory (measured, full4096 = 31,475 cycles); die floor ≥ 4 + 2×12 per row (estimate) | none | single outstanding; CDC 8 entries each way | comparator memsys | RTL (comparator backend); die missing |
| E3 | shared service → SU operand read | 337 / 273 b; valid/ready, one outstanding | ≥12 cycles per sector (estimate: CDC SYNC 3 + xbar/L2; HBM write-through ack excluded) | `f_vm` / `t_vm` faces (XOR envelope) | single outstanding | — | RTL (comparator); die-view only |
| E4 | SM r → gather → `hfd_su.r` | 270 leaf / 2,165 trunk; wires only | 51 cycles one-way (r23 floor; worst `result_sm8`, 17.4 mm, 49 stages) vs control 55 | rg gather stations → rh arms → rt trunk waypoints → hub edge; 36 r22 relay ends (17,300 relay bits) | none | 36 stations, 0.436 mm²; relay DFF ≈ 6,558 µm² (TT) | die-view only; consumer missing |
| E5 | SU ↔ TU endpoint | inj 2×512 b, pull (idx/rd, HUBW 35); delivery 4×545 b push, no ready; die faces 1,024 / 580 b | HUBW 35 each way inside the measured endpoint; die 7 + 7, plus 6 face stages in the ledger | `t_coll` / `f_coll` (envelope) | none on delivery | missing SU-side buffer | endpoint RTL; SU side missing; 580 b < 2,180 b delivery |

## Publication impact (cycles per AR token; percentages of the unified candidate 561.067 µs AR / 1,102.39 µs MTP step)

| line | cycles | µs | AR % | MTP % |
|---|---|---|---|---|
| published today (hidden wire + gather a2 +1) | 343 | 0.286 | 0.051 | 0.026 |
| **proposed native edge** (station +1, SU ingress +2 per barrier, conservative) | 1,029 | 0.858 | 0.153 | 0.078 |
| implemented RTL store-and-forward, **floor estimate** (3,313 rows × (4 + 3×12)) | 132,520 | 110.4 | 19.7 | 10.0 |
| same path at the component's own 1-cycle test memory | 25,457 | 21.2 | 3.8 | 1.9 |
| correction if the native edge is adopted | +686 | +0.572 | +0.102 | +0.052 |
| collective HUBW reconciliation, **not credited** | −13,250 | −11.0 | −2.0 | −1.0 |

These lines currently count the synthetic tree as native execution:

- `closure_cost_ledger.md` "stations gather a2 +1" (343).
- `hbm_accel_die_price.py` `result_gather`, which is 0 because the result is assumed to travel with the arrive.
- Both lines inherit into `headline_with_closure_r23.json` (1,750.9 / 3,626.1) and into the unified ledger HBM DS rows (1,782.3 / 3,772.7 and 1,656.7 / 3,526.2).

The correction that keeps the native-edge figure is small: about +0.1% AR. Using the implemented RTL path instead would be about +20% AR. That gap is why the native edge has to be built rather than relabelled.

## Proposed line items

1. Replace "stations gather a2 +1 (343)" with "SM → SU native result edge: station +1 and SU ingress +2 per barrier = 1,029 cycles/token". The status is *gated*.
2. Add `sm_su_result_edge_native` to the `gated_by` list of the HBM DS rows in the unified ledger.
3. Until that gate closes, label the result handoff as "priced as a native edge that exists only in the die view (envelope)".
4. Leave the collective HUBW give-back (13,250 cycles) uncredited until the endpoint is re-measured with HUBW set to the die path.

## Proposed contract (owners: SU = Codex /hbm SU; result store and shared service = Codex /hbm SM)

- **SM face.** The SM `r` face (270 b) stays one-way. The SU grants op_rows rows per SM at issue through cmdproc, so no ready or credit return crosses the die. On the DS walk the maximum is 43 rows per SM per op.
- **Transport.** Place `ot_hbm_result_relay_slice` ×5 (64-b slices) at each of the 36 stations and relay ends. The 8-SM trunk stays a parallel bundle, so no arbitration is needed.
- **SU result ingress (new, SU owner).** Give each SM lane a FIFO of at least 43 × 268 b, plus a row counter. Gate the consumer's release/start on count == op_rows, so ordering comes from the protocol rather than the 57-cycle timing slack (72 vs 144 on the r23c routed bound, from a scratch GRT that is not pinned). Area estimate: 0.14 mm² of raw DFF for 32 lanes, or 2 × 512x64 SRAM per lane.
- **Collective.** The SU ingress also feeds the endpoint injection buffer, which the endpoint pulls by index. Endpoint delivery needs either a sink that takes 4 flits per cycle or a measured DEL=1 pacing.
- **Result store (SM control).** The store remains the retention, readback and publication path. It is not on the per-token SM → SU critical path.

## Estimates

The 12-cycle round-trip floor counts only the AW3 CDC synchronisers (SYNC 3 each way) and xbar/L2 acceptance. It excludes the HBM write-through acknowledgement. The store-and-forward floor assumes every SM's store and memory port run in parallel, whereas the integrated cluster has one sink per die. Two node row counts are proxies with 1 row each: `engram.wkv` and `compressor.wkv|wgate`. The die stages are the r23 Manhattan floor from committed sources.
