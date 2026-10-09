# HBM generic die interface (HGI-1), v0.9 frozen draft

Stream hbm-iface, 2026-10-09. This is the interface that every hardware fork, the simulator, the compilers and the goldens of the generic HBM die build against. The die runs both Qwen3-8B and DeepSeek-V4.1-Flash.

- **Machine-readable form:** `results/arch/hbm_generic_iface_20261009/spec.json`.
- **Reference encoder and validator:** `tools/hbm_generic_iface.py`. It writes the spec and the two model descriptors (`md_*.hex`, `md_*.json`). `--check` fails on any drift.
- **Inputs:**
  - the approved block inventory and parameter list of the hbm-generic plan (`results/arch/hbm_generic_20261009/PLAN.md`, branch claude/hbm-generic-20261009, 01f643326; REVIEW_20261009 addendum);
  - the Qwen-on-r25 study (`results/arch/qwen_on_r25_20261008/PLAN.md`);
  - the coverage ledgers T3 and T4;
  - Codex's family inventory (871 graph operations, 28 families, 22 without a producer);
  - the existing r25 block ports (`hfd_cmdproc` LAUNCH/END list, `smh` op port with `op_fmt`, the SU op set of `tools/hdc_isa_v41.py`, `ot_dshbm_argmax`, `ot_dsrom_su_softmax`, `ot_hbm_rope_table`).

Status: **v0.9 is frozen for parallel start.** Changes go through the change rule in §8. v1.0 freezes once the cmdproc fork and the simulator have both consumed the encodings without amendment.

## 0. The design on one page

A model differs from another in three kinds of thing. Each kind has exactly one home:

| What differs | Where it lives | Hardware cost |
|---|---|---|
| Shape and numeric constants: widths, heads, layers, eps, θ, softmax scale, clamp limit, RoPE tables, norm gains, sinks, scales | **Data and program.** Tables sit in HBM. Constants are template immediates. Counts and strides go in memory descriptors. | none |
| Rigid control in a fused fast path: token width, norm width, output formats, RoPE pairing, softmax sink, collective group, KV layout | **17 static mode fields in 9 words** (MD section C), loaded once at model load | small mode logic in the blocks the plan already parameterises |
| Per-operator choices that already vary inside one DS token: weight format, rows, positions, segment length | **Per-op fields** in the program record (§3) | none beyond the ports that exist |

Five rules keep the design simple:

1. **Reset = DS.**
   - The reset value of every mode register is today's DS behaviour.
   - The DS descriptor's section C equals the reset values, so loading it is a no-op. The encoder asserts this.
   - A DS bench that never loads a descriptor still runs, and every existing DS closure and vector stays valid.
2. **Hardware never derives.**
   - The encoder computes section C from sections A/B (`derive()`).
   - Hardware only latches words and checks magic, version, CRC, reserved bits and legal values.
3. **One path per operator family per model.**
   - Each family is bound either to a fused fast path or to an exact SU fallback.
   - The golden uses the arithmetic order of the bound path, so changing a binding is a golden change (§5).
4. **Static during decode.** Mode registers change only at a model load, while the die is idle. There is no per-token reconfiguration.
5. **One program format for both models.**
   - The command processor runs a stream of unit-op records. Every engine is reached the same way.
   - DS's existing SIMT kernels are one unit op (`SIMT.RUN`), so DS evidence carries over.

## 1. Model configuration: the descriptor

### 1.1 Layout

The model descriptor (MD) is 64 little-endian 32-bit words (256 B). An FP32 constant is stored as its IEEE bits. Every reserved bit is 0. `spec.json` → `md_fields` is the authority for every bit position.

| Words | Section | Read by | Content |
|---|---|---|---|
| 0–3 | A header | cmdproc (0–1), software | magic `0x31494748` ("HGI1"), version 0.9, length 64, model class (1 DS-V4.1-Flash, 2 Qwen3 dense), feature flags (MOE, INDEXER, HC, ENGRAM, MTP, QK_NORM, ATTN_SINK, KV_COMPRESS, SHARED_LATENT_KV, Q_LORA, O_GROUPS, SWIGLU_CLAMP) |
| 4–31 | B geometry | software only | hidden, layers, MTP layers, q/KV heads, head dim, vocab, FFN/MoE widths, norm type/eps, activation, RoPE {pairing, dims, offset, scaling, θ, factor, YaRN β, compress θ}, window, context, softmax scale literal, SwiGLU limit, weight/KV/activation/scale/expert formats, MoE {experts, shared, top-k, scoring, norm, scaling}, indexer, candidate, HC {mult, Sinkhorn iters, eps}, Engram, MTP {kind, block, Markov rank, draft experts, noise token}, q/o LoRA, o groups, TP size |
| 32–39 | B identity | software | sha256 of the model's `config.json`, which binds the MD to one model |
| 40–48 | **C block modes** | **hardware** | the 17 mode fields of §2 |
| 49–55 | C reserved | — | 0 |
| 56–61 | D program | cmdproc | entry offsets (AR, verify, draft) and the program image's HBM base and size |
| 62 | — | — | 0 |
| 63 | CRC | cmdproc | IEEE CRC-32 of words 0–62 |

Section B is deliberately complete. It lets the compiler, golden, simulator and table generator read one table instead of each parsing HF configs. Per-layer lists (compress ratios, Engram, KV-source and index-source layer ids) stay in the program and the bound config (sha256), not in the MD.

### 1.2 The one config path

The path reuses the existing host write port of `hfd_cmdproc` (`cmd_we / cmd_addr / cmd_wdata`, 64 bits). No new pin is needed.

1. **CFG window.** Addresses with the window bit set write MD word pairs (word 2a in bits 31:0, word 2a+1 in bits 63:32) into the cmdproc's 64-word staging buffer. One more address is `CFG_COMMIT`.
2. **Commit.** At `CFG_COMMIT` the cmdproc runs the hardware check (§1.4). On success it broadcasts the section-C words on the **config bus**.
   - The bus is `cfg_v, cfg_addr[5:0], cfg_data[31:0], cfg_commit`. It is registered at every station it crosses and runs through the clock-crossing synchronisers into the 0.9 GHz serial domain.
3. **Latch.** Each block decodes only its own word addresses into shadow registers. On `cfg_commit` it copies shadow → active.
4. **Settle.** The cmdproc waits `CFG_SETTLE` cycles (≥ the deepest bus latency + 16; 64 by default), then sets `CFG_STATUS.loaded`. Doorbells are refused (`db_rdy` = 0) while a commit settles.

Because the active registers change only while every unit is idle, they are **quasi-static**:
- Synthesis treats them as constants for timing (`set_false_path -from` the `*cfg_act*` registers, with the settle interval as the hold-off).
- No mode register sits on a 1.2 GHz path as a timed launch point.
- A fork whose active registers are held at reset must be equivalent to the legacy block (§5.3).

### 1.3 Load sequence (once per model load)

1. The host writes the model image into HBM through `hfd_loader`: weights, tables, scales, embedding and the program records (§3.6).
2. The host writes the 32 MD word pairs into the CFG window, then `CFG_COMMIT`.
3. The cmdproc checks the MD, broadcasts, settles, and sets `loaded`. On error it sets `CFG_STATUS.err`, broadcasts nothing, and keeps the previous active values.
4. The host reads `CFG_STATUS`. On `loaded` it rings the first doorbell.

Reloading the same model is idempotent. Switching models means steps 1–4 with the die idle, which takes seconds and is off the token path (hbm-generic PLAN §4).

### 1.4 Validation and errors

These checks are implemented once, in `tools/hbm_generic_iface.py hw_check()`. The cmdproc RTL must match them case for case; that is conformance test CF-0.

| Code | Name | Condition | Effect |
|---|---|---|---|
| 0 | OK | — | modes active after the settle interval |
| 1 | E_MAGIC | word 0 ≠ `0x31494748` | refused; previous modes kept |
| 2 | E_VERSION | major/minor ≠ 0.9, or length ≠ 64 | refused |
| 3 | E_CRC | CRC-32 of words 0–62 ≠ word 63 | refused |
| 4 | E_BUSY | commit while a job runs or any unit queue is non-empty | refused |
| 5 | E_RANGE | a section-C field outside its legal set (§2) | refused |
| 6 | E_RESERVED | a reserved bit set in a hardware-read word | refused |

- **Before any load:** the reset values (DS) apply and doorbells are accepted. This keeps every existing DS bench valid.
- **After an error:** the last good values stay active.
- **Software-only check:** section C must equal `derive(A, B)`. The encoder and the conformance harness run it. Hardware does not.

### 1.5 The two descriptors

These are generated by the encoder from the checked-in `compiler/models/*/config.json`.

| Field | DS-V4.1-Flash (= reset) | Qwen3-8B (TP4) |
|---|---:|---:|
| `cp_vocab` | 129,280 | 151,936 |
| `cp_ctx_max` | 1,048,576 | 40,960 |
| `rope_half`, `rope_rot_log2` | 0, 6 | 1, 7 |
| `norm_d_units`, `norm_hc_off`, `norm_out_bf16` | 40, 0, 0 | 32, 1, 1 |
| `sfx_sink_off`, `sfx_multipass` | 0, 0 | 1, 1 |
| `glu_out_bf16`, `glu_clamp_off`, `glu_routew_off` | 0, 0, 0 | 1, 1, 1 |
| `coll_group_size`, `coll_head_rows` | 96, 0 | 4, 37,984 |
| `kv_dense` | 0 | 1 |
| `emb_int8`, `emb_row_bytes` | 0, 10,240 | 1, 4,128 |
| CRC-32 | see `md_ds_v41_flash.json` | see `md_qwen3_8b.json` |

## 2. Per-block mode fields

These are exactly the parameters of the approved hbm-generic list, and nothing else. A field is listed only when a fused fast path cannot express the model through data or per-op fields. "Fork" says what the hardware change must implement.

| Block (owner master) | Field | Bits | Legal | DS (reset) | Qwen | The fork implements |
|---|---|---:|---|---|---|---|
| `hfd_cmdproc_n/s` | `cp_vocab` | 18 | 1 … 2¹⁸ | 129,280 | 151,936 | Doorbell and completion range check against a register instead of the `VOCAB_SIZE` parameter. Token width **18 everywhere**, with no field (DS ids < 2¹⁷ leave bit 17 at 0). |
| | `cp_ctx_max` | 21 | 1 … 2²⁰ | 2²⁰ | 40,960 | Position range check against a register. Position width stays 20. |
| RoPE chains (q/kv chains in `hfd_su`) | `rope_half` | 1 | 0, 1 | 0 | 1 | Pair partner i XOR 1 (adjacent) or i XOR dims/2 (split-half). The sign of the partner term comes from the same bit of i. One operand-offset mux; on the c12 lanes, an XOR on a lane-index bit of `ld_c`. |
| | `rope_rot_log2` | 3 | 6, 7 | 6 | 7 | Rotated span: the last 64 dims (DS tail) or all 128. The start offset = head_dim − 2^k, from the op's descriptor. Tables are **HBM data** fetched per position (no θ or YaRN in hardware). |
| Norm engine (`norm_engine_view`, grp16, fused norm chains) | `norm_d_units` | 6 | 32, 40 | 40 | 32 | Vector width 4,096 or 5,120. The D4096 tree is the D5120 tree with a +0-padded tail, which is exact (x + 0 = x on the pairwise levels). The 1/D divide set already holds 2¹². |
| | `norm_hc_off` | 1 | 0, 1 | 0 | 1 | Bypass the hc_pre mix. The input is the residual itself. |
| | `norm_out_bf16` | 1 | 0, 1 | 0 | 1 | Publish BF16 (RNE) instead of the FP8 quantised output. |
| | *(per-op)* `seg` | — | 0, 128 | 0 | 0 (RMSNorm), 128 (QK-norm) | **Per-op, not static**: Qwen issues both segment lengths every layer. It is carried in `FUSED.ROW_NORM` `param`. A segmented reduction is one result per 128 slot. |
| Softmax (`ot_dsrom_su_softmax`) | `sfx_sink_off` | 1 | 0, 1 | 0 | 1 | Remove the sink from the max and from the denominator. (Feeding sink = −2¹⁰⁰ as data would also be exact, but the bit avoids a fake table; the plan approved the bit.) |
| | `sfx_multipass` | 1 | 0, 1 | 0 | 1 | Rows > NVMAX·LPH (640): pass 1 global max; pass 2 fixed 640-row chunks of exp + sum with carry-in, in chunk order; pass 3 scale (the PV normalise). NVMAX stays 40. 8,192 rows = 13 chunks. |
| SwiGLU fused chain (`hfd_sfu`) | `glu_out_bf16` | 1 | 0, 1 | 0 | 1 | Skip `PUBLISH_QUANT` FP8 and publish BF16. |
| | `glu_clamp_off` | 1 | 0, 1 | 0 | 1 | Skip the swiglu_limit clamp. |
| | `glu_routew_off` | 1 | 0, 1 | 0 | 1 | Skip the route-weight multiply (equal to × 1.0, exact). |
| Collective (`hfd_coll`, truecredit, owner half) | `coll_group_size` | 8 | 4, 8, 96 | 96 | 4 | Groups are **aligned** blocks of die ids: rank = die_id mod size, group = die_id div size, and the owner (reduction) order is rank order. No member map or owner table is needed while boot partitioning keeps groups aligned (PLAN §4). The fixed-order reduction is unchanged. |
| | `coll_head_rows` | 18 | 0 … 2¹⁸−1 | 0 | 37,984 | Argmax select carries 18-bit ids: global id = rank · rows + local id. Ties go to the lowest global id (numpy). 0 = ids already global (DS today). |
| KV write-back / ingest / causal mask (`hfd_kvwb_native`, `hfd_host_ingest`, `ot_qwen_r25_causal_mask`) | `kv_dense` | 1 | 0, 1 | 0 | 1 | 0 = DS: window ring (WR ≥ W + PMAX), selected rows, ROWS/IKEY ingest. 1 = dense per-head linear `[layer][kvh][K\|V][pos][head_dim]` FP8, cache-length mask (rows ≤ pos), QKV NHD → FP8 per-head-row ingest. The layout base and per-layer strides come from the op's descriptor. One bit drives all three blocks because they always change together. |
| Embedding fetch (svc row + SU dequant) | `emb_int8` | 1 | 0, 1 | 0 | 1 | Row = INT8 codes + BF16 row scale, dequantised on the SU (DS: BF16 rows). |
| | `emb_row_bytes` | 16 | 1 … 65,535 | 10,240 | 4,128 | Row stride (32 B aligned). Row address = base + token · stride, with an 18-bit token. |

**Changes with no field:**

| Block | Change | Why there is no mode field |
|---|---|---|
| SM (`smh_front_c/n/s`, tiles) | `op_fmt` 3 = INT8→BF16 unpack plus half-line issue | Format is **per-op** (DS mixes BF16, FP8 and FP4 inside one token). Fmt 0–2 latency is bypass-matched (PLAN), so DS cycles are unchanged. The per-row BF16 scale is applied by the consuming SU op (§3.7). |
| `ot_dshbm_argmax_m` | IW 17 → 18 | Universal. DS ids keep bit 17 at 0. |
| svc segments (`hfd_svc_*`) | Kind-1 KV and kind-2 index-key reads striped over all 32 PCs; posted-write merge | Both models need it (Qwen bandwidth; the DS native indexer). It is the same function in both modes. |
| Attention tiles (`hfd_attn_half_*`) | none | The GQA head mapping is a program choice: one KV head a tile, with 4 of 16 lanes at AR and 16 at verify p = 4. A per-lane KV select is rejected (it would reopen closed quads while attention is KV-bound). |
| `hfd_su` lanes, `hfd_sfu`, `su_red`, `su_full` | none | Generic. They run the exact fallbacks (row scale, residual, embedding dequant, argmax-merge fallback). |
| `hfd_mtp`, `dspark_ctl`, `hdc_accept` | TW 18 when reopened | Qwen MTP comes after the owner's τ measurement. Its parameters (B, STAGES, MARKOV_EN, UNION_EN) are **not** in v0.9; they get descriptor words 49–55 at that decision. |
| `hfd_hc`, HCP, indexer, Engram | none | DS-only. Qwen programs never issue them. |

## 3. Program interface

### 3.1 Execution model

- **SPMD.** Every die of a group runs the same program. Rank-dependent addresses use the DYN value `RANK` (§3.5).
- **The cmdproc is an in-order sequencer.**
  - It fetches **records** from the program image in HBM through a prefetch ring.
  - It evaluates each record's predicate and holds the record until its `wait` mask is satisfied.
  - It then dispatches the record to the target unit's queue. Each unit retires its queue in order and keeps an outstanding count.
- **`wait`** (12 bits, one per unit): issue only when those units have nothing outstanding. Cross-unit dependences on memory use `wait`. The compiler computes it from region hazards, as `tools/hdc_program_v41.py` `schedule()` does today.
- **STREAM operands.** A producer and a consumer joined by a hardware FIFO (`space = STREAM`; for example SM results → SU lane registers, head matvec → argmax) need no `wait`; credits order them. This is dataflow level 2 of AGENTS.md. The stream ids a die supports are fixed by its wiring (§3.3).
- **Collectives synchronise themselves** by data arrival. Each die issues them in the same program order, and the endpoint's sequence counter matches them.
- **The doorbell** `{token 18, pos 20, job 32, gen 4, entry 2, ncol 4}` starts the program at `entry` (AR, verify, draft).
  - `ncol` is the number of positions for a verify pass (1 at AR).
  - The completion carries `{token 18, pos 20, job, gen, status 4, cycles}`. Status codes are those of today's cmdproc (0 OK, 1 unit fault, 2 no result, 3 bad command/range).

### 3.2 Record format

A record is a 128-bit header, then an optional 256-bit SU template, then one 256-bit memory descriptor for each set bit of `opnd`, in A, B, C, O order. It is 16–176 bytes long.

**Header (UOP, 128 bits):**

| Bits | Field | Meaning |
|---|---|---|
| 127:124 | `unit` | 0 CTL, 1 SM, 2 SU, 3 SFU, 4 FUSED (norm engine and fused SU chains), 5 ATT, 6 COLL, 7 ARGMAX, 8 DMA (svc, loader, kvwb), 9 IDX (DS indexer/select), 10 HC (DS), 11 SIMT (DS legacy kernels) |
| 123:118 | `op` | unit op (§3.3) |
| 117:106 | `wait` | unit drain mask |
| 105:104 | `pred` | 0 always, 1 pos == 0, 2 pos ≠ 0, 3 last loop iteration |
| 103:100 | `opnd` | which of A, B, C, O descriptors follow |
| 99 | `tmpl` | an SU template follows |
| 98:96 | `slot` | position slot (verify column) whose DYN bank this op uses |
| 95:64 | `param` | unit-specific integer (§3.3) |
| 63:32 | `imm_a` | FP32 or integer immediate |
| 31:0 | `imm_b` | FP32 or integer immediate |

**Memory descriptor (MDESC, 256 bits):**
- `space` (2 bits): HBM, VM, STREAM or NONE.
- `fmt` (3 bits): FP32, BF16, FP8E4M3, FP4E2M1, INT8, U32, UE8M0.
- `base` (40 bits): HBM byte address (32 B aligned), or VM FP32-word address.
- `n` (20 bits), the inner count, and `m` (20 bits), the outer count.
- `stride` (32 bits), the outer stride; `istride` (16 bits), the inner element stride (0 = 1).
- `lstride` (32 bits), the per-loop-iteration stride.
- `dyn_sel` (5 bits) and `dyn_mul` (27 bits).
- `n_sel` (5 bits): 0 means static n; otherwise n = DYN[n_sel].

The effective base is **base + L·lstride + DYN[dyn_sel]·dyn_mul**. The dispatcher computes it. It is the only address arithmetic hardware does on the program's behalf.

**SU template (SUT, 256 bits):** the pipeline fields of the existing SU op set (`tools/hdc_isa_v41.py`):
- operand sources `a_src a_ind b_src b_half c_src c_pair d_src`;
- pre-ops `a_rnd a_relu a_min c_clip`;
- stages `m1 m2 qm ad sfu e1 e2 rnd`;
- destination and reduction `dst red red_sq red_whole red_rnd su_vec red_tree`;
- `imm1..3`.

That is 142 bits used. Semantics are `hdc_program_v41.Machine.su1` (R-ARITH chunk8). The only change is that `c_pair`'s partner and sign follow `rope_half` / `rope_rot_log2`. The bases and strides that the 1,536-bit ISA word carried move into the descriptors, so one template serves every layer.

### 3.3 Unit ops

| Unit.op | Operands | `param` | Semantics (bit-exact reference) |
|---|---|---|---|
| CTL.NOP / FENCE | — | — | FENCE = wait for all units and for every posted HBM write to be visible |
| CTL.LOOP / ENDLOOP | — | count (LOOP) | One level. L = 0 … count−1, and the body replays from the prefetch ring, so it must fit the ring. Unrolled programs are equally legal. |
| CTL.END | A = U32 token | — | completion token = A[0] (range-checked against `cp_vocab`) |
| CTL.TOKX / AMAX / ACCEPT | A | slot | the existing MTP control steps of `hdc_isa_v41` (reserved until the Qwen MTP decision; DS keeps its `dspark_ctl`) |
| SM.MATVEC | A = x (VM/STREAM), B = weights (HBM, fmt), O = y (VM/STREAM) | [1:0] fmt (0 BF16, 1 FP8 block-dot, 2 FP4 block-dot, 3 INT8), [4:2] positions − 1 (weight read shared by up to 8 slots) | smh arithmetic (tc16 ring, column tree, stack pairing). Rows are split over the die's 32 SMs by the SM layout rule (§7, item 2). |
| SU.VOP | template, A–D, O | — | `Machine.su1` |
| SFU.GLU | A = gate, B = up, C = route weight, O | — | the fused SwiGLU chain under `glu_*` |
| FUSED.HC_PRE_NORM / ROW_NORM / HC_POST | A, B = gain, O | [7:0] seg (0 or 128) for ROW_NORM | the norm engine under `norm_*`. imm_a = eps. |
| ATT.QK / ATT.PV | A = q or p (VM), B = K or V rows (HBM, `n_sel` = POS1), O | [3:0] head lanes used, [7:4] 64-element slices per head − 1 | tile chunk8 + pairwise per 64-slice, then the slices in slice order |
| ARGMAX.LOCAL | A = logits (STREAM/VM), O = {value, id} | — | numpy argmax, lowest index on ties, NaN flag reported |
| COLL.ALL_REDUCE_SUM / ALL_GATHER / TOPK_MERGE / ARGMAX_MERGE | A = local, O = result | — | the owner fixed-order reduction in rank order. ARGMAX_MERGE uses `coll_head_rows`. |
| DMA.LOAD / STORE / FENCE | A = source, O = destination | — | HBM ↔ VM row moves (embedding row, RoPE row at POS, sinks, scales). A STORE with `kv_dense` is the KV append; FENCE makes it visible to the next ATT read. |
| IDX.*, HC.HC_MIX | DS-only | — | today's DS engines |
| SIMT.RUN | — | entry PC (14 bits) | launches an existing OTG-1 kernel on the SM mask in imm_a and waits for done. **This is how every committed DS kernel runs unchanged.** |

### 3.4 Synchronisation summary

There are exactly four mechanisms:
- the `wait` mask, for unit drain;
- STREAM credits, for producer → consumer;
- collective arrival, for cross-die;
- CTL.FENCE, for HBM write visibility.

There are no semaphores, events or kernel-level barriers. Transaction-level exactness holds: latency may grow, but the order of results and faults is fixed by program order within a unit and by these four mechanisms.

### 3.5 DYN values

The cmdproc computes these at the doorbell, one bank per slot:

| Code | Value |
|---|---|
| 0 | ZERO |
| 1 | POS |
| 2 | POS1 = pos + 1, the valid KV rows |
| 3 | TOKEN |
| 4 | L, the loop counter |
| 5 | RANK |
| 6 | SLOT |
| 7 | POS_SLOT = pos + slot |

The DS-only selectors (window and compressed-row counts from `hdc_isa_v41.FULL_DYN`) occupy codes 8–31 unchanged.

### 3.6 Memory map (per die)

- **HBM** is one die-local byte address space, 40-bit, with 32 B sectors.
  - The svc address map (sector → stack / PC) is fixed and the same in both modes.
  - **Required:** a contiguous KV or index-key sweep spreads over all 32 PCs (the svc striping fork). The old fixed `KV_PC` path is not a legal target for `kv_dense` reads.
- **Regions** are placed by the compiler and recorded in the image manifest, not in hardware:

| Region | Content |
|---|---|
| IMAGE | program records; `image_base` / `image_pages` in MD section D |
| TABLES | RoPE cos/sin rows per position (Qwen: 1 set, θ 1e6, 128 dims; DS: plain + YaRN + compressed sets), norm gains, sinks, softmax-scale-free constants |
| SCALES | INT8 per-row BF16 scales (Qwen) / UE8M0 block scales (DS) |
| WEIGHTS | per-SM layout by the SM layout rule |
| EMBED | row stride `emb_row_bytes`, replicated per die |
| HEAD | this die's vocabulary shard, `coll_head_rows` rows |
| KV | Qwen: `[layer][kvh][K\|V][pos][128]` FP8, 2 KV heads a die at TP4. DS: today's ring layout. |
| SCRATCH | spills and collective staging |

- **VM** is FP32-word addressed (the 262,144-word VM of a die), allocated by the compiler.
- **Alignment:** HBM bases are 32 B aligned; KV rows are whole sectors.

### 3.7 Qwen: the 28 families as unit ops

| Family (operations a token) | Unit op | Path |
|---|---|---|
| qkv, o, gu, down (144), head (1) | SM.MATVEC fmt 3 | fast path (fmt 0 BF16-widened image for bring-up, bit-identical) |
| row_scale_qkv/o/gu/down (144), head_scale (1) | the consuming SU.VOP takes B = scale, M1 = A·B (one FP32 RNE multiply, the golden's rounding point) | SU; no separate op where the consumer's first stage is free |
| prenorm (73) | FUSED.ROW_NORM seg 0 | fast path (`norm_*`) |
| QKnorm (36) | FUSED.ROW_NORM seg 128 | fast path |
| RoPE (36) | SU.VOP with `c_pair`; tables by DMA.LOAD at POS | fast path (`rope_*`) |
| roundQ (36) | SU.VOP rnd (FP8 for KV) | SU |
| attention_qk / attention_pv (72) | ATT.QK / ATT.PV, 4 lanes a KV head | tiles |
| softmax (36) + pv_normalize (36) | FUSED softmax `sfx_multipass` (pass 3 normalises) | fast path |
| SwiGLU (36) | SFU.GLU | fast path (`glu_*`) |
| residual (72) | folded into the next ROW_NORM input, else SU.VOP add | fast path / SU |
| all_reduce_o / all_reduce_down (72) | COLL.ALL_REDUCE_SUM, group 4 | collective |
| kv_append / kv_fence (72) | DMA.STORE (`kv_dense`) / DMA.FENCE | kvwb |
| embedding (1) | DMA.LOAD (TOKEN · `emb_row_bytes`) + SU.VOP dequant | svc + SU |
| argmax_local / argmax_gather / argmax_merge (3) | ARGMAX.LOCAL + COLL.ARGMAX_MERGE | fast path |
| (end of token) | CTL.END | — |

That is 28 families on 12 unit ops plus SU templates.

**Migrating Codex's six joined descriptors.** Codex's six SU-ROM entries (prenorm 0/4, QK 4/6, RoPE 10/6, roundQ 16/1, SwiGLU 17/2, softmax 19/23) translate mechanically: each ROM slot becomes one SU.VOP record. Its fields go to the template and its bases go to the descriptors.

**What this supersedes.** The CP namespace `0x53550000..05`, the two-half launch coalescer and per-family owner frames have no place in HGI-1. The sequencer dispatches SU records directly. Those sources stay as history.

### 3.8 DS on HGI-1

DS keeps its kernels and engines. Its program is a record stream of:
- `SIMT.RUN(pc)` for every committed OTG-1 kernel;
- the native engine ops (`FUSED.HC_PRE_NORM`, `IDX.*`, `HC.HC_MIX`, `COLL.*`, `DMA.*`) where the DS composition already uses them.

With section C at reset, every block behaves as today. The DS lowering is a re-encoding, not a re-design. Its acceptance test is identical tokens and per-unit outputs against the existing DS evidence (§5).

## 4. Simulator contract

The simulator (`tools/hgi_sim/`, new) is the arbiter between compilers and hardware. It must model the following.

**Inputs and outputs**
- **Inputs** are the same artifacts the die consumes: the MD (64 words), the program image (records), the HBM image, and doorbells.
- **Outputs:**
  - completions;
  - a per-record trace: issue cycle, retire cycle, unit, a hash of each operand and result buffer;
  - an HBM/VM write log;
  - fault codes.

**Functional model (bit-exact).** Each unit op is computed by one shared **arithmetic library**, whose order functions are each pinned to an RTL bench:
- SM: per-format leaf, tc16 ring, column tree, stack pairing;
- ATT: chunk8 + pairwise per 64-slice;
- SU: `Machine.su1` / R-ARITH csum;
- norm, softmax (incl. multipass chunk order) and SwiGLU under every mode value;
- collective: rank-order reduction;
- argmax: lowest index.

The simulator and the golden both call this library. Nothing else is shared, so a compiler error (a wrong address, stride, wait or binding) shows up as a mismatch.

**Control model**
- the CP sequencer: prefetch, predicate, `wait`, LOOP, DYN banks;
- unit queues and STREAM credits;
- collective matching by group sequence;
- FENCE visibility;
- the config path, including every error code of §1.4 and the settle hold-off.

**Timing model (transaction-level)**
- Per unit: issue rate, pipeline depth and per-op setup cycles, taken from a calibration table (`hgi_sim/calibration.json`). Every entry carries a record pin and a grade (measured or estimate).
- HBM: per-PC bandwidth, 32 B sectors, request queue depth.
- Collective: the measured endpoint latency plus a per-crossing budget.

Cycle results are pathfinding until each entry is measured. The bar is timing within ±2 % of each stage bench; exactness is never a tolerance.

**Faults:** every fail-closed condition of the RTL (SU domain faults, non-finite FP, descriptor out of range, `END` token ≥ `cp_vocab`) must produce the same fault and the same completion status.

**Out of scope:** wires, clock crossings beyond fixed latencies, and physical faults.

**Proof obligations**
- (a) The simulator's functional mode equals the golden bit for bit on every token of the test set.
- (b) Every RTL stage bench equals the simulator's per-record buffers for the same records.
- (c) The simulator's cycles track the stage benches within tolerance, and the composition uses measured entries only for published numbers.

## 5. Goldens, verification and conformance

### 5.1 Goldens

- **DS: unchanged.** `hdc_golden_v41` (chunk8) and the existing campaigns remain the reference. HGI-1 adds only a re-encoded program, which must reproduce the same tokens and buffers.
- **Qwen: `qwen_r25`** (new). This is the Qwen3-8B graph in r25 order, built on the arithmetic library and parameterised by the MD.
  - Its path bindings are those of §3.7: fast paths for norm, QK-norm, RoPE, softmax and SwiGLU.
  - The SU fallbacks are the documented alternative, and binding one is a golden change.
  - Owner sign-off rests on one contract quality run in r25 order (~2.2 GPU-h; the INT8 per-row contract must stay within the pre-committed PPL/MMLU rule).
  - The bring-up image (fmt 0, BF16-widened INT8) uses the same golden bit for bit.

### 5.2 Verification ladder (per model)

| Level | Vehicle | Pass criterion |
|---|---|---|
| L0 | the arithmetic library vs each block's pinned bench vectors | bit-exact, with each mode value covered |
| L1 | simulator functional vs golden | every token of the test set, AR at P8191 (Qwen) / the DS reference positions |
| L2 | RTL stage benches (one stage per layer type plus the head; owner rule "minimum component") vs simulator per-record buffers | bit-exact, each with a negative mutant |
| L3 | composition: simulator timing with measured entries | published only as a measured composition |

### 5.3 Conformance tests every hardware fork must pass

| ID | Test | DS mode (reset) | Qwen mode |
|---|---|---|---|
| CF-0 | Config path | DS descriptor load = no change. Each error code, with active values kept. Doorbell before any load = DS. Commit while busy refused. Settle hold-off. | Qwen descriptor load; read-back of every section-C field |
| CF-1 | Mode-0 equivalence | Fork with active registers at reset ≡ legacy block: formal equivalence where the block is small (cmdproc, argmax, coll owner half, kvwb), else byte-identical replay of the block's committed DS vectors **and** identical cycle counts | — |
| CF-SM | `smh_front_c` fmt 3 | fmt 0–2 vectors identical, latency bypass-matched | fmt 3 output ≡ fmt 0 on the BF16-widened image, bit for bit; INT8 −128/127/0 rows |
| CF-CP | cmdproc | 17-bit DS token set | ids 131,071 / 131,072 / 151,935; pos 2²⁰−1; range refusal at `cp_vocab` and `cp_ctx_max` |
| CF-ROPE | RoPE chain | adjacent 64-tail vectors | split-half 128 against the golden; mutant: `rope_half` = 0 must fail |
| CF-NORM | norm engine | D5120 / HC / FP8 vectors | D4096 HC-off BF16; seg 128 QK-norm (32 + 8 heads); mutant: an unpadded tail |
| CF-SFX | softmax | sink vectors | 8 heads × 8,192 rows multipass vs the golden chunk order; T = 1, 640, 641, 8,192 |
| CF-GLU | SwiGLU | FP8 / clamp / route vectors | BF16, no clamp, no route weight, 3,072 a die |
| CF-COLL | collective | TP-96 vectors | TP4 and TP8 AR (256 words) in rank order; ARGMAX_MERGE ties across shards; group isolation (no cross-group delivery) |
| CF-ARG | argmax | 17-bit ids | id 151,935; lowest-index tie; NaN flag |
| CF-KV | kvwb, ingest, mask | ring / selected / ROWS-IKEY vectors | linear append at pos, fence-before-read negative, cache-length mask len−1/len/len+1, ingest NHD→FP8 rows |
| CF-EMB | embedding | BF16 rows | row 151,935, INT8 + scale dequant |
| CF-SVC | KV striping | DS index-key sweep | Qwen 8K dense sweep ≥ 90 % of die bandwidth (owner rule) |
| CF-PROG | sequencer | DS program re-encoded: same tokens and buffers as today | Qwen layer and head records vs simulator, with `wait`, STREAM, LOOP and FENCE negatives |

## 6. Parallel work breakdown

Everything below starts from v0.9 today. Arrows are hard dependencies only.

| ID | Work | Owner | Depends on | First deliverable |
|---|---|---|---|---|
| I0 | This spec and encoder (`tools/hbm_generic_iface.py`) | Claude hbm-iface | — | done (v0.9) |
| C1 | cmdproc fork: CFG window, config bus master, CF-0 checks, TW 18, `cp_vocab`/`cp_ctx_max` registers | **Codex** (cmdproc18 side) | I0 | CF-0 + CF-CP bench |
| C2 | cmdproc sequencer: record fetch from HBM, prefetch ring, `wait`, pred, LOOP, DYN banks, unit-queue dispatch, SIMT.RUN | **Codex** (cmdproc18 side) | I0 | CF-PROG on a 10-record smoke |
| C3 | Config bus receiver (one small module, instanced per block) | **Codex** with C1 | I0 | CF-1 for the receiver |
| H1 | SM `smh_front_c` fmt 3 (in flight, child qwen_r25_fmt3) | Claude | — | CF-SM |
| H2 | RoPE `rope_*` in the q/kv chains and the SU `c_pair` | Claude hbm-su | C3 | CF-ROPE |
| H3 | Norm engine `norm_*` + per-op seg | Claude hbm-su | C3 | CF-NORM |
| H4 | Softmax `sfx_*` | Claude hbm-su | C3 | CF-SFX |
| H5 | SwiGLU `glu_*` | Claude hbm-su | C3 | CF-GLU |
| H6 | Collective group / head rows, 18-bit select | Claude hbm-coll (Codex's qwen-r25-collective branch is input) | C3 | CF-COLL |
| H7 | argmax_m IW 18 | Claude (small) | — | CF-ARG |
| H8 | svc PC striping + posted-write merge | Claude hbm-svc (T3) | — | CF-SVC |
| H9 | kvwb / ingest / causal mask `kv_dense`, embedding `emb_*` | Claude hbm-kv | C3 | CF-KV, CF-EMB |
| H10 | Unit dispatchers (record → native ports) for SM, SU, FUSED, ATT, ARGMAX, COLL, DMA | Claude per block owner (H1–H9), each with its block | C2 encodings | per-unit CF-PROG slice |
| S1 | `hgi_sim` functional: arithmetic library, sequencer, units | Claude hgi-sim | I0 | L1 on a Qwen layer |
| S2 | `hgi_sim` timing + calibration table | Claude hgi-sim | S1, stage benches | L3 composition |
| G1 | `qwen_r25` golden on the arithmetic library | Claude qwen-golden | S1 library | L1 |
| G2 | Qwen r25-order quality run (owner sign-off) | Claude quality | G1 | PASS/FAIL record |
| P1 | Qwen compiler: the 28 families → records, KV/embedding/head layout, TP4 images, the 6 SU-ROM migrations | **Codex** | I0 (encoder), S1 to run | L1 PASS against G1 |
| P2 | DS lowering: committed kernels and native ops → records | Claude ds-control | I0, C2 | CF-PROG DS |
| V1 | Conformance harness (CF-*), vectors from S1 | Claude hgi-sim | S1 | CF tables green |
| M1 | uarch model / `token_path_export` `qwen_hbm` (hbm-generic W1) | Claude | — | priced composition |

The critical path is I0 → S1 → G1 → P1 (L1) → stage benches (L2) → S2 (L3).

The hardware forks H1–H9 depend only on I0 and the config receiver (C3). They run fully in parallel with the software.

## 7. Open items (v0.9 → v1.0)

1. **svc KV path (HIGH).** Until H8 lands, Qwen attention runs at ~1/32 bandwidth. `kv_dense` reads must not target the fixed `KV_PC` path. (PLAN risk 1.)
2. **SM layout rule.** The row split over 32 SMs and the per-SM weight layout must be pinned from the DS image builder before P1 writes weights. Owner: H10 SM dispatcher, within one day.
3. **`attn_scale` literal (resolved).** MD word 17 = FP32(head_dim^-0.5), matching `hdc_golden_v41` (`F(self.hd ** -0.5)`) bit for bit for head dims 512 and 128.
4. **DS embedding row stride.** 10,240 (BF16 × 5,120) is taken from the model shape and must be confirmed against the DS image.
5. **Physical split of the cmdproc** (north/south halves, 16 SMs each). The spec defines one logical sequencer; C2 decides the split.
6. **Qwen MTP** (after τ). Fields for B, STAGES, MARKOV_EN and UNION_EN go into MD words 49–55 at that decision. CTL.TOKX/AMAX/ACCEPT are reserved for it.

## 8. Change rule

- A field is added only when a fused path cannot express a model through data or a per-op field, and the addition comes with its DS reset value and a conformance row.
- Every change bumps the minor version (the CP's version check enforces it), regenerates `spec.json` and both descriptors with the encoder, and is merged with `--check` passing.
- Encodings are never reused. A removed field's bits stay reserved.
