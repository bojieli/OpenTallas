# ROM-MULTIUSER 2026-10-18: many concurrent requests on the ROM designs by pipeline interleaving

Owner goal (10-18): keep a good single-user tok/s AND scale to many concurrent requests by pipeline parallelism across
the ROM die chain, unlike GPU batching.

This is a design study. Producer: `compute.py`, which writes `summary.json` and reads only `inputs_s81_stages_1009.json`
beside it. There is no RTL change and no fleet job.

**Grades.**
- **composed:** `token_path_1018` single-user rates.
- **measured:** a committed RTL bench or view.
- **modelled:** this file's arithmetic; the formula is in `compute.py`.
- **stale:** power, kept only because no die has a current power figure.

**Comparator:** the A100 80GB (owner 10-18): 8x HGX for DeepSeek, 1x for Qwen. It is a modelled roofline with the repo's
assumed efficiencies (weight 0.75, KV 0.70, compute 0.45), so it is an **upper bound for the A100**.

## Short answer

1. **The single-user rate is unchanged, by construction.** Each user's static schedule is a time shift of the
   reference user's schedule, so other users only ever take stage time the reference user leaves idle (proof below).
2. **S81 (DeepSeek, 1M) is 1 user today. Once the calendar exists it reaches about 33.6k tok/s (modelled).** That is
   27 AR users at 1,243 tok/s each; the S81 cap comes from the busiest stage, about 35.1k cycles a position.
   - The stage idle fraction behind this: in AR, the worst stage is 3.6% busy and the mean stage 1.4%.
   - Against the 8x A100 at its best: **11.4x per system and 0.21x per mm²** (AR against AR). Against the A100 with MTP
     (modelled upper bound), our best is 3.8x per system and 0.07x per mm².
   - Per W the result is 0.95x (AR vs AR) and 0.30x (MTP vs MTP), but our power is **stale**.
3. **Qwen ROM (8K) is 1 user today. Once 4 slots exist it reaches about 18.4k tok/s (modelled).** The KV-die attention
   service sets the cap.
   - Against 1x A100: **8.8x per system and 0.81x per mm²** AR against AR. Against the A100 with speculative decoding
     (an upper bound), 2.1x per system and 0.20x per mm².
4. **The A100 delivers no throughput at ≥1,000 tok/s per user, in either model, with or without speculation.** Its best
   batch-1 rates are DS 778 tok/s with MTP and Qwen 643 tok/s with spec, on the roofline. At that per-user rate we give
   33.6k (S81) and 18.4k (Qwen). This is the regime the ROM designs own.
5. **Balancing the "L20 stage" alone buys little:** +11% for +10 dies, and copies 3 and 4 add nothing more.
   - The worst stage (L19.ffn + L20.attn, 35.1k cycles) is only 10% above the other three full-scan stages (L14 32.0k,
     L8 31.1k, L2 28.0k).
   - Replicating **all four full-scan stages x2** gives 55.9k tok/s (+67%) for +40 dies (+9.1% area). That is
     0.146 tok/s/mm² against 0.095 today.
   - Its index scan is 18% of the stage. The ROM field matvec (about 42%), the select/top-k step and the collectives
     make up the rest.
6. **HBM stacks matter only if p4l really has 1 stack a scan die.** The 10-18 composition charges the 10-09 scan rate,
   which implies about 4 stacks a die (5,937 cycles for 71 MB over 4 dies).
   - At 1 stack the L20 stage grows to 53.9k cycles. Single-user AR drops to 1,173 tok/s (−5.7%) and MTP to 3,412 (−10%).
     The aggregate drops to 21.1k.
   - **Check owed (S81-DIE / PRICE):** make sure the p4l composition charges the stacks p4l actually has.

## (1) What multi-request needs (exact list)

| # | item | S81 | Qwen ROM | today |
|---|---|---|---|---|
| 1 | **Compiler calendar.** User k = the reference schedule shifted by k slots. A slot is the worst stage's per-position occupancy. Slot 0 is reserved for the latency user. | `dv_layer_compile.py` → N-slot calendar: 27 slots AR, or 6 MTP + 31 AR-filler positions per MTP step. Each slot reuses the same per-stage program with a per-slot {user, pos, base} table. | 4 slots per 6,886-cycle layer period (1,721.5 cycles a slot). Fillers carry static bubbles around every user's LM-head window (3,048 cycles). | one token (S81); one slot (Qwen) |
| 2 | **Non-collision proof in the compiler** (the shift lemma below, plus an assertion that every resource window ≤ the slot). Collision = fault, never a stall (static rule). | `ot_dsdv_fixed_issue` already faults on a same-cycle engine collision between its 2 job contexts. | `kv_calendar` needs a user dimension. | partial |
| 3 | **Per-stage activation buffer.** One extra landing message a stage ingress, so user k+1 lands while user k computes. No queueing beyond 2 under the shift calendar. | +40,976 B a rank die (the h message). The MTP wavefront already needs the same per-position landing. | Compute die keeps each resident user's FP32 residual + BF16 staging (24 KB a user). | MTP wavefront landing (S81, partial); none (Qwen) |
| 4 | **User-tagged hand-off.** The 10-bit user id rides the message header; the receiving stage selects that user's bases. | `{user 10, tok 21, pos 21}` already on start frames (`dsdv_seq_host.sv`). Extend it to the stage h message. | `ot_qwen_activation_handoff` has user tags, but in its TB only. Wire it. | partial |
| 5 | **Per-user KV / index / window addressing** (state in HBM, never on-die SRAM). | Window ring `WB + 68·u` exists (`dsdv_svc_att`). **Missing:** a per-user index-key base in `svc_sx`, a per-user KV-row base for the owner layers 2/8/14/20, and the reuse layers reading the owner's rows by user. | KV-die per-user KV base (`kv_calendar` user dim). | partial / none |
| 6 | **Host interface slots.** | Host plane takes one token in and out a step. It needs N outstanding {user, pos} and a per-user next-token return (133.5 cycles each, off the critical path). | `qkd_host_if_pins.sv:104` `$fatal` unless NSLOT==1 && ENG_CTX==1. Lift it to 4. | 1 |
| 7 | **KV-die attention multi-request.** | n/a (attention is on the layer dies; the svc is per-position) | Service buffer capacity stays 1. Slot 1,721 ≥ service 1,555, so only the next request's q (1 KB) must land while one is in service. The all-reduce engine must accept a new collective every slot. **If it is one-in-flight (2,184 cycles), Qwen caps at 3 slots = 14.0k tok/s.** | 1 |
| 8 | **HBM capacity per user** | 22.5 GB a stack / ((288+68) B x 1M / 4 dies) ≈ **241 users** on the busiest owner die. Not binding (27-48 users). | 32 stacks x 22.5 GB / 604 MB ≈ 1,192 users. Not binding (4). | ok |
| 9 | **HBM bandwidth per user** | L20 index scan = 71.3 MB a user a position. In the composed basis it is 6.3k cycles of the 35.1k stage. At 1 stack a die it is 22.5k cycles and becomes most of the stage (item 6 of the short answer). | 75.5 MB a KV die a token a user; inside the 1,555-cycle service. Not binding. | ok (composed) |
| 10 | **MTP draft state per user** | The draft dies keep a seed hidden state per MTP user, 40 KB each. AR fillers need none. | AR only | none |

## (2) Area per die: buffers vs control

The SRAM figure is 0.52 mm²/MB: 3.869 MB/mm² array (`configs/architecture/chip_design_v2.json`) x2 for ASAP7 macro
periphery. Grade: modelled.

| die | added SRAM | mm² | share of die |
|---|---|---|---|
| S81 rank die | +40 KB landing message + 0.5 KB user table | **0.021** | 0.003% of 799.2 |
| S81 draft die | 6 x 40 KB seed state | 0.13 | 0.02% |
| Qwen compute die | 4 users x 24 KB | 0.05 | 0.006% of 841 |
| Qwen KV die | 1-KB q landing for the next request (the service never holds 2 requests: slot 1,721 ≥ service 1,555) | 0.001 | <0.001% of 272.6 (0.20 mm² only if a full second 128-KB score slot were built; not needed) |

**Conclusion: multi-user is almost entirely a compiler and control job.** The hardware is:
- user-tag fields;
- per-slot base registers;
- a 2nd landing buffer;
- the lifted NSLOT asserts.

Most of it lands in unbuilt or unclosed leaves or in new small leaves, so no closed tile has to re-close (section 6) and no die grows.

**Exception: balancing does cost silicon.** It takes +10 dies a replicated stage, or about +10 mm² of PHY a stack.

## (3) Proof that the single-user rate is unchanged

**Construction.** Let R be the reference (latency) user's compiled single-user schedule, with period P:
- AR: P = 965,379 cycles (S81), 251,615 (Qwen).
- MTP: P = one step, 1,311,216 cycles.

For every shared resource r (stage engine set, link, HBM port, collective engine, KV service), R occupies a set of
windows W_r. User k runs R shifted by δ_k = k·S, where S ≥ max over resources of the longest window (the slot).

**Lemma.** Two users collide on r iff some window of R overlaps a window of R shifted by δ_i − δ_j (mod P). With every
window ≤ S and the shift a nonzero multiple of S, that can only happen if R itself occupies r twice within S. That
holds for no resource:
- S81: a stage sees each position once per pass.
- MTP: the 6 positions occupy 6 consecutive slots at each stage. These are reserved as slots 0-5 of the step, and the
  fillers take slots 6-36.
- Qwen: a resource is used once per layer period, except the LM head.

R's windows are therefore never touched, and the reference user's timeline is bit-for-bit the compiled single-user
timeline. Fillers inherit the single-user period, so they run at the same per-token latency (AR) or at the MTP step
period (fillers inside an MTP calendar: 915 tok/s each).

**Exceptions the compiler must handle.** Each is charged to the fillers, never to R:
- **Qwen LM head.** It takes 3,048 cycles once a token on the tile field, more than one slot. Fillers carry a static
  bubble around every user's head, so a filler runs at 4,549 instead of 4,769 tok/s.
- **HBM refresh.** It is already in the single-user calendar. Filler scan reads are confined to the filler's own windows.
- **Link serialisation.** The 652-cycle h message is shorter than the slot.
- **Host plane.** 133.5 cycles a token per user.

**Idle fraction available to fillers.** Measured/composed busy per stage, scaled to the 10-18 composition by K = 1.0575.

| design | worst stage busy | mean stage busy | worst idle |
|---|---|---|---|
| S81 AR | 35,092 / 965,379 = **3.6%** | 1.4% (59 stages) | 96.4% |
| S81 MTP step | 6 x 35,092 / 1,310,492 = **16.1%** | 6.3% | 83.9% |
| Qwen AR | KV service 36 x 1,555 / 251,615 = **22.2%**; tile field 21.1%; all-reduce (one in flight) 31.2% | – | 77.8% |

## (4) Aggregate tok/s vs N (the binding bound is the busiest-stage occupancy)

| system | N | per-user | aggregate | binding |
|---|---|---|---|---|
| S81 AR, all users | 1 … 27 | 1,243 | 1,243 … **33,562** | worst stage (L19.ffn+L20.attn) 35.1k cycles a position |
| S81 MTP, all users | 1 … 6 | 3,808 | 3,808 … **22,850** | 6 verify positions = 6 slots a step |
| S81 1 MTP reserved + AR fillers | 1 + 0 … 31 | 3,808 reserved, fillers 915 | 3,808 … **32,195** | same stage |
| S81 MTP, verify shares the index read across its 6 positions (modelled sensitivity) | 1 … 7 | 3,808 | 26.7k | same stage |
| S81 + 4 full-scan stages x2 (+40 dies) | 1 … 45 | 1,243 | **55,937** | next stage 21.3k (L33-L36 reindex stages) |
| S81 + all 10 stages > 20k x2 (+80 dies) | 1 … 48 | 1,243 | 59,666 | 20.0k |
| Qwen AR, 1 reserved + 3 fillers | 1 … 4 | 4,769 reserved, fillers 4,549 | 4,769 … **18,416** | KV-die service 1,555 / slot 1,721 |
| Qwen, all-reduce one-in-flight | 1 … 3 | same | 13,973 | all-reduce 2,184 |

**Other bounds are not binding at these N:**
- S81 index-scan HBM: 53k (1 stack) to 213k (4 stacks).
- S81 KV capacity: 241 users.
- Qwen KV HBM: 53k.
- Qwen KV capacity: 1,192 users.

**Why the S81 cap is "only" 27-45 users:** a stage is a whole layer's attention + next layer's FFN on the same dies.
The 2 job contexts a die (`ot_dsdv_fixed_issue`) would let two positions overlap inside a stage. That is the next
lever (about 2x), but it is unmeasured.

### Balancing (coordinator item 2)

| option | added | II (cycles) | single-user AR / MTP | aggregate AR | tok/s/mm² |
|---|---|---|---|---|---|
| as composed | – | 35,092 | 1,243 / 3,808 | 33,562 | 0.0954 |
| 1 stack a scan die (p4l as specified?) | – | 53,927 | **1,173 / 3,412** | 21,107 | 0.060 |
| 2 stacks a scan die | +32 stacks, about +320 mm² PHY | 41,370 | 1,219 / 3,666 | 28,028 | 0.080 |
| 4 stacks a scan die | +96 stacks, about +960 mm² PHY (shoreline unchecked on a 799 mm² die) | 35,092 | 1,243 / 3,808 | 33,562 | 0.095 |
| L20 stage x2 | +10 dies, 7,992 mm² | 31,979 | unchanged | 37,291 | 0.1037 |
| L20 stage x3 / x4 | +20 / +30 dies | 31,979 | unchanged | 37,291 | 0.101 / 0.099 |
| 4 full-scan stages x2 | +40 dies, 31,968 mm² | 21,274 | unchanged | **55,937** | **0.1458** |
| all 10 stages > 20k x2 | +80 dies | 19,970 | unchanged | 59,666 | 0.1436 |

**How users alternate copies.** Users alternate copy A and copy B of a replicated stage. The reference user always uses
copy A, so its path is unchanged. Each copy's HBM holds the KV and index of its own users. The reuse layers (21-23 read
L20's rows) must address the owner copy by user, which is part of item 5.

**Effect of HBM stacks on latency.** More stacks only shorten the scan. That helps single-user latency in the 1-stack
case and does nothing in the composed basis.

### The index-scan traffic (coordinator item 3)

**Where the 68 B a key comes from.** The V4.1 indexer (`configs/models/candidates/deepseek-v4.1-flash.json`: 32 index
heads x 128 dims, top-512) stores, for every compressed context entry, one FP4 index key of 128 dims (64 B) plus one E8M0
scale per 32 dims (4 B), which is 68 B.

**Size per user and position:**
- Layer 20 (compress ratio 1) scans every one of 1M entries: 71.3 MB a user a position.
- Layers 2/8/14 (ratio 2) scan 512K entries each.
- The reindex layers 24/28/32/36 scan at most 16,384.
- Total: 182.7 MB a user a position.

**What can be shared or cached:**
- **Across users: only a common prefix.** The keys are a function of each user's own tokens. If several users share a
  prompt prefix (system prompt, agent scaffold), the keys of those entries are identical. One read could score several
  users' queries if the compiler co-schedules those users into one "group slot" at the scan stage.
  - Gain: HBM bytes only. The score MACs (32 x 128 x 1M a position) stay per user.
  - It matters only in the 1-stack case, because in the composed basis HBM is 18% of the stage.
- **Across the 6 MTP verify positions of one user: yes.** It is the same key set, so one read can score 6 queries.
  The composition re-reads them for each position; sharing is worth about +17% on the all-MTP calendar (modelled).
- **Caching on-die: no.** 71 MB a user at one layer is more than a die's SRAM, and every position needs all of it.
  The keys grow by one entry per token, so there is no reuse across tokens that would beat streaming.

## (5) Fair A100 baseline (modelled roofline, A100 upper bound)

| system | batch 1 per-user | max batch | aggregate at max | per-user at max |
|---|---|---|---|---|
| 8x A100, DS 1M, AR | 406 | 62 users (KV capacity) | 2,945 | 47 |
| 8x A100, DS 1M, MTP γ5 τ 4.159 | 778 | 62 | **8,858** | 143 |
| 1x A100, Qwen 8K, AR | 173 | 103 | 2,105 | 20 |
| 1x A100, Qwen 8K, spec 6 positions τ 4.159 (DFlash-class drafter 1.05 GB) | 643 | 103 | **8,632** (τ 3.1445: 6,526) | 84 |

**Model assumptions.**
- On the GPU, speculation multiplies tokens per KV read and per weight read. At max batch it is KV-bound, so the roofline
  credits it about 3-4x.
- This is an upper bound. Measured GPU spec decoding at large batch gains far less.
- The A100's 8-GPU NCCL latency (2 all-reduces x 40 layers x 15 µs, assumed) caps DS at batch 1.

**Comparison** (ratios = ours / A100 best point; power for ours is STALE (±50%)):

| pair | per system | per mm² | per W (stale) |
|---|---|---|---|
| S81 b1 AR vs A100 b1 AR | 3.06x | 0.058 | 0.26 |
| S81 b1 MTP vs A100 b1 MTP | 4.89x | 0.092 | 0.41 |
| S81 max (AR, 27 users) vs A100 max AR | **11.4x** | **0.21** | 0.95 |
| S81 max (1 MTP + AR fillers) vs A100 max MTP | 3.63x | 0.068 | 0.30 |
| S81 + 4 scan stages x2 vs A100 max MTP | 6.3x | 0.109 | 0.48 |
| Qwen b1 vs A100 b1 AR / b1 spec | 27.6x / 7.4x | 2.56 / 0.69 | 1.57 / 0.42 |
| Qwen max (4 slots) vs A100 max AR | **8.75x** | **0.81** | 0.50 |
| Qwen max vs A100 max spec | 2.13x | 0.20 | 0.12 |

**Pareto curve** (`summary.json` `pareto`: per-user rate, aggregate, aggregate/mm², aggregate/kW for every point).
- The A100 curves fall steeply from their batch-1 points: DS 778 → 143 per user, Qwen 643 → 84.
- Ours are flat lines: every user keeps the single-user rate up to N_max.
- Above ~800 tok/s per user, the A100 has no points at all; ours sit at 1,243-4,769 per user.
- Below ~150 tok/s per user, the A100 wins on area by 5-14x for DS and 1.2-5x for Qwen. That is the GPU regime.

## (6) Touched tiles, closure risk, and die floorplan / GRT impact

Full rows are in `summary.json` `touched_tiles` / `die_impact` / `reclosure_plan`.

**Sources.**
- Status comes from `gaps/die_element_table.json`, generated 10-18 03:29. Re-check it before acting.
- Floorplan facts come from `s81_dv_1016/p4l/price_land.json`.
- Grade: modelled. No gate was run.

**Touched tiles:**

| design | change | tile / element (status, fails) | can it avoid touching a closed tile? | mm² | risk |
|---|---|---|---|---|---|
| S81 | N-slot calendar | compiler + `ot_dsdv_fixed_issue` program (inside `dsdv_seq_host`, RTL-only; `sh_vc` CLOSED, 2 fails) | yes: the slots are program content, and 2 job contexts already exist | 0 | low |
| S81 | user tag on h message | end-slice `dsdv_slice_lep` (RTL owed) | yes: put it in the lep before its first hardening | 0 | low |
| S81 | 2nd landing buffer | NEW leaf `dsdv_mu_land` beside each end-slice lep | yes: new leaf (0 mm² if the MTP wavefront landing is reusable) | 0.021 | low |
| S81 | per-user index / KV-row base | `dsdv_svc_sx_hrow` CLOSED (native owed, 0 fails) | **yes, preferred:** the compiler writes absolute per-user bases into each job word (as `svc_att` WIN_LOAD already carries SB). Fallback: a NEW user-context leaf `dsdv_mu_ctx` at the svc entries rsv_05/rsv_11 | 0-0.004 | low (medium if svc_sx itself must change) |
| S81 | per-user window ring | `dsdv_svc_att` | already built | 0 | none |
| S81 | host plane N outstanding | `dsfd_host_sd` CLOSED; `dsfd_host_native` RTL-only, NEEDS_HUMAN, 7 + 3 fails | partly: put the return-path user field in the open `dsfd_host_native` | 0.001 | **medium** (fail history) |
| S81 | 4 full-scan stages x2 | die count and chain | die unchanged; rack/chain re-plan; the lep must expose a 2nd tx port | +31,968 system | medium (system) |
| S81 | 2-4 HBM stacks a scan die | p4l PHY shoreline | no | +10-30 a die | **high: forces a die re-plan** |
| Qwen | host NSLOT 4 | `qkd_host_if_pins` (core `ot_host_if_pb2` already parameterised to 16; KV-HROOT live) | no, but the cluster is unclosed: do it now in KV-HROOT | 0.01 | low-medium |
| Qwen | KV calendar user dim + base | compiler + `qkd_kvs_ctl` / `qkd_kvs_hroot` (RTL-only) | yes (base in the job word) | 0.002 | low |
| Qwen | next request lands during service | NEW 1-KB q leaf beside `qkd_land`; `qkd_kvs_attn` (gating) unchanged | yes | 0.001 | low |
| Qwen | per-user residual 4 x 24 KB | VM regions (compiler) | yes, if VM has 96 KB free (check owed) | 0-0.05 | low |
| Qwen | all-reduce one per 1,721-cycle slot | collective sequencer | likely (links are pipelined; payload 1.9% busy); check that it accepts overlapping epochs | 0 | **medium** (else 3 slots = 14.0k) |

**Die level (calendar + buffers; balancing is separate):**

| die | where it sits | added die wires / crossings | bits-per-cut | long links / relays | area | GRT risk |
|---|---|---|---|---|---|---|
| S81 p4l | Leaves abut their consumers: `dsdv_mu_land` at each end-slice lep, `dsdv_mu_ctx` at rsv_05/rsv_11. They fit in the 171 mm² (21.4%) of whitespace without moving neighbours. | 0 if the user id uses spare header bits; else +10 b on the abutted 4 x 276-b stage lanes, with no new crossing | worst cut 0.5357, +<0.001 | none | +0.03 mm² (0.004%), fits in the outline | **low.** No new long wires. Die GRT headroom is unknown: no S81 die run yet; bind FAIL 10-18 00:38. |
| Qwen dv2f14 | VM regions; fallback leaf beside the SU spine | 0 | unchanged | none | +0-0.05 mm² (0.006%) | low |
| Qwen kvs14 | 1-KB leaf at the d2d entry; slot bits inside the host cluster | +2 slot bits, local to the leaf | unchanged | none | +0.01 mm² (0.004%) | low |
| HBM d4g GEN2 | not touched by this study (HBM multi-user = P position lanes, lane HBM-MTP, next die) | – | – | – | – | – |

**What forces a re-plan:** nothing in the calendar or buffer work forces a die re-plan. HBM stacks 2-4 on the scan dies
would force one.

**Ordered plan to minimise re-closure:**
1. **Compiler only.** S81 N-slot calendar plus a shift-lemma checker; Qwen `kv_calendar` user dimension; absolute
   per-user bases in the job words.
2. **Fold into first hardenings.** S81 end-slice lep user tag; Qwen host NSLOT 4 (KV-HROOT); the `dsfd_host_native`
   return user field on its next attempt.
3. **New small leaves beside the consumers.** `dsdv_mu_land`; the Qwen 1-KB q landing. `dsdv_mu_ctx` only if svc_sx
   cannot take an absolute base.
4. **MU.TOK bench.** A two-user calendar on the stage/layer benches: bit-exact per user, and the reference user's cycle
   trace identical to its single-user trace.
5. **Optional.** Replicate the 4 full-scan stages (a chain re-plan, no die change). Add HBM stacks only if the 1-stack
   scan-rate check shows p4l is scan-bound.

## Files

- `compute.py`: the model; every constant has its source inline.
- `summary.json`: every number with its grade.
- `inputs_s81_stages_1009.json`: per-stage critical-path busy cycles and index-score cycles, extracted from
  `results/arch/token_path_20261009/ds_rom.json` (the record and commit are inside the file).
