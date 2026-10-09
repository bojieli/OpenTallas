# The HBM Generic Interface (HGI-1)

**Programming and configuration specification for the generic HBM accelerator die: proposed design for owner review**

| | |
|---|---|
| Status | **Proposed design for owner review.** Not yet approved or frozen. |
| Applies to | The r25 HBM accelerator die running Qwen3-8B and DeepSeek-V4.1-Flash, and further dense, mixture-of-experts and linear-attention models through software |
| Machine-readable form | `results/arch/hbm_generic_iface_20261009/spec.json` (authoritative for every bit position), with the two model manifests `manifest_*.json` and descriptors `md_*.hex` |
| Reference encoder and validator | `tools/hbm_generic_iface.py` (`--out <dir>` writes the spec, manifests and descriptors; `--check <dir>` fails on any drift) |
| Simulator | `tools/hgi_sim/` (bit-exact functional and transaction-level timing model) |

## Abstract

The generic HBM (high-bandwidth memory) die is one accelerator design that must run very different language models: Qwen3-8B, a dense transformer; DeepSeek-V4.1-Flash (DS), a large mixture-of-experts (MoE) model with several unusual operators; and, through software, other dense, mixture-of-experts and linear-attention models. HGI-1 is the contract that makes that possible. It defines what software sees of the die: a small set of fixed engines, three kinds of memory, and a stream of self-describing *records* that the die executes for every generated token. Each record names an engine operation and describes every operand with a memory descriptor that carries its own address, shape and number format.

Almost nothing about a model is configured in hardware. A 256-byte *model descriptor* sets three static values at model load (the vocabulary limit, the context limit and the collective group size). Everything else that distinguishes one model from another (its shapes, number formats, rotary-embedding layout, norm widths, sinks and layer mix) lives in the program, in per-operation fields and in data tables.

Every party builds against this one contract. Hardware engineers implement their blocks to it; the simulator models it; the compilers emit it; the goldens (the bit-exact reference models) compute the arithmetic it describes. This document explains the machine, works through one Qwen3-8B decoder layer and one Gated DeltaNet layer record by record, gives the complete encoding reference, and states how conformance is proved.

---

## 1. Introduction

### 1.1 Purpose and audience

This specification is written for an engineer who needs to program, simulate, verify or modify the generic HBM die, including one new to the project. It assumes familiarity with transformer inference (attention, feed-forward layers, the key-value (KV) cache, tensor parallelism) but not with the project's history or block names. Every term is defined at first use and collected in the glossary (Chapter 11).

Chapters 2 to 4 explain the machine, the programming model and the ordering rules. Chapters 5 and 6 are the reference: the model descriptor and every encoding. Chapter 7 maps the target models onto the interface, Chapter 8 defines verification, and Chapter 9 covers extension to other models and the change process. Chapter 10 lists the open questions. Appendix A records the main design decisions and their reasons.

### 1.2 Conventions

- **Normative language.** "Must", "must not" and "only" state requirements. Examples and notes are informative.
- **Bits and words.** Bit 0 is the least significant bit. A *word* is 32 bits. Multi-word values are little-endian: the lowest word holds the lowest bits. A field written `46.0` is word 46, starting at bit 0.
- **Floating-point constants** are stored as their IEEE-754 binary32 bit pattern.
- **Sizes.** B is bytes; KiB is 1,024 bytes; MiB is 1,024 KiB. Addresses in high-bandwidth memory (HBM) are in bytes. Addresses in the vector memory (VM, §2.4) are in 32-bit floating-point (FP32) words.
- **Engines** are written `UNIT.OP`, for example `SM.MATVEC`, the matrix-vector operation of the matrix engine (SM). §2.3 gives every unit's full name, and tables that use the short names carry a legend.

### 1.3 Scope

HGI-1 defines:

- the **model descriptor**, the **model manifest**, the descriptor load path and its error behaviour (Chapter 5);
- the **record** format, the unit operations and the address rule (Chapters 3 and 6);
- the **synchronisation and ordering** rules (Chapter 4);
- the **per-die memory map** (§6.10);
- the **simulator contract**, the goldens and the conformance tests (Chapter 8).

It does not define block-internal ports, physical design, clocking beyond what the configuration path needs, or the host software stack.

### 1.4 Design goals

The die serves one user at a time with the lowest possible decode latency, and every result must match the golden bit for bit. Within those two objectives the interface follows one principle: **keep the hardware minimal and put the complexity in the compiler.** Compilers are written and corrected far more cheaply than silicon, and an interface that asks hardware to understand models becomes obsolete with the next model.

Every way in which one model differs from another therefore has exactly one home, and that home is almost never a hardware setting:

| What differs between models | Where it lives | Hardware cost |
|---|---|---|
| Shapes and numeric constants: widths, heads, layers, epsilon, softmax scale, clamp limit, RoPE tables, norm gains, attention sinks, weight scales, gate constants | **Data and program.** Tables sit in HBM. Constants are record or template immediates. Counts and strides go in memory descriptors. | None |
| Number formats, norm width and segment, softmax mode, rotary pairing, KV layout, argmax id offset, embedding row layout | **Per-operation fields**: the operand descriptor's format, the record's `param` and immediates, the opcode, or (for rotary pairing) a permutation applied to the weights offline | The decode of those fields in each engine |
| The layer mix (attention kind, window, FFN kind, norm kind per layer) | **The model manifest** (software) and the program | None |
| Vocabulary limit, context limit, collective group size | **Three static fields** in the model descriptor, loaded once per model | Range checks and the collective group logic |

---

## 2. Machine model

### 2.1 Overview

The die is a set of fixed-function and programmable **engines** (also called *units*) driven by a single in-order **command processor** (CP). Weights, the KV cache, recurrent state and constant tables live in HBM. Activations live in an on-die scratch memory, the vector memory (VM). A few producer–consumer pairs are joined by hardware first-in, first-out buffers (FIFOs), called STREAM links. Dies of a tensor-parallel group exchange partial results through a collective engine.

```text
                  host: doorbell (token, position, entry)  /  completion (token, status, cycles)
                                       |  ^
                                       v  |
  +----------------------------- CMDPROC (in-order sequencer) ------------------------------+
  |  prefetch ring <- program records from HBM;  predicate;  wait-mask check;  address    |
  |  computation (base + L*lstride + L1*l1stride + DYN or indexed id * dyn_mul);  dispatch |
  +-----+--------+--------+--------+--------+--------+--------+--------+---------+---------+
        |        |        |        |        |        |        |        |         |
       SM      SU/SFU   FUSED     ATT      DMA     COLL    ARGMAX     IDX       HC
     (x32)   templates  norm,   QK, PV   HBM<->VM  cross-  local    top-k,   (DS mix)
     matvec  & GLU      softmax  tiles   KV store  die              indexer
        |        ^                 |        |        |        ^
        +--STREAM (SM -> SU lanes) |        |        |        +--STREAM (LM head -> ARGMAX)
        |                          |        |        |
  ======+==========================+========+========+=====  HBM (per die, 40-bit bytes)
        weights, KV cache, recurrent state, tables, scales, embedding, program image, scratch
  ---------------------------------------------------------  VM (262,144 FP32 words, on die)
        activations, staged tables, id tables; every address chosen by the compiler
```

*Figure 2-1. The die as the program sees it. Each engine has its own in-order queue. STREAM links carry data directly between engines without passing through VM. Short names: CMDPROC command processor; SM matrix engine; SU/SFU stream unit and special-function unit; FUSED fused paths; ATT attention tiles; DMA DMA engine; COLL collective engine; ARGMAX argmax unit; IDX indexer / top-k; HC hyper-connections; VM vector memory.*

### 2.2 The command processor (CP)

The **command processor** (CP, block `hfd_cmdproc`) is the only control engine. It is an in-order sequencer:

1. It fetches **records** from the program image in HBM through a prefetch ring.
2. It evaluates each record's predicate and skips records whose predicate is false.
3. It holds the record until the record's `wait` mask is satisfied (Chapter 4).
4. It computes the effective base address of each operand (§3.3). For an *indexed* operand, the unit dispatcher reads the id from VM.
5. It dispatches the record to the target unit's queue.

Every engine is reached the same way, through records, for every model. Each unit retires its queue in order and reports an outstanding-work count back to the CP. The CP also owns the doorbell and completion interface to the host, the per-slot DYN registers (§3.3) and the model-descriptor load path (Chapter 5).

### 2.3 The engines

Every engine is addressed by a 4-bit **unit code** in the record header. Codes 12–15 are reserved for future engines. Chapter 6 gives the operations each engine accepts.

| Code | Unit | What it does | Main blocks |
|---:|---|---|---|
| 0 | Control (CTL) | Control steps run by the CP itself: loops, fence, end of token, MTP control | `hfd_cmdproc` |
| 1 | Matrix engine (SM) | Matrix-vector product: streams weight rows from HBM against an activation vector. The weight format is chosen per operation (BF16, FP8 block, FP4 block, INT8). 32 SMs per die. | `hfd_sm`, `smh_front_*`, tiles |
| 2 | Stream unit (SU) | The programmable vector pipeline. A 256-bit *SU template* configures its stages (multiply, add, special function, reduce, round). Exact fallbacks run here. | `hfd_su` lanes, `su_red`, `su_full` |
| 3 | Special-function unit (SFU) | The fused SwiGLU chain | `hfd_sfu` |
| 4 | Fused paths (FUSED) | Fused fast paths: the norm engine, the DS hyper-connection norms, the softmax unit and the block quantiser (FP8/FP4 quantise-dequantise) | `norm_engine_view`, `ot_dsrom_su_softmax`, `hfd_quant` |
| 5 | Attention tiles (ATT) | Attention tiles: QK scores and PV products over FP8/BF16 KV rows in HBM | `hfd_attn_half_*` |
| 6 | Collective engine (COLL) | Cross-die collectives: all-reduce, all-gather, top-k merge, argmax merge, sub-group reduce with multicast, row gather from owner dies | `hfd_coll` |
| 7 | Argmax unit (ARGMAX) | Local argmax over a logit shard | `ot_dshbm_argmax_m` |
| 8 | DMA engine (DMA) | Row moves between HBM and VM, the KV append, the DS KV write-back and the HBM write fence | svc, `hfd_loader`, kvwb |
| 9 | Indexer / top-k (IDX) | Generic top-k selection, the DS indexer engines and the Engram hash | DS selector, indexer, `ot_hdc_engram_hash` |
| 10 | Hyper-connections (HC) | DeepSeek hyper-connection mix | `hfd_hc` |
| 11 | SIMT engine (SIMT) | **Optional; absent on r25.** Launches a general-purpose SIMT kernel on dies that have a kernel engine. | — |
| 12–15 | — | Reserved | — |

The r25 die's matrix engines are fixed-function matrix-vector elements with no kernel memory, so r25 has no SIMT (single-instruction, multiple-thread) kernel engine. A record sent to an absent unit faults with completion status 3. Everything r25 runs is expressed with units 0–10.

### 2.4 The memory hierarchy

A record names each operand by a **memory descriptor** whose `space` field selects one of three memories (or none):

- **HBM** is one die-local byte address space, 40 bits wide, organised in 32-byte sectors. It holds everything large or persistent: weights, the KV cache, recurrent state for linear-attention layers, constant tables (rotary position embedding (RoPE) rows, norm gains, sinks, scales, gate constants), the embedding table, the program image and spill space. The service layer (svc) maps sectors onto stacks and pseudo-channels (PCs) with a fixed map.
- **VM** (vector memory) is the on-die scratch: 262,144 FP32 words per die, addressed in words. It holds activations, staged tables and id tables. The compiler allocates every VM address; hardware has no allocator.
- **STREAM** is a hardware FIFO between a fixed producer and a fixed consumer, for example matrix-engine results into stream-unit lane registers, or the language-model (LM) head's matrix-vector product into the argmax unit. Data on a STREAM never touches VM. The set of stream ids a die supports is fixed by its wiring.

STREAM operands implement the project's dataflow rule that a value returns to shared memory only when another lane, unit or die needs it (AGENTS.md dataflow level 2).

### 2.5 Data flow through a token

For one token, data moves in a fixed pattern:

- **Weights** flow from HBM through the SMs once per token and are never stored on die.
- **Activations** stay in VM (or in STREAM links) from the embedding lookup to the final logits.
- **New KV rows** are written from VM to HBM by `DMA.STORE` (or `DMA.KVWB_DS` for DS); **old KV rows** flow from HBM into the ATT tiles.
- **Recurrent state** of a linear-attention layer is loaded into VM, updated by the SU and written back.
- **Partial sums** of tensor-parallel matrix products cross dies through `COLL`.
- **The next token** leaves the die in the completion record.

### 2.6 Die groups and SPMD execution

A model runs on a **group** of dies that split each layer's matrices between them (tensor parallelism, TP): Qwen3-8B uses 4 dies, DeepSeek-V4.1-Flash 96. Every die runs a program of the **same structure** (single program, multiple data, SPMD):

- Each die has its own program image in its own HBM. The images of a group must be identical record for record in unit, operation, operand slots and the order of collectives. They may differ in descriptor values and immediates, and a record that a rank does not run is replaced by `CTL.NOP`, so the collectives of every die still line up.
- Where a die's slice is a uniform function of its rank, one image serves every die and addresses the slice with the DYN value `RANK` (§3.3). Where it is not, for example an even split of n rows over G dies when G does not divide n (rank r owns rows ⌊r·n/G⌋ to ⌊(r+1)·n/G⌋ − 1), the compiler writes the rank's own constants into that rank's image.
- The descriptor's `image_base` is a die-local address, so one model descriptor serves every die.

Qwen3-8B uses one image for all four dies. DS uses 96 images of identical structure. Per-die images need no hardware: the CP of each die already fetches from its own HBM.

Groups are **aligned** blocks of die ids. A die's rank is `die_id mod group_size`, its group is `die_id div group_size`, and reductions combine contributions in rank order. Legal group sizes are 1, 2, 4 and 8 (on the collective engine's 8-input reduction tree, with inactive inputs presented as +0) and 96 (the DS configuration and the reset value). At 96, reductions run as 12 aligned sub-groups of 8 ranks (`COLL.GROUP_REDUCE_MCAST` with s = 8, the shipped DS order); a 96-way `ALL_REDUCE_SUM` is rejected (§6.7).

---

## 3. Programming model

### 3.1 Programs, images and entry points

A **program** is a sequence of records stored in the **program image**, a region of HBM placed by the compiler. The model descriptor records the image's base and size (in 4 KiB pages) and up to three **entry points**, each a record offset into the image in 16-byte units:

- `entry_ar`: the normal autoregressive (AR) decode step, one token;
- `entry_verify`: the multi-token prediction (MTP) verify pass (0 if absent);
- `entry_draft`: the MTP draft pass (0 if absent).

### 3.2 The record

A **record** is one unit operation with everything it needs. It has three parts:

1. a **128-bit header** (UOP) naming the unit and operation, the wait mask, a predicate, which operand descriptors follow, a 25-bit parameter and two 32-bit immediates;
2. optionally, a **256-bit SU template** (SUT), present when the header's `tmpl` bit is set, which configures the vector pipeline;
3. one **256-bit memory descriptor** (MDESC) for each operand the record names, in the fixed order **A, B, C, D, O, R, I**.

The seven operand slots have fixed roles:

*Units and terms in this table:* Stream unit (SU) · Vector memory (VM).

| Slot | Role |
|---|---|
| A, B, C, D | Sources. For an SU template, the pipeline's four inputs (D is, for example, the RoPE sine). For other units, as each operation defines (§6.6). |
| O | The element-wise result. |
| R | A reduction result (one value per outer row), for templates and operations that reduce. |
| I | An id table in VM used for gathers and for indexed addressing (§3.3). |

A record is therefore 16 to 272 bytes long. Programs are per die but share one structure (§2.6). Because each record carries its own addresses, counts and formats, one SU template can serve every layer, and two consecutive records may use the same engine in different ways.

### 3.3 Addressing

**Two-level arrays.** A memory descriptor describes `m` rows of `n` elements. Elements within a row are `istride` apart (0 means 1); rows are `stride` apart. The element format is `fmt`.

**Broadcast.** When the descriptor's `ibcast` bit is set, the inner stride is 0: every element of a row reads the same value. This gives per-row scalars without copying, for example the softmax maximum and normaliser of each head, a per-head gate, or a row scale.

**The effective base.** The CP computes one effective base per descriptor:

> **effective base = base + L · lstride + L1 · l1stride + X · dyn_mul**, where X = DYN[`dyn_sel`] for a normal descriptor, and X = U32(VM[I + L]) for an *indexed* descriptor.

This is the only address arithmetic the hardware performs on the program's behalf. Its terms are:

- **`L` and `L1`**, the counters of the inner and outer loops (`CTL.LOOP`, §3.4). With `lstride` set to the per-layer size of a weight block, one record addresses every layer's weights. With `l1stride` set to the per-head size of a state block, one record serves every local head.
- **DYN values**, small per-token integers the CP computes when the doorbell arrives. `POS` (the token's position) addresses the RoPE row and the KV append slot; `TOKEN` addresses the embedding row; `RANK` addresses a die's shard; `POS1 = pos + 1` is the number of valid KV rows. Each verify column (*slot*) has its own DYN bank. §6.8 lists every code.
- **Indexed ids.** When the descriptor's `indexed` bit is set, the id comes from row 0 of the record's I table in VM, entry L. The I table is typically written by `IDX.TOPK` (the selected experts or KV positions) and ordered before its readers by a wait bit. Id bounds are software-owned: the compiler guarantees that every indexed id lands in a placed region; the hardware checks only that the effective address fits the 40-bit HBM space (or the VM); the simulator faults any out-of-region access as a compiler-bug detector.

**Dynamic counts.** When `n_sel` is non-zero, `n = DYN[n_sel]`. Attention uses `n_sel = POS1` to read exactly the `pos + 1` valid KV rows, and that count is also the causal mask. The special code `n_sel = 63` (N_FROM_VM) takes `n` from row 1 of the I table: U32(VM[I + I.stride + L]).

**The indexed stream form.** A `DMA.LOAD` whose source descriptor is indexed and whose `n_sel` is N_FROM_VM fetches a list of rows chosen by id, such as the KV rows that the DS indexer selected. The DMA dispatcher reads the I table and hands the svc one stream command plus the id list. The svc fetches the rows from the PCs that own them, in parallel, and the rows are delivered in list order.

### 3.4 Predicates and loops

A record's 2-bit **predicate** decides whether it runs: always, only at position 0, only at positions other than 0, or only on the last loop iteration. A skipped record has no effect.

`CTL.LOOP` and `CTL.ENDLOOP` bracket a body that runs `count` times. The loop's level selects its counter: level 0 drives `L`, level 1 drives `L1`. Two levels may nest, for example layers (`L`) around per-head records (`L1`). Loop bodies replay from the prefetch ring, so a body must fit the ring. Unrolled programs are equally legal.

### 3.5 The life of a token

```text
  host                         CMDPROC                                  engines
   |  doorbell {token, pos,      |                                         |
   |   job, gen, entry, ncol} -->|  range-check token < cp_vocab,          |
   |                             |  pos < cp_ctx_max; fill DYN banks       |
   |                             |  (POS, POS1, TOKEN, RANK, SLOT, ...)    |
   |                             |  fetch records from entry point ------->|  one queue per unit,
   |                             |  for each record:                       |  in-order retire
   |                             |    predicate? wait mask satisfied?      |
   |                             |    compute bases; dispatch ------------>|  SM / SU / ATT / ...
   |                             |<---------- outstanding counts ----------|
   |                             |  ...                                    |  COLL <-> other dies
   |                             |  CTL.END: token = A[0], range-checked   |
   |<-- completion {token, pos,  |                                         |
   |    job, gen, status, cycles}|                                         |
```

*Figure 3-1. One token from doorbell to completion.*

**Doorbell.** The host starts a token by ringing the doorbell with `{token 18, pos 20, job 32, gen 4, entry 2, ncol 4}` (field widths in bits). `token` is the input token (the previous step's output), `pos` its position, `entry` selects the entry point (AR, verify, draft), and `ncol` is the number of positions for a verify pass (1 at AR). The CP refuses the doorbell (`db_rdy` = 0) while a descriptor commit is settling (§5.5).

**Records.** The CP fills the DYN banks and runs records from the entry point. The token's work is entirely described by the records; no engine starts on its own.

**Completion.** `CTL.END` names a U32 operand A whose element 0 is the result token, normally the output of `COLL.ARGMAX_MERGE`. The CP range-checks it against `cp_vocab` and returns the completion `{token 18, pos 20, job, gen, status 4, cycles}`. Status codes: 0 OK, 1 unit fault, 2 no result, 3 bad command or range (including a record sent to an absent unit).

### 3.6 Worked example: one Qwen3-8B decoder layer

This section traces the program for one Qwen3-8B token on one die of a 4-die group (TP4) at AR decode, with full attention over an 8,192-row context. It is the program the simulator runs bit-exact against the `qwen_r25` golden (`tools/hgi_sim/qwen_compiler.py`), shown in this document's encoding.

**Shapes.** Qwen3-8B has a hidden width of 4,096, 36 layers, 32 query heads and 8 KV heads of dimension 128, and a feed-forward network (FFN) width of 12,288. At TP4 each die holds 8 query heads and 2 KV heads, so its QKV projection has 1,024 + 256 + 256 = 1,536 rows, its output projection takes 1,024 inputs, and its gate/up and down projections cover 3,072 FFN columns. Weights are 8-bit integers (INT8) with one bfloat16 (BF16) scale per output row. The q and k rows of W_q and W_k (and the gains of the per-head query/key norm, QK-norm) are permuted offline so that the rotary pairs are adjacent elements (§7.2).

**VM placement** (FP32 words): residual stream X at 0; normalised input H at 4,096; raw QKV at 8,192; scaled QKV at 9,728; QK-normalised heads at 11,264; the RoPE cos/sin row at 12,544; rotated heads at 12,800; BF16 queries at 14,080; scores at 15,104 (8 heads × 8,192); exponentials at 80,640; per-head maxima at 146,176 and sums at 146,304; the probability-weighted values (PV) at 146,432; attention output at 147,456; output-projection partial and sum at 148,480 and 152,576; staged row scales at 156,672; raw and scaled gate/up at 162,816 and 168,960; SwiGLU (SiLU-gated linear unit) output at 175,104; down partial and sum at 178,176 and 182,272.

**HBM placement**: each layer's weights, scales and gains form one block of 48,283,648 bytes, so every weight descriptor uses `lstride` = 48,283,648 and the layer loop counter L selects the layer. Within the block, W_qkv is at offset 0, its scales at 6,291,456, W_o at 6,294,528, W_gu at 10,497,024, W_down at 35,675,136, and the gains at 48,266,240 onward. The KV cache gives each layer 2 heads × {K, V} planes of 8,192 rows × 128 bytes (8-bit floating point, FP8), so a plane is 1 MiB and `lstride` for KV is 4 MiB. `Wb`, `Tb` and `KVb` below are the weight, table and KV region bases.

**Prologue** (once per token). Records 0–3 fetch the embedding row and the RoPE row:

*Units and terms in this table:* Control (CTL) · Stream unit (SU) · DMA engine (DMA) · Vector memory (VM).

| # | Record | Operands | `param`, immediates | `wait` |
|---:|---|---|---|---|
| 0 | `DMA.LOAD` | A: HBM EMBED, INT8, n = 4,096, `dyn_sel` = TOKEN, `dyn_mul` = 4,128; O: VM 0 | — | — |
| 1 | `DMA.LOAD` | A: HBM EMBED + 4,096, BF16, n = 1, `dyn_sel` = TOKEN, `dyn_mul` = 4,128; O: VM scale word | — | — |
| 2 | `SU.VOP` | A: VM 0 (codes); B: the scale word, `ibcast`; O: VM 0 | template M1 = A·B | DMA |
| 3 | `DMA.LOAD` | A: HBM `Tb` + RoPE table, FP32, 256 words, `dyn_sel` = POS, `dyn_mul` = 1,024; O: VM 12,544 | — | — |
| 4 | `CTL.LOOP` | — | count = 36, level 0 | — |

*Table 3-1. The prologue.*

**The layer** (records 5–36, replayed 36 times with L = 0 … 35):

*Units and terms in this table:* Control (CTL) · Matrix engine (SM) · Stream unit (SU) · Special-function unit (SFU) · Fused paths (FUSED) · Attention tiles (ATT) · Collective engine (COLL) · DMA engine (DMA) · Vector memory (VM).

| # | Record | Operands | `param`, immediates | `wait` | Family |
|---:|---|---|---|---|---|
| 5 | `FUSED.ROW_NORM` | A: VM 0, n = 4,096; B: HBM ln1 gain, BF16; O: VM 4,096, **BF16** | d_units = 32, seg = 0; `imm_a` = eps (`0x358637BD`) | SU | prenorm |
| 6 | `SM.MATVEC` | A: VM 4,096; B: HBM `Wb`, m = 1,536 rows of n = 4,096, INT8, `lstride` = layer; O: VM 8,192 | fmt = 3 (INT8) | FUSED | qkv |
| 7 | `DMA.LOAD` | A: HBM qkv scales, BF16, n = 1,536; O: VM 156,672 | — | — | row_scale_qkv |
| 8 | `SU.VOP` | A: VM 8,192; B: VM 156,672; O: VM 9,728 | M1 = A·B | SM, DMA | row_scale_qkv |
| 9 | `FUSED.ROW_NORM` | A: VM 9,728, 8 heads × 128; B: q-norm gain; O: VM 11,264, **FP32** | d_units = 8, seg = 128 | SU | QK-norm |
| 10 | `FUSED.ROW_NORM` | A: VM 10,752, 2 heads × 128; B: k-norm gain; O: VM 12,288, FP32 | d_units = 2, seg = 128 | — | QK-norm |
| 11 | `SU.VOP` | A: VM 11,264, m = 10 heads of n = 128; B: cos row (stride 0); D: sin row (stride 0); O: VM 12,800 | `c_pair`, QM alternating sign, AD = +Q, M1 = A·B | FUSED | RoPE |
| 12 | `SU.VOP` | A: VM 12,800, n = 1,024; O: VM 14,080 | `rnd` (BF16 queries) | — | roundQ |
| 13 | `DMA.STORE` | A: rotated K rows, m = 2 of n = 128; O: HBM `KVb` K planes, FP8, `stride` = 2 MiB, `lstride` = 4 MiB, `dyn_sel` = POS, `dyn_mul` = 128 | — | SU | kv_append |
| 14 | `DMA.STORE` | A: V rows (VM 11,008); O: the V planes, as record 13 | — | — | kv_append |
| 15 | `DMA.FENCE` | — | — | — | kv_fence |
| 16, 17 | `ATT.QK` (one per KV head h) | A: VM 14,080 + 512·h, 4 query heads; B: HBM K plane of head h, FP8, `n_sel` = POS1; O: VM 15,104 + 4·8,192·h, 4 rows, `n_sel` = POS1 | lanes = 4, slices − 1 = 1 | DMA (16) | attention_qk |
| 18 | `SU.VOP` | A: scores, m = 8 heads, `n_sel` = POS1; R: VM 146,176 (one max per head) | M1 = A·imm1 (imm1 = scale `0x3DB504F3`), RED = MAX | ATT | softmax |
| 19 | `SU.VOP` | A: scores; B: the maxima, `ibcast`; O: VM 80,640; R: VM 146,304 (one sum per head) | M1 = A·imm1, AD = −B, SFU = EXP, RED = SUM | — | softmax |
| 20 | `SU.VOP` | A and O: VM 80,640 | `rnd` (BF16 probabilities) | — | softmax |
| 21, 22 | `ATT.PV` (one per KV head) | A: exponentials of the 4 heads; B: HBM V plane, `n_sel` = POS1; O: VM 146,432 + 512·h | lanes = 4, slices − 1 = 1 | SU (21) | attention_pv |
| 23 | `SU.VOP` | A: VM 146,432, m = 8 × 128; B: the sums, `ibcast`; O: VM 147,456 | M1 = A / B | ATT | pv_normalize |
| 24 | `SM.MATVEC` | A: VM 147,456, n = 1,024; B: HBM W_o, m = 4,096 rows, INT8; O: VM 148,480 | fmt = 3 | SU | o |
| 25 | `COLL.ALL_REDUCE_SUM` | A: VM 148,480 (4,096); O: VM 152,576 | group of 4, rank order | SM | all_reduce_o |
| 26 | `DMA.LOAD` | A: HBM o scales; O: VM 156,672 | — | — | row_scale_o |
| 27 | `SU.VOP` | A: VM 152,576; B: VM 156,672; C: VM 0; O: VM 0 | M1 = A·B, AD = +C | COLL, DMA | row_scale_o + residual |
| 28 | `FUSED.ROW_NORM` | as record 5 with the ln2 gain | d_units = 32, seg = 0 | SU | prenorm |
| 29 | `SM.MATVEC` | A: VM 4,096; B: HBM W_gu, m = 6,144 rows (gate then up), INT8; O: VM 162,816 | fmt = 3 | FUSED | gu |
| 30 | `DMA.LOAD` | A: HBM gate/up scales; O: VM 156,672 | — | — | row_scale_gu |
| 31 | `SU.VOP` | A: VM 162,816; B: VM 156,672; O: VM 168,960 | M1 = A·B | SM, DMA | row_scale_gu |
| 32 | `SFU.GLU` | A: VM 168,960 (gate); B: VM 172,032 (up); C: constant 1.0, `ibcast`; O: VM 175,104, **BF16** | `imm_a` = FLT_MAX (no clamp) | SU | SwiGLU |
| 33 | `SM.MATVEC` | A: VM 175,104, n = 3,072; B: HBM W_down, m = 4,096 rows, INT8; O: VM 178,176 | fmt = 3 | SFU | down |
| 34 | `COLL.ALL_REDUCE_SUM` | A: VM 178,176; O: VM 182,272 | group of 4 | SM | all_reduce_down |
| 35 | `DMA.LOAD` | A: HBM down scales; O: VM 156,672 | — | — | row_scale_down |
| 36 | `SU.VOP` | A: VM 182,272; B: VM 156,672; C: VM 0; O: VM 0 | M1 = A·B, AD = +C | COLL, DMA | row_scale_down + residual |
| 37 | `CTL.ENDLOOP` | — | — | — | — |

*Table 3-2. The decoder layer. A wait entry names only other units; a unit's own records are ordered by its queue (§4.1).*

**Epilogue.** Records 38–44 run the final norm (`FUSED.ROW_NORM`), the LM head (`SM.MATVEC`, 37,984 rows on this die), its row scale (`DMA.LOAD` + `SU.VOP`), `ARGMAX.LOCAL` with `imm_a` = 37,984 (so that global id = local id + rank · 37,984), `COLL.ARGMAX_MERGE` into a U32 word in VM, and `CTL.END` reading that word. The whole token is 45 records in the image; with the loop, 1,163 records execute.

**Walking through the layer.**

- **Pre-attention norm (5).** The norm engine reads the residual stream, the gain and epsilon, and publishes BF16 because the output descriptor's format is BF16. `d_units = 32` selects the 4,096-wide reduction tree; `seg = 0` means one norm over the whole vector.
- **QKV projection and row scale (6–8).** The SM streams 1,536 INT8 rows and writes raw FP32 sums. The SU multiplies each by its BF16 row scale; that multiply is the golden's rounding point. The scales are staged into VM by record 7, which can run while the SM works.
- **QK-norm (9, 10).** Qwen normalises each query and key head separately. `seg = 128` makes the norm engine produce one result per 128-element segment. QK-norm publishes FP32 in the same layer in which the prenorm publishes BF16; that is why the format belongs to the output descriptor and not to a global mode.
- **RoPE and rounding (11, 12).** Because the weights were permuted offline, every rotary pair is two adjacent elements, and the template's `c_pair` reads element i's partner at i XOR 1. B supplies the cosine and D the sine; both descriptors have stride 0, so all 10 heads reuse the one row fetched in the prologue. Queries are then rounded to BF16.
- **KV append and fence (13–15).** `DMA.STORE` writes this position's K and V rows into the per-head planes, converting to FP8, at `POS · 128` bytes into each plane. `DMA.FENCE` makes the posted writes visible before attention reads them.
- **Attention scores (16, 17).** Each KV head serves 4 query heads, so one ATT tile uses 4 of its 16 lanes. `n_sel = POS1` reads exactly the `pos + 1` valid rows; that count is the causal mask.
- **Softmax (18–20).** The bound path for Qwen is the exact SU fallback in three records: the per-head maximum of the scaled scores, then exp(scaled score − max) with the per-head sum in the same pass, then BF16 rounding of the exponentials. The scale is the golden's literal FP32(128^−0.5), carried as an immediate and never folded into the weights. The maxima and sums are per-head scalars, read with `ibcast`. The fused `FUSED.SOFTMAX` fast path replaces these records once its conformance test proves it bit-identical (§8.4, CF-SFX).
- **PV and normalisation (21–23).** ATT multiplies the unnormalised BF16 probabilities by the V rows; the SU then divides each head's 128 outputs by that head's sum.
- **Output projection, all-reduce, scale and residual (24–27).** Each die multiplies its 1,024 attention outputs by its slice of W_o and produces a 4,096-wide partial sum. `COLL.ALL_REDUCE_SUM` adds the four partials in rank order on every die. One SU template then applies the row scale (M1 = A·B) and adds the residual (AD = +C) in place: two families in one record, with the golden's two rounding points.
- **Feed-forward (28–36).** The second norm, the gate/up projection (6,144 rows), the row scales, the SwiGLU chain on the SFU, the down projection, the second all-reduce, and the scale-plus-residual. SwiGLU's per-operation settings say what Qwen needs: BF16 output (O format), no clamp (`imm_a` = FLT_MAX) and no route weight (C is a constant 1.0, broadcast).

### 3.7 Worked example: one Gated DeltaNet layer

Linear-attention layers run in software on the same engines. This example is one Gated DeltaNet (GDN) decode layer at Qwen3-Next dimensions (hidden width 2,048; 16 key heads and 32 value heads of dimension 128; a 4-tap causal convolution) on one die of TP4, which holds 4 key heads and 8 value heads. The simulator runs this layer bit-exact against its golden on all four dies (`tools/hgi_sim/gdn.py`), and the golden matches the transformers reference to an rms relative error of 5.8e-7 before the BF16 projection rounding.

A GDN head keeps a 128 × 128 FP32 **state** matrix S instead of a KV cache. Each token decays S, corrects it towards the new key/value pair (the delta rule), and reads it with the query. The state lives in HBM region STATE, **transposed** (`[dv][dk]` row-major per head) so that the SU's inner-index reduction computes S·k and S·q. It never passes through ATT, whose rows are FP8 or BF16.

*Units and terms in this table:* Control (CTL) · Matrix engine (SM) · Stream unit (SU) · Fused paths (FUSED) · Collective engine (COLL) · DMA engine (DMA).

| Step | Records | What they do |
|---|---|---|
| Prenorm | `FUSED.ROW_NORM` | RMSNorm of the residual, BF16 out |
| Input projections | 2 × `SM.MATVEC` (fmt 0, BF16 weights) | q, k, v, z (output gate) and b, a (gate inputs) for the die's heads |
| Convolution | `DMA.LOAD` (ring from STATE); 3 × `SU.VOP` (append the new q, k, v inputs as tap 4); `SU.VOP` with R (4-tap sum per channel); `SU.VOP` (SiLU); `DMA.STORE` (ring back, minus the oldest tap) | The causal conv1d over a 4-token ring per channel |
| L2 norm | 4 × `SU.VOP` | Sum of squares per head (R, `red_sq`), rsqrt(+eps), then q scaled by 128^−0.5 and k, each reading its head's factor with `ibcast` |
| Gates | `DMA.LOAD` (−exp(A_log) and dt_bias); `SU.VOP` (β = sigmoid(b)); a sequence of `SU.VOP` records for softplus(a + dt_bias); `SU.VOP` (α = exp(softplus · −exp(A_log))) | Per-head decay α and write strength β. Softplus is an exact SU template sequence (the series log1p of the golden); there is no softplus function code. |
| State in | `DMA.LOAD` from STATE, 8 heads × 16,384 words | 512 KiB per die per layer |
| Delta rule | `CTL.LOOP` level 1 over the 8 local value heads around: `SU.VOP` decay (S = α·S, α by `ibcast`) and `SU.VOP` with R (kv = S·k). Then one `SU.VOP` for all heads: δ = (v − kv)·β. Then a second level-1 loop around: `SU.VOP` update (S = S + k·δ) and `SU.VOP` with R (o = S·q). | The recurrence. `l1stride` steps the state, k, q and δ descriptors from head to head, so each family is one record in the image. Key head = value head div 2 (the GQA map). |
| State out | `DMA.STORE` to STATE | Written back for the next token |
| Gated norm | `FUSED.ROW_NORM` seg 128, FP32 out; `SU.VOP` (o · SiLU(z)) | Per-head RMSNorm, then the output gate |
| Output | `SM.MATVEC`, `COLL.ALL_REDUCE_SUM`, `SU.VOP` (residual add) | The output projection over the die's 1,024 value columns, the TP4 sum and the residual |

*Table 3-3. One GDN decode layer on one die.*

Three features of the record format carry this layer: the R slot (every reduction writes one value per row), `ibcast` (per-head scalars such as α, β and the norm factors), and the second loop level (per-head replay). The STATE region is not position-indexed, which matters for speculative decoding (§10.1).

---

## 4. Synchronisation and ordering

### 4.1 Ordering within a unit

Each unit receives records in program order and retires them in order. A unit starts a record only after the previous record of the same unit has made its writes visible to that unit. A record therefore never needs a wait bit for its own unit. Results and faults of one unit appear in program order.

### 4.2 The four mechanisms

Ordering between units is established by exactly four mechanisms. There are no semaphores, events or kernel-level barriers.

**1. The `wait` mask: unit drain.** The header carries 16 wait bits; bit u names unit code u. The CP issues the record only when every unit named in the mask has nothing outstanding. The compiler computes the mask from region hazards: a record waits for another unit when it reads a region that unit wrote, or writes a region that unit read or wrote, since that unit last drained (read-after-write, write-after-read, write-after-write).

*Example:* in Table 3-2, record 6 (`SM.MATVEC`) reads the normalised vector that record 5 (`FUSED`) wrote, so it waits on FUSED. Record 8 reads both the SM's raw sums and the DMA's staged scales, so it waits on SM and DMA.

*Hazards covered:* all cross-unit memory dependences, including an indexed descriptor's I table, which must be written before the record that reads it issues.

**2. STREAM credits: producer to consumer.** When a producer and a consumer are joined by a STREAM link, the consumer's record needs no wait bit. The FIFO's credit flow control orders the data: the consumer cannot read an element before the producer has written it, and the producer cannot overrun the consumer.

*Hazards covered:* read-after-write on the streamed data, at element granularity, while both engines run concurrently.

**3. Collective arrival: cross-die.** Collectives synchronise themselves by data arrival. Every die of a group issues the same collectives in the same program order, and the collective endpoint matches them with a per-group sequence counter. A die's `COLL` record completes when the contributions it needs have arrived.

*Example:* record 25 completes on each die only when all four partial sums have arrived; record 27 waits on COLL.

**4. `CTL.FENCE` and `DMA.FENCE`: HBM write visibility.** HBM writes are posted. `CTL.FENCE` waits for all units and for every posted HBM write to be visible. `DMA.FENCE` makes the DMA unit's writes (for example a KV append) visible to the next reader.

*Example:* record 15 orders the KV append before the attention reads in records 16 and 21.

### 4.3 The head-of-line and drain caveat

Two consequences of this model affect performance, not correctness:

- **Drain is coarse.** A wait bit waits for the whole unit to drain, not for one specific earlier record.
- **The sequencer is in order.** A record held by its wait mask also holds every record behind it, including records for idle units (head-of-line blocking).

The compiler hides both by scheduling independent chains between dependent ones (AGENTS.md dataflow level 4). The simulator models both effects. Its pathfinding estimates put the CP's total overhead at 1.8 % of a Qwen3-8B token at position 8,191, and at 3.8 % of a DS token at 1M context after CP-aware list scheduling. The remaining cost is the CP-to-unit round trip on each dependent hop of the serial chain.

### 4.4 Transaction-level exactness

Latency may change between implementations, but the order of results and faults may not: it is fixed by program order within a unit and by the four mechanisms. Every result is bit-exact against the golden regardless of timing.

---

## 5. Model configuration

### 5.1 The model descriptor and the model manifest

A model is described at two levels:

- The **model descriptor** (MD) is a 64-word, 256-byte image that the hardware reads at model load. It holds three static fields, the program's entry points and image location, a hash that binds it to one manifest, and a cyclic redundancy check (CRC).
- The **model manifest** is a versioned JSON file that software reads: the compiler, the golden, the simulator and the table generator. It has global values (hidden width, vocabulary, RoPE θ and scaling, softmax-scale literal, weight and KV formats, TP size, head rows per die) and **one row per layer** (mixer kind and heads, window, RoPE span and pairing, DS compression ratio and source flags, Engram, FFN kind, norm). Per-layer rows let one model mix layer types, for example full attention with GDN, or dense layers before MoE layers.

The descriptor carries the manifest's sha256 in words 32–39. The encoder generates both from the model's checked-in `config.json`.

### 5.2 Descriptor layout

The descriptor is 64 little-endian 32-bit words. Every reserved bit must be 0; the CP rejects a set reserved bit. `spec.json` → `md_fields` is the authority for every bit position.

*Units and terms in this table:* Command processor (CP).

| Words | Content | Read by |
|---|---|---|
| 0 | magic `0x31494748` ("HGI1") | CP |
| 1 | version 1.0 (minor in bits 7:0, major in 15:8), length 64 (bits 23:16) | CP |
| 2–31 | reserved | — |
| 32–39 | sha256 of the model manifest | software |
| 40 | `cp_vocab` (bits 17:0) | CP |
| 41 | `cp_ctx_max` (bits 20:0) | CP |
| 42–45 | reserved | — |
| 46 | `coll_group_size` (bits 7:0) | collective |
| 47–48 | reserved | — |
| 49, 53–55 | reserved for MTP parameters (§10.3) | — |
| 50–52 | reserved for window and chunk parameters (§10.2) | — |
| 56–58 | entry offsets: AR, verify, draft | CP |
| 59 | reserved | — |
| 60–61 | program image base and size in HBM, in 4 KiB pages | CP |
| 62 | reserved | — |
| 63 | IEEE CRC-32 of words 0–62 | CP |

### 5.3 The three static fields

| Field (word.bit) | Bits | Legal | DS (reset) | Qwen3-8B | Purpose, and why it is static |
|---|---:|---|---:|---:|---|
| `cp_vocab` (40.0) | 18 | 1 … 2¹⁸ − 1 | 129,280 | 151,936 | Range check for doorbell and completion tokens. A token id is 18 bits everywhere (doorbell, completion, argmax). The limit is a safety check on the host interface, so it is per model, not per operation. |
| `cp_ctx_max` (41.0) | 21 | 1 … 2²⁰ | 2²⁰ | 40,960 | Range check for the doorbell position. Positions are 20 bits. |
| `coll_group_size` (46.0) | 8 | 1, 2, 4, 8, 96 | 96 | 4 | Which dies form a group. Membership is genuinely static configuration: every collective on a die uses the same group. At 96, reductions run as 12 sub-groups of 8 (`GROUP_REDUCE_MCAST` s = 8); `ALL_REDUCE_SUM` at 96 is rejected. The values 16, 32 and 64 are defined encodings that the range check rejects until a collective engine that builds them exists. |

Each static field resets to the DS value. DS programs also carry DS's own per-operation settings in their records, so loading the DS descriptor changes nothing, and a DS test bench that never loads a descriptor still runs. The static fields change only when a model is loaded while the die is idle; they never change while it is decoding.

### 5.4 Per-operation settings that replace modes

Every other model-dependent setting is carried by the operation that needs it, not by a global setting. Two consecutive records may therefore use the same engine in different ways, and one program can mix layer types. The engines decode these fields per record:

*Units and terms in this table:* Stream unit (SU) · Special-function unit (SFU) · Fused paths (FUSED) · Attention tiles (ATT) · Argmax unit (ARGMAX) · DMA engine (DMA).

| Setting | Where it lives | DS value | Qwen3-8B value |
|---|---|---|---|
| Norm width | `FUSED.ROW_NORM` `param[5:0]` d_units (width / 128: 32 or 40 for the prenorms; 8 and 2 for the Qwen3-8B TP4 QK-norms, 8 query and 2 key heads of 128). The 4,096 tree is the 5,120 tree with a +0-padded tail, which is exact. | 40 | 32 (prenorm), 8 / 2 (QK-norm) |
| Norm segment | `FUSED.ROW_NORM` `param[13:6]` (0 or 128) | 0 | 0 (prenorm), 128 (QK-norm) |
| Norm, GLU and softmax output format | The O descriptor's `fmt` (FP8, BF16 or FP32 for norms; FP8 or BF16 for GLU) | FP8 | BF16 (prenorm, GLU), FP32 (QK-norm) |
| Hyper-connection pre-mix | The opcode: `FUSED.HC_PRE_NORM` versus `FUSED.ROW_NORM` | HC_PRE_NORM | ROW_NORM |
| Attention sink | Data: the B operand of `FUSED.SOFTMAX`. A sink of −2¹⁰⁰ is bit-identical to no sink. | the model's sinks | −2¹⁰⁰ |
| Softmax multipass | `FUSED.SOFTMAX` `param[0]` | as the rows require | 1 (rows > 640) |
| SwiGLU clamp | `SFU.GLU` `imm_a` = the limit; FLT_MAX disables it exactly | 10.0 | FLT_MAX |
| Route weight | `SFU.GLU` C operand; a constant 1.0 with `ibcast` disables it exactly | the routing weights | 1.0 |
| RoPE pairing and span | The weights (rows permuted offline so pairs are adjacent) and the RoPE record's descriptor range | adjacent, last 64 dims | adjacent after permutation, all 128 dims |
| KV layout | The opcode: `DMA.STORE` (linear append) versus `DMA.KVWB_DS` (DS window ring); the mask is the ATT B descriptor's `n_sel` | `DMA.KVWB_DS` | `DMA.STORE` |
| Argmax id offset | `ARGMAX.LOCAL` `imm_a` (global id = local id + RANK · `imm_a`) | 1,347 (uniform 1,347-row head shards; the last rank holds 1,315 rows; rows are independent dot products, so the logits are unchanged) | 37,984 |
| Embedding row | The `DMA.LOAD` descriptor (TOKEN · row bytes, `fmt`) plus an SU dequantisation | BF16 rows of 10,240 B | INT8 rows of 4,128 B (codes + BF16 scale + padding) |

### 5.5 The configuration path

The descriptor reaches the blocks through the existing 64-bit host write port of the CP (`cmd_we`, `cmd_addr`, `cmd_wdata`). No new pin is needed.

1. **Configuration (CFG) window.** Writes to addresses with the window bit set place descriptor word pairs (word 2a in bits 31:0, word 2a + 1 in bits 63:32) into the CP's 64-word staging buffer. One further address is `CFG_COMMIT`.
2. **Commit.** At `CFG_COMMIT` the CP runs the hardware check (§5.7). On success it broadcasts the static words on the **configuration bus** `cfg_v, cfg_addr[5:0], cfg_data[31:0], cfg_commit`. The bus is registered at every station it crosses and passes through the clock-crossing synchronisers into the 0.9 GHz serial-chain domain.
3. **Latch.** Each block decodes only its own word addresses into shadow registers. On `cfg_commit` it copies the shadow registers into its active registers.
4. **Settle.** The CP waits `CFG_SETTLE` cycles (at least the deepest bus latency plus 16; 64 by default), then sets `CFG_STATUS.loaded`. Doorbells are refused (`db_rdy` = 0) while a commit settles.

Because active registers change only while every unit is idle, they are **quasi-static**: synthesis treats them as constants for timing (`set_false_path -from` the `*cfg_act*` registers, with the settle interval as the hold-off), and no static register sits on a 1.2 GHz path as a timed launch point. A block whose active registers are held at reset must be equivalent to its DS predecessor (conformance test CF-1, §8.4).

### 5.6 Load sequence

Once per model load:

1. The host writes the model image into HBM through `hfd_loader`: weights, tables, scales, the embedding and the program records (§6.10).
2. The host writes the 32 descriptor word pairs into the CFG window, then writes `CFG_COMMIT`.
3. The CP checks the descriptor, broadcasts, settles and sets `loaded`. On an error it sets `CFG_STATUS.err`, broadcasts nothing and keeps the previous active values.
4. The host reads `CFG_STATUS`. On `loaded` it rings the first doorbell.

Reloading the same model is idempotent. Switching models repeats steps 1–4 with the die idle, which takes seconds and is off the token path.

### 5.7 Validation and errors

Software computes every value in the descriptor; the hardware never derives one. It only latches the words and runs the checks below, which are implemented once, in `tools/hbm_generic_iface.py` `d_hw_check()`. The CP's register-transfer-level (RTL) design must match them case for case (conformance test CF-0).

| Code | Name | Condition | Effect |
|---:|---|---|---|
| 0 | OK | — | Values become active after the settle interval |
| 1 | E_MAGIC | word 0 ≠ `0x31494748` | Refused; previous values kept |
| 2 | E_VERSION | major.minor ≠ 1.0, or length ≠ 64 | Refused |
| 3 | E_CRC | CRC-32 of words 0–62 ≠ word 63 | Refused |
| 4 | E_BUSY | Commit while a job runs or any unit queue is non-empty | Refused |
| 5 | E_RANGE | A static field outside its legal set (including group sizes 16, 32, 64) | Refused |
| 6 | E_RESERVED | A reserved bit set in words 1–62 (including `cp_vocab` = 2¹⁸, which overflows its 18 bits) | Refused |

Before any load, the reset (DS) values apply and doorbells are accepted. After an error, the last good values stay active.

### 5.8 The two descriptors

| Field | DS-V4.1-Flash (= reset) | Qwen3-8B (TP4) |
|---|---:|---:|
| `cp_vocab` | 129,280 | 151,936 |
| `cp_ctx_max` | 1,048,576 | 40,960 |
| `coll_group_size` | 96 | 4 |
| CRC-32 (word 63) | `0xcb3ffafa` | `0x9ed3a0c3` |

---

## 6. Encoding reference

This chapter is the bit-level reference. `spec.json` is authoritative; these tables reproduce it.

### 6.1 Record layout

*Units and terms in this table:* Stream unit (SU) · Unit operation header (UOP) · Memory descriptor (MDESC) · Stream-unit template (SUT).

| Part | Size | Present when |
|---|---|---|
| Header (UOP) | 128 bits (16 B) | always |
| SU template (SUT) | 256 bits (32 B) | header bit `tmpl` = 1 |
| Memory descriptors (MDESC) | 256 bits (32 B) each | one per set bit of `opnd`, in A, B, C, D, O, R, I order |

### 6.2 Unit operation header (UOP, 128 bits)

*Units and terms in this table:* Stream unit (SU) · Dynamic values (DYN).

| Bits | Field | Meaning |
|---|---|---|
| 127:124 | `unit` | Unit code (§2.3) |
| 123:118 | `op` | Operation code: the operation's index in its unit's list (§6.7) |
| 117:102 | `wait` | Drain mask; bit u = unit code u |
| 101:100 | `pred` | Predicate (§6.3) |
| 99:93 | `opnd` | Operand presence: bit 0 = A, then B, C, D, O, R, I |
| 92 | `tmpl` | An SU template follows |
| 91:89 | `slot` | Position slot (verify column) whose DYN bank this operation uses |
| 88:64 | `param` | Operation-specific parameter (§6.7) |
| 63:32 | `imm_a` | FP32 or integer immediate |
| 31:0 | `imm_b` | FP32 or integer immediate |

### 6.3 Predicates

| Code | Name | The record runs when |
|---:|---|---|
| 0 | ALWAYS | always |
| 1 | POS0 | pos = 0 |
| 2 | NOT_POS0 | pos ≠ 0 |
| 3 | LAST_ITER | on the last iteration of the enclosing loop |

### 6.4 Memory descriptor (MDESC, 256 bits)

*Units and terms in this table:* Vector memory (VM) · Dynamic values (DYN).

| Bits | Field | Width | Meaning |
|---|---|---:|---|
| 1:0 | `space` | 2 | 0 HBM, 1 VM, 2 STREAM, 3 NONE |
| 4:2 | `fmt` | 3 | Element format (§6.5) |
| 5 | `ibcast` | 1 | Inner stride 0: every element of a row reads the same value |
| 6 | `indexed` | 1 | The DYN term is replaced by U32(VM[I + L]) (§3.3) |
| 47:8 | `base` | 40 | HBM byte address (32 B aligned), or VM FP32-word address |
| 67:48 | `n` | 20 | Inner count |
| 87:68 | `m` | 20 | Outer count (rows) |
| 119:88 | `stride` | 32 | Outer (row) stride |
| 135:120 | `istride` | 16 | Inner element stride (0 means 1) |
| 167:136 | `lstride` | 32 | Stride per iteration of the level-0 loop (L) |
| 173:168 | `dyn_sel` | 6 | DYN code added to the base (§6.8) |
| 200:174 | `dyn_mul` | 27 | Multiplier of the DYN value or indexed id |
| 206:201 | `n_sel` | 6 | 0: static `n`; 1–62: `n` = DYN[`n_sel`]; 63: `n` from row 1 of the I table |
| 238:207 | `l1stride` | 32 | Stride per iteration of the level-1 loop (L1) |

Bit 7 and bits 255:239 are reserved.

**Effective base:** base + L·`lstride` + L1·`l1stride` + X·`dyn_mul`, where X = DYN[`dyn_sel`], or U32(VM[I + L]) when `indexed` = 1.

### 6.5 Element formats

| `fmt` | Format |
|---:|---|
| 0 | FP32 |
| 1 | BF16 |
| 2 | FP8E4M3 |
| 3 | FP4E2M1 |
| 4 | INT8 |
| 5 | U32 |
| 6 | UE8M0 |

### 6.6 Operand roles by unit

| Unit | Operand use |
|---|---|
| Stream unit (SU) | The template's sources map to A, B, C, D; the element result to O; the reduction result to R; a gather index table to I. |
| Matrix engine (SM) | A = activation (VM or STREAM); B = weights (HBM, possibly indexed); O = result (VM or STREAM); I = id table when B is indexed. |
| Fused paths (FUSED) | A = input; B = gain (norms) or sink row (softmax); O = output, whose `fmt` is the output format. QDQ: A = values, O = the quantised-dequantised values. |
| Special-function unit (SFU) | A = gate, B = up, C = route weight, O = output. |
| Attention tiles (ATT) | A = queries or probabilities (VM); B = K or V rows (HBM, `n_sel` = POS1 or POS_SLOT1), optionally a ring; C (optional) = a second row source whose rows follow B's; O = scores or PV. |
| DMA engine (DMA) | A = source, O = destination; I = id table for an indexed source. |
| Indexer / top-k (IDX) | TOPK: A = scores (m rows of n); O = selected ids (U32); R = selected values (optional). EHASH: B = hash constants; O = row ids (U32). |
| Collective engine (COLL) | A = local contribution (ROW_GATHER: this die's row store), O = result; I = the selected row ids (ROW_GATHER). |
| Argmax unit (ARGMAX) | A = logits (VM or STREAM), O = {value, id}. |
| Control (CTL) | `CTL.END`: A = the U32 token. |

### 6.7 Unit operations

Operation codes are the index of each operation in its unit's list in `spec.json` → `uop.ops`, shown here in order.

| Unit | Operations (code order) | `param` and immediates | Semantics (bit-exact reference) |
|---|---|---|---|
| Control (CTL) | NOP, LOOP, ENDLOOP, END, FENCE, TOKX, AMAX, ACCEPT | LOOP: `[15:0]` count, `[16]` level (0 → L, 1 → L1) | LOOP/ENDLOOP as §3.4. END: completion token = A[0], range-checked against `cp_vocab`. FENCE: wait for all units and all posted HBM writes. TOKX (**proposed**, §7.4, SPEC_GAP Q-MTP-1): A = U32 [1 + ncol], A[0] = k (1 ≤ k ≤ ncol), A[1..k] = the committed tokens; the CP emits k completion beats {token A[i], pos + i − 1, status 0} before `END`. AMAX, ACCEPT: reserved (DFlash needs neither, §7.4). |
| Matrix engine (SM) | MATVEC | `[1:0]` format (0 BF16, 1 FP8 block-dot, 2 FP4 block-dot, 3 INT8); `[4:2]` positions − 1 (one weight read shared by up to 8 slots) | smh arithmetic (tc16 ring, column tree, stack pairing). With P > 1 slots, A and O carry one row per slot (m = P) and each slot's result is the single-slot arithmetic, bit for bit. Rows are split over the die's 32 SMs by the SM layout rule. With an indexed B, the expert is chosen by id. |
| Stream unit (SU) | VOP | — (the template carries the configuration) | `Machine.su1` (R-ARITH chunk8) |
| Special-function unit (SFU) | GLU | `imm_a` = clamp limit (FLT_MAX disables) | The fused SwiGLU chain; output format = O `fmt` |
| Fused paths (FUSED) | HC_PRE_NORM, ROW_NORM, HC_POST, SOFTMAX, QDQ_FP8, QDQ_FP4_E8M0, QDQ_FP4_E4M3 | ROW_NORM: `[5:0]` d_units (with seg 128 and an A of m > 1 rows, the width of one row), `[13:6]` seg; `imm_a` = epsilon. SOFTMAX: `[0]` multipass; `imm_a` = scale | Norms: the norm engine. SOFTMAX: A = scores, B = sink row (−2¹⁰⁰ for none), O = probabilities. The global maximum is merged across all tile pairs before the exponential. Multipass (rows > 640): pass 1 the global maximum; pass 2 exponentials and their sum over fixed 640-row chunks in chunk order, carrying the streaming csum8 binary-counter state so that the sum equals the golden's csum8 tree exactly; pass 3 the normalisation. QDQ: quantise each 32-element block and dequantise it again, exactly as the DS activation quantiser does: QDQ_FP8 to FP8E4M3 with a UE8M0 (power-of-two) block scale; QDQ_FP4_E8M0 to FP4E2M1 with a UE8M0 block scale; QDQ_FP4_E4M3 to FP4E2M1 with an FP8E4M3 scale per block of `param[7:0]` elements (DS 16). The SU cannot form the exact power-of-two scale (⌈log2⌉ of the block maximum), so these are engine operations. |
| Attention tiles (ATT) | QK, PV | `[3:0]` head lanes used (0 encodes 16); `[7:4]` 64-element slices per head − 1; `[8]` ring | Tile chunk8 plus pairwise per 64-element slice, then the slices in slice order. Rows are B's n rows, then C's rows when C is present (scores and PV run over the concatenation, B first). With `ring` = 1, B is a ring of `B.m` slots (a power of two): the first row read is slot (POS1 − n) mod `B.m` and reading wraps at `B.m`, so the rows arrive oldest first. |
| Collective engine (COLL) | ALL_REDUCE_SUM, ALL_GATHER, TOPK_MERGE, ARGMAX_MERGE, GROUP_REDUCE_MCAST, ROW_GATHER | GROUP_REDUCE_MCAST: `[7:0]` sub-group size s. ROW_GATHER: `[7:0]` owner block B; `imm_a` = row count when I has no count row; `imm_b` = destination ranks | Fixed-order reduction in rank order. ARGMAX_MERGE: lowest global id wins ties. ALL_GATHER: rank r contributes elements ⌊r·n/G⌋ to ⌊(r+1)·n/G⌋ − 1 of A (n = A.n, G = group size) and every rank receives all n. GROUP_REDUCE_MCAST: each aligned sub-group of s ranks (s = 2, 4 or 8) reduces A in the rank-order pairwise tree, and each sub-group's result is multicast to every rank of the group; O holds the sub-groups' results in sub-group order, in format O `fmt`. ROW_GATHER: row i of the selection is owned by rank (i div B) mod G, which stores it at local row (i div (B·G))·B + i mod B of A; every destination rank 0 … `imm_b` − 1 receives the selected rows in list order in O. Group size 96: reductions run as 12 aligned sub-groups of 8 ranks in the rank-order pairwise tree, which is `GROUP_REDUCE_MCAST` with s = 8 (the shipped DS order); `ALL_REDUCE_SUM` with G = 96 is rejected with E_RANGE, because no target model sums 96 contributors and a 96-input tree would need new reduction hardware. |
| Argmax unit (ARGMAX) | LOCAL | `imm_a` = id offset multiplier | numpy argmax: lowest index on ties; NaN flag reported; global id = local id + RANK · `imm_a` |
| DMA engine (DMA) | LOAD, STORE, FENCE, KVWB_DS | — | LOAD/STORE: HBM ↔ VM row moves, including the linear KV append, recurrent state and the indexed row stream (§3.3). FENCE: makes the DMA unit's writes visible. KVWB_DS: the DS window-ring KV write-back. |
| Indexer / top-k (IDX) | INDEX_Q, INDEX_SCORES, TOPK, SELECT, EHASH | TOPK: `[11:0]` k (1 … 2,048); `[12]` order (0 = descending score, 1 = ascending id; order 1 is legal for k ≤ 8 only, otherwise E_RANGE). EHASH: `[2:0]` Engram layer index. INDEX_Q, INDEX_SCORES, SELECT: `param[5:0]` source (compressed-KV) layer, `imm_a` candidate count, `imm_b` layer | TOPK: for each of the m rows of A (n scores each), O = the k ids (U32) sorted by descending score, ties to the lowest index (with `order` = 1, the same selected set in ascending id order: the DS router top-6); R (optional) = the k values; NaN fails closed. EHASH: the Engram row ids of the slot's token for one Engram layer, one per head and n-gram order, written as a U32 I table for indexed `DMA.LOAD`s. The engine keeps the n-gram token history: the first EHASH of a token pushes the slot's token, and `CTL.ACCEPT` restores the history to the last accepted slot. B holds the layer's hash constants. INDEX_Q, INDEX_SCORES and SELECT are the DS indexer engines: they keep their working buffers inside the indexer engine, so their A, B and C descriptors may be NONE; SELECT (the DS index top-512) writes O = the selected ids (U32, ascending id order) and optionally R = their values, and that I table feeds `COLL.TOPK_MERGE`, `COLL.ROW_GATHER` and indexed `DMA.LOAD`s. These are engine-internal DS operations; a generic model uses `IDX.TOPK`. |
| Hyper-connections (HC) | HC_MIX | — | The DS hyper-connection mix |
| SIMT engine (SIMT) | RUN | `[13:0]` entry PC; `imm_a` = SM mask | Optional unit, absent on r25 (§2.3) |

### 6.8 Dynamic values (DYN)

The CP computes the DYN values at the doorbell, one bank per slot. Codes are 6 bits.

| Code | Name | Value |
|---:|---|---|
| 0 | ZERO | 0 |
| 1 | POS | the token's position |
| 2 | POS1 | pos + 1, the number of valid KV rows |
| 3 | TOKEN | the doorbell token |
| 4 | L | the level-0 loop counter |
| 5 | RANK | the die's rank in its group |
| 6 | SLOT | the slot (verify column) |
| 7 | POS_SLOT | pos + slot |
| 8 | L1 | the level-1 loop counter |
| 9–14 | WIN_N0, WIN_START0, WIN_N1, WIN_START1, CHUNK_START, CHUNK_N | Reserved for windowed and chunked attention (§10.2) |
| 15 | POS_SLOT1 | pos + slot + 1, the valid KV rows of a verify slot |
| 16–62 | DS selectors | The DS window and compressed-row counts of `hdc_isa_v41.FULL_DYN`, in their order |
| 63 | N_FROM_VM | `n_sel` only: n from row 1 of the I table |

### 6.9 Stream-unit template (SUT, 256 bits)

The SU template carries the pipeline fields of the SU operation set (`tools/hdc_isa_v41.py`), packed from bit 0 in this order; 142 bits are used and bits 255:142 are reserved. Its semantics are `tools/hdc_program_v41.py` `Machine.su1`. `c_pair` always pairs element i with i XOR 1.

| Bits | Fields |
|---|---|
| 11:0 | `a_src` 1:0, `a_ind` 3:2, `b_src` 5:4, `b_half` 6, `c_src` 8:7, `c_pair` 9, `d_src` 11:10 |
| 15:12 | `a_rnd` 12, `a_relu` 13, `a_min` 14, `c_clip` 15 |
| 35:16 | `m1` 18:16, `m2` 20:19, `qm` 23:21, `ad` 26:24, `sfu` 29:27, `e1` 32:30, `e2` 34:33, `rnd` 35 |
| 45:36 | `dst` 37:36, `red` 39:38, `red_sq` 40, `red_whole` 41, `red_rnd` 42, `su_vec` 44:43, `red_tree` 45 |
| 141:46 | `imm1` 77:46, `imm2` 109:78, `imm3` 141:110 |

### 6.10 Memory map (per die)

**HBM** is one die-local, 40-bit byte address space with 32-byte sectors. The svc address map (sector → stack and PC) is fixed. A contiguous KV or index-key sweep must spread over all 32 PCs. DS compressed KV rows keep the shipped 9-channel layout: each 288-byte row is 9 consecutive sectors on 9 consecutive PCs (sector s on PC s mod 32), and the existing gather readers fetch the selected rows in that layout, so an indexed selection still spreads over all PCs. The indexed row stream of §3.3 and conformance row CF-IDXD apply to contiguous row layouts only (whole rows in consecutive sectors); the DS 9-channel rows are read by the DS gather readers and checked by their own vectors.

**Regions** are placed by the compiler and recorded in the image manifest, not in hardware:

*Units and terms in this table:* Matrix engine (SM) · DMA engine (DMA).

| Region | Content |
|---|---|
| IMAGE | Program records; `image_base` and `image_pages` in the descriptor |
| TABLES | RoPE cos/sin rows per position (Qwen: one set, θ = 10⁶, 128 dims; DS: plain, YaRN and compressed sets), norm gains, sinks, gate constants |
| SCALES | INT8 per-row BF16 scales (Qwen) or UE8M0 block scales (DS) |
| WEIGHTS | Per-SM layout by the SM layout rule; one block per layer, `lstride` apart |
| EMBED | One row per token, replicated per die |
| HEAD | This die's vocabulary shard |
| KV | Qwen: `[layer][kv head][K\|V][pos][128]` FP8, 2 KV heads per die at TP4. DS: the window ring of `DMA.KVWB_DS`. |
| STATE | Linear-attention layers: per layer and local head, the FP32 state stored transposed (`[dv][dk]`), and the FP32 convolution ring (`[conv_k − 1][channels]`). Base = STATE + layer · layer bytes. |
| SCRATCH | Spills and collective staging |

**VM** is FP32-word addressed (262,144 words per die) and allocated by the compiler. **Alignment:** HBM bases are 32-byte aligned; KV rows are whole sectors.

### 6.11 Doorbell and completion

| Record | Fields (width in bits) |
|---|---|
| Doorbell | `token` 18, `pos` 20, `job` 32, `gen` 4, `entry` 2, `ncol` 4 |
| Completion | `token` 18, `pos` 20, `job`, `gen`, `status` 4, `cycles` |

Completion status: 0 OK, 1 unit fault, 2 no result, 3 bad command or range.

### 6.12 Model manifest schema

The manifest (`schema` = `opentallas.hgi_model_manifest.v1`) has three parts:

- **Identity:** model name, configuration path and the configuration's sha256.
- **`globals`:** hidden width, vocabulary, RoPE θ and scaling, the softmax-scale literal, weight and KV formats, TP size, head rows per die.
- **`layers`:** one row per layer with `mixer` (kind `gqa`, `dsa_mla` or `gated_deltanet`; heads; head dimension; window; RoPE dimensions, offset, pairing as stored in the weights, table set; DS compression ratio and KV/index source flags), `engram`, `hc`, `ffn` (dense width, or MoE experts, shared experts and top-k) and `norm` (kind, epsilon, QK-norm).

---

## 7. Mapping the target models

### 7.1 DeepSeek-V4.1-Flash: native unit operations

DS runs on r25 as a record stream of native unit operations only, one image per die (96 images of identical structure, §2.6). The simulator runs a full DS token at 1M context this way on 96 simulated dies, bit-exact against the released-checkpoint golden: all 40 layers and the head, 4,526 records per die per token.

*Units and terms in this table:* Control (CTL) · Matrix engine (SM) · Stream unit (SU) · Special-function unit (SFU) · Fused paths (FUSED) · Attention tiles (ATT) · Collective engine (COLL) · Argmax unit (ARGMAX) · DMA engine (DMA) · Indexer / top-k (IDX) · Hyper-connections (HC).

| DS work | Records |
|---|---|
| Matrix-vector products | `SM.MATVEC` (FP8 or FP4 block-dot, BF16); each die's rows by its own even-split constants |
| Activation, window-row, index-key and compressed-row quantisation | `FUSED.QDQ_FP8`, `FUSED.QDQ_FP4_E8M0`, `FUSED.QDQ_FP4_E4M3` |
| Buffer all-gathers | `COLL.ALL_GATHER` (even-split segments) |
| Grouped output projection | One `SM.MATVEC` per o-group as a K-split over its 8 head dies, then `COLL.GROUP_REDUCE_MCAST` (s = 8, BF16 out), which replaces the o all-gather |
| hc_pre_norm, q_norm_kv_row, hc_post | `FUSED.*` |
| SwiGLU | `SFU.GLU` (FP8 out, clamp 10.0, route weights as C) |
| RoPE, attend, router activation, route, MoE sum | SU templates |
| Attention tiles | `ATT.QK`, `ATT.PV` over the window ring (B, `ring` = 1) followed by the selected compressed rows (C); SU templates for the max, exp-sum, sink term and normalisation |
| Indexer query, scores and select | `IDX.INDEX_Q`, `IDX.INDEX_SCORES`, `IDX.SELECT` (the index top-512, ids in ascending id order) |
| Router top-6 | `IDX.TOPK` k = 6, `order` = 1 (ascending id order, the golden's expert-slot order) |
| Selected compressed KV rows | `COLL.TOPK_MERGE` of the dies' local selections, then `COLL.ROW_GATHER` from the owner dies (compressed rows and index keys are sharded by position in blocks of 8: block j lives on rank j mod 96) into each head die's HBM; the indexed stream `DMA.LOAD` (§3.3) serves rows held locally |
| Engram rows | `IDX.EHASH` per Engram layer, then indexed `DMA.LOAD`s of the codes and scales and an SU decode |
| Window and compressed rows, KV write-back | `DMA.LOAD`, `DMA.KVWB_DS` |
| Expert fetch by id | `SM.MATVEC` with an indexed B descriptor over the `IDX.TOPK` ids, in a `CTL.LOOP` over the 6 experts |
| HC mixes | `HC.HC_MIX` |
| Gathers and merges | `COLL.*` |
| Head and token | `ARGMAX.LOCAL`, `COLL.ARGMAX_MERGE`, `CTL.END` reading A |

The acceptance test is identical tokens and per-unit outputs against the existing DS evidence (`hdc_golden_v41`, chunk8).

**What the DS lowering needs beyond the generic set.** Most items map onto DS engines the die already carries:

*Units and terms in this table:* Fused paths (FUSED) · Attention tiles (ATT) · Collective engine (COLL) · DMA engine (DMA) · Indexer / top-k (IDX).

| Item | Interface | Hardware or compiler |
|---|---|---|
| Block quantise-dequantise | `FUSED.QDQ_*` | Existing DS activation quantiser behind the FUSED dispatcher; dispatcher decode only |
| Uneven all-gather segments | The ALL_GATHER segment rule (§6.7) | None: it states the DS collective's split rule |
| o-group reduce with multicast | `COLL.GROUP_REDUCE_MCAST` | Existing DS o-group reduce on the collective (tree tap at log2 s); dispatcher decode |
| Rank-dependent rows and skipped records | Per-die images of identical structure (§2.6) | Compiler only |
| Window ring plus selected rows in one attention | ATT C operand and `ring` flag | **Small hardware:** the ATT row-fetch front end takes a second row list and wraps a power-of-two ring counter |
| Engram hash ids | `IDX.EHASH` | Existing DS Engram hash engine behind IDX. Until it is wired, the host writes the ids into an HBM table before the doorbell and a `DMA.LOAD` stages them; the rest of the program is identical |
| Selected compressed rows from owner dies | `COLL.ROW_GATHER` | The DS row-gather collective; dispatcher decode of the owner rule |

### 7.2 Qwen3-8B: the 28 families

A *family* is a class of graph operations that share one implementation. Qwen3-8B's 871 graph operations per token fall into 28 families. Each family is bound, per model, either to a fused fast path or to an exact fallback on the stream unit. The golden follows the arithmetic order of the bound path, so changing a binding changes the golden (§8.2). The counts below are operations per token; §3.6 shows the records.

*Units and terms in this table:* Control (CTL) · Matrix engine (SM) · Stream unit (SU) · Special-function unit (SFU) · Fused paths (FUSED) · Attention tiles (ATT) · Collective engine (COLL) · Argmax unit (ARGMAX) · DMA engine (DMA).

| Family (operations per token) | Records | Path |
|---|---|---|
| qkv, o, gu, down (144), head (1) | `SM.MATVEC` format 3 (INT8) | Fast path (format 0, a BF16-widened image, for bring-up; bit-identical) |
| row_scale_qkv, row_scale_gu, head_scale | `DMA.LOAD` of the scales + `SU.VOP` (M1 = A·B, the golden's rounding point) | SU |
| row_scale_o, row_scale_down + residual | `DMA.LOAD` + one `SU.VOP` (M1 = A·B, AD = +C) | SU |
| prenorm (73) | `FUSED.ROW_NORM` seg 0, BF16 out | Fast path |
| QK-norm (36) | `FUSED.ROW_NORM` seg 128, FP32 out | Fast path |
| RoPE (36) | `SU.VOP` with `c_pair` (weights permuted offline), cos in B and sin in D, one table row per token | SU |
| roundQ (36) | `SU.VOP` with `rnd` | SU |
| kv_append, kv_fence (72) | `DMA.STORE`, `DMA.FENCE` | DMA |
| attention_qk, attention_pv (72) | `ATT.QK`, `ATT.PV`, 4 lanes per KV head | Tiles |
| softmax (36) | Three `SU.VOP` records (max, exp + sum, BF16 rounding); `FUSED.SOFTMAX` once CF-SFX passes | SU (fast path pending) |
| pv_normalize (36) | `SU.VOP` (M1 = A / B, B broadcast) | SU |
| SwiGLU (36) | `SFU.GLU` (BF16 out, no clamp, route weight 1.0) | Fast path |
| all_reduce_o, all_reduce_down (72) | `COLL.ALL_REDUCE_SUM`, group of 4 | Collective |
| embedding (1) | Two `DMA.LOAD` (codes and scale at TOKEN · 4,128) + `SU.VOP` | DMA + SU |
| argmax_local, argmax_gather, argmax_merge (3) | `ARGMAX.LOCAL` (`imm_a` = 37,984) + `COLL.ARGMAX_MERGE` | Fast path |
| (end of token) | `CTL.END` | — |

**RoPE in the weights.** Qwen's checkpoint pairs element i with i + 64 (split-half). The loader permutes the q and k output rows of W_q and W_k, and the QK-norm gains, so that each pair becomes adjacent. The q·k dot product is unchanged up to summation order, and the `qwen_r25` golden is defined in the permuted order. The RoPE record then uses the same adjacent-pair hardware as DS.

### 7.3 Linear attention

Gated DeltaNet layers (Qwen3-Next style) run as programs on SM, SU, FUSED, DMA and COLL, with no new engine. §3.7 shows a layer. The manifest's mixer kind `gated_deltanet` carries the key and value heads, head dimensions, convolution kernel, gate and state formats, and the layer order. The simulator's pathfinding estimate is about 15,000 cycles per layer per die with BF16 projections; the recurrent core is cheaper than full attention beyond about 14K positions.

### 7.4 Speculative decoding: DFlash on Qwen3-8B

Qwen3-8B's drafter is DFlash (`z-lab/Qwen3-8B-DFlash-b16`, used unchanged: BF16 weights, block 16, mask token 151,669). It has five Qwen3-shaped layers and an `fc` projection. It reads the target's hidden states after layers 1, 9, 17, 25 and 33, and it shares the target's embedding and LM head. Its attention is **bidirectional within the block**: every block position sees the drafter's context rows and all B block rows. The verify pass is causal per position. The whole step is one doorbell at `entry_verify`, with `token` = the last committed token (the anchor) and `pos` = its position. `tools/hgi_sim/dflash.py` compiles it. `tools/hgi_sim/dflash_proof.py` runs it bit-exact against its golden, and its committed tokens equal plain greedy decoding. `tools/hgi_sim/dflash_timing.py` times it.

**Programming rules.** These rules use only the operations above. No slot DYN bank and no new DYN code is needed.

| DFlash need | How the program expresses it |
|---|---|
| Per-slot position (RoPE row, KV append at pos + s) | `dyn_sel` = POS plus a static offset of s rows in the descriptor base |
| Per-slot causal count pos + s + 1 (s up to 15, beyond the 3-bit `slot` field) | One `DMA.LOAD` per step from an HBM table T[q] = q (U32) at POS + 1 + s, with `ibcast`, gives one I table per slot. The records use `n_sel` = 63 (N_FROM_VM) with that I table. |
| Verify attention for a group of slots (16 lanes = 4 query heads × 4 slots) | ATT B = rows [0, pos) (`n_sel` = POS); C = the block rows [pos, pos + s_last + 1) of the same plane (`dyn_sel` = POS, static n). Each slot's SU softmax reads its own count. An `SU.VOP` (×0) writes +0 over the slot's masked tail, so the group's PV equals the slot's own causal PV bit for bit: zeros only extend the chunk8 tree. |
| Drafter attention (context + whole block, bidirectional) | ATT B = the drafter's context KV rows [0, pos) (`n_sel` = POS); C = the block's own K/V rows in an HBM scratch (static n = B). Every lane uses count pos + B, with no mask. |
| Target features of layers 1, 9, 17, 25, 33 | The verify loop is split at those layers. After each split, a `DMA.STORE` writes all slots' residuals (BF16) to region CTXF at POS. |
| `fc` projection, drafter context K/V | Each step recomputes the drafter K/V rows for the B most recent committed positions [pos − B, pos) from CTXF, which also covers the rows the previous step accepted. The chain is `fc` (one SM record per captured layer, K = 4,096, the die's 1/TP output rows), SU pairwise adds, `COLL.ALL_GATHER`, `hidden_norm`, then per layer the K/V projection, `k_norm`, RoPE and a `DMA.STORE` (BF16). Rewriting committed rows writes identical values. |
| Mask-token embedding | A static descriptor base: EMBED + 151,669 × row bytes, m = B − 1 rows with stride 0 |
| Draft ids into the verify pass | ARGMAX.LOCAL plus COLL.ARGMAX_MERGE per slot into a U32 VM table D. The verify embeddings are indexed `DMA.LOAD`s on D. |
| LM head over several slots | At most 4 slots per head pass, because VM holds 4 × 37,984 FP32 logits. The row scales are read in place from HBM by the SU. |
| Accept (18-bit tokens) | D[1..] and the posterior ids are stored as U32 and reloaded as INT8 bytes. An SU computes the sum of squared byte differences per id, then min(·, 1). A leading 0 and a trailing 1 are added. `ARGMAX.LOCAL` (`imm_a` = 0, lowest index on ties) then gives k = accepted + 1. The committed tokens are posterior[0..k − 1]. |
| KV commit / rollback | None needed. Rejected rows at ≥ pos + k are never read, because every count is derived from POS, and the next step overwrites them. The host rings the next step with {posterior[k − 1], pos + k}. |
| Returning k tokens to the host | `CTL.TOKX` (proposed, Q-MTP-1, the one hardware item). |

**Block size.** Block 16 is 2 weight passes of 8 slots for every target and drafter matrix, plus 4 LM-head passes per pass type. Block 8 is 1 weight pass and 2 head passes.

**Open items** (`tools/hgi_sim/records.py` SPEC_GAPS):

- **G18 (verify, hbm-forks).** The SM element (`ot_hbm_accel_smh`: ports op_rows/op_c/op_g/op_gs/op_fmt/op_xb) has no slot count. Whether one issued line serves P x-fragments in the same issue beat is not benched. If it does not, every slot replays the line, and verify cost grows with P (see the timing record).
- **G19.** The ATT lane field encodes 16 as 0.
- **Q-MTP-1 (cmdproc).** `CTL.TOKX`.

---

## 8. Verification

### 8.1 The simulator contract

The simulator (`tools/hgi_sim/`) is the arbiter between the compilers and the hardware. It must model the following.

**Inputs and outputs.** The inputs are the artifacts the die consumes: the descriptor, the program image, the HBM image and the doorbells. The outputs are completions; a per-record trace (issue cycle, retire cycle, unit, and a hash of each operand and result buffer); an HBM and VM write log; and fault codes.

**Functional model (bit-exact).** Each unit operation is computed by one shared **arithmetic library** whose order functions are each pinned to an RTL bench:

- SM: per-format leaf, tc16 ring, column tree, stack pairing;
- ATT: chunk8 plus pairwise per 64-element slice;
- SU: `Machine.su1` / R-ARITH csum;
- norm, softmax (including the multipass chunk order and csum8 carry) and SwiGLU, under every per-operation setting;
- collective: rank-order reduction;
- top-k and argmax: lowest index on ties.

The simulator and the goldens both call this library. Nothing else is shared, so a compiler error (a wrong address, stride, wait mask or binding) shows up as a mismatch.

**Control model:** the CP sequencer (prefetch, predicate, `wait`, both loop levels, DYN banks, indexed reads); unit queues and STREAM credits; collective matching by group sequence; fence visibility; and the configuration path, including every error code of §5.7 and the settle hold-off.

**Timing model (transaction-level):** per unit, issue rate, pipeline depth and per-operation setup cycles from a calibration table (`hgi_sim/calibration.json`) in which every entry carries a record pin and a grade (measured or estimate); HBM per-PC bandwidth, 32-byte sectors and request queue depth; collective endpoint latency plus a per-crossing budget. Cycle results are pathfinding until every entry is measured. The bar is timing within ±2 % of each stage bench; exactness is never a tolerance.

**Faults.** Every fail-closed condition of the RTL (SU domain faults, non-finite values, a descriptor out of range, an indexed id out of range, a record to an absent unit, an `END` token ≥ `cp_vocab`) must produce the same fault and completion status in the simulator.

**Out of scope:** wires, clock crossings beyond fixed latencies, and physical faults.

**Proof obligations:** (a) the functional mode equals the golden bit for bit on every token of the test set; (b) every RTL stage bench equals the simulator's per-record buffers for the same records; (c) the simulator's cycles track the stage benches within tolerance, and published numbers use measured entries only.

### 8.2 Goldens

A **golden** is the bit-exact software reference that hardware and simulator must reproduce.

- **DS:** `hdc_golden_v41` (chunk8) and the existing campaigns.
- **Qwen3-8B:** `qwen_r25`, the graph in r25 order on the arithmetic library, with the bindings of §7.2 and the permuted RoPE order. Binding a different path (for example the fused softmax) is a golden change. Owner sign-off rests on one contract quality run in r25 order (about 2.2 GPU-hours) within the pre-committed rule on perplexity (PPL) and the MMLU benchmark.
- **Gated DeltaNet:** the golden in `tools/hgi_sim/gdn.py`, checked against the transformers reference.

### 8.3 The verification ladder

| Level | Vehicle | Pass criterion |
|---|---|---|
| L0 | The arithmetic library against each block's pinned bench vectors | Bit-exact, every per-operation setting covered |
| L1 | Simulator (functional) against the golden | Every token of the test set: Qwen AR at position 8,191, the DS reference positions |
| L2 | RTL stage benches (one stage per layer type plus the head) against the simulator's per-record buffers | Bit-exact, each with a negative mutant |
| L3 | Composition: simulator timing with measured entries | Published only as a measured composition |

### 8.4 Conformance tests

*Units and terms in this table:* DMA engine (DMA) · Hyper-connections (HC) · Command processor (CP) · Vector memory (VM).

| ID | Block | DS (reset) | Qwen and other models |
|---|---|---|---|
| CF-0 | Configuration path | DS descriptor load causes no change; each error code with the active values kept; a doorbell before any load runs DS; commit while busy refused; settle hold-off | Qwen descriptor load and read-back; reserved-bit, group 12, group 16 and vocabulary 2¹⁸ negatives |
| CF-1 | DS equivalence | A block with its active registers at reset and DS per-operation values is equivalent to its DS predecessor: formal equivalence where the block is small, otherwise byte-identical replay of the committed DS vectors **and** identical cycle counts | — |
| CF-SM | `smh_front_c` format 3 | Formats 0–2 identical; latency bypass-matched | Format 3 output equals format 0 on the BF16-widened image; INT8 rows of −128, 127, 0 |
| CF-QDQ | Block quantiser | DS act-quant vectors (FP8 UE8M0, FP4 UE8M0, FP4 E4M3 block 16) | All-zero, maximum and subnormal blocks; mutant: a scale off by one power of two |
| CF-CP | CP | 17-bit DS token set | Ids 131,071, 131,072, 151,935; position 2²⁰ − 1; range refusal at `cp_vocab` and `cp_ctx_max`; a record to an absent unit faults with status 3 |
| CF-ROPE | RoPE | Adjacent 64-tail vectors | Permuted-weight 128-dim RoPE against the golden; mutant: unpermuted weights must fail |
| CF-NORM | Norm engine | D5120, HC and FP8 vectors | D4096 BF16; seg 128 QK-norm (32 + 8 heads); FP32, BF16 and FP8 outputs in one program; mutant: an unpadded tail |
| CF-SFX | Softmax | Sink vectors | 8 heads × 8,192 rows multipass against the golden's chunk order; T = 1, 640, 641, 1,280, 8,192; csum8 carry equality; global maximum across all tile pairs; sink −2¹⁰⁰ equals no sink |
| CF-GLU | SwiGLU | FP8, clamp and route-weight vectors | BF16 out, clamp FLT_MAX, route 1.0 by broadcast, 3,072 per die |
| CF-COLL | Collective | TP-96 vectors; ALL_GATHER with G not dividing n; GROUP_REDUCE_MCAST s = 8, BF16 out; ROW_GATHER k = 7, 512, 2,048 across owner dies, list order, an unwritten row faults | Groups 1, 2, 4, 8 at every rank (all-reduce of 256 words and ARGMAX_MERGE ties); a −0 contributor; pad mutant; group isolation; 16, 32, 64 rejected; `ALL_REDUCE_SUM` at G = 96 rejected (E_RANGE) |
| CF-ARG | Argmax | 17-bit ids | Id 151,935; lowest-index tie; NaN flag; `imm_a` id offset |
| CF-ATT | Attention row sources | Window ring with wrap at every phase (first row = slot (POS1 − n) mod m) followed by k selected rows; mutant: ring read from slot 0 | Single B source, `n_sel` = POS1 |
| CF-EHASH | Engram hash | Ids of every Engram layer against the golden's hashes over a token sequence; history restored by ACCEPT after a rejected draft | — |
| CF-KV | KV paths | `DMA.KVWB_DS` ring, selected-row and ingest vectors | Linear append at pos; fence-before-read negative; mask at len − 1, len, len + 1 |
| CF-EMB | Embedding | BF16 rows | Row 151,935; INT8 plus scale dequantisation |
| CF-SVC | KV striping | DS index-key sweep | Qwen 8K dense sweep at ≥ 90 % of die bandwidth |
| CF-BCAST | Broadcast | — | `ibcast` per-row scalar; mutant reading inner stride 1 |
| CF-IDXD | Indexed descriptors | Contiguous row layouts only: a selected-row stream (k = 7, 513, 2,048 sorted positions over 1M): every row exactly once, in list order; mutant: list order broken in one PC. DS compressed KV rows (9-channel layout, §6.10) are excluded: the existing DS gather readers and their vectors cover them | Expert fetch by id; `n` from VM; stale-table mutant (missing wait) must fail; out-of-range id faults |
| CF-TOPK | Top-k | Router top-6 (`order` = 1, ascending id order); index top-512 through `IDX.SELECT` | k ∈ {1, 2, 6, 8, 512}; m > 1 rows; lowest-index ties; NaN fail-closed; `order` = 1 with k > 8 rejected |
| CF-LOOP2 | Sequencer loops | — | Two-level loop with `l1stride` and L1 |
| CF-GDN | Linear attention | — | State round trip in the transposed layout; convolution-ring wrap; per-head loop; GQA-map mutant |
| CF-PROG | Sequencer | DS program: 96 per-die images of identical structure (a structure-mismatch negative must fail), same tokens and buffers as today | Qwen layer and head records against the simulator, with `wait`, STREAM, LOOP and FENCE negatives |

---

## 9. Extensibility

### 9.1 How generality is achieved

HGI-1 is generic because model variation lives in programs and per-operation operand descriptors, and because the programmable vector unit (SU templates), indexed descriptors and the generic top-k cover what the fused fast paths do not. Each operator of a new model falls into one of three tiers:

*Units and terms in this table:* Matrix engine (SM) · Stream unit (SU) · Special-function unit (SFU) · Fused paths (FUSED) · Attention tiles (ATT) · DMA engine (DMA) · Indexer / top-k (IDX).

| Tier | Meaning |
|---|---|
| **F**, fast | A fused path (norm engine, `SFU.GLU`, `FUSED.SOFTMAX`, an `SM.MATVEC` format, ATT, `IDX.TOPK`) runs it with its per-operation settings. |
| **T**, template | One or more `SU.VOP`, `DMA` or `SM.MATVEC` records with SU templates and data tables. Exact under its own golden; slower. |
| **X** | Not expressible without a hardware or encoding change. |

### 9.2 What other models need

- **Dense transformers** (Llama-3, Mistral, Phi, GPT-2/NeoX) are expressible. Norm widths other than 4,096 and 5,120, LayerNorm, GELU variants, biases and odd RoPE spans run at tier T. The fast paths are worth only 4–7 % of a Qwen token, because the weight stream dominates, so this costs little.
- **Mixture-of-experts models** (Mixtral, Qwen3-MoE, DeepSeek-V3/R1, Kimi-K2, GLM-4.5, GPT-OSS, Llama-4) are expressible:
  - top-k selection is `IDX.TOPK` (tier F);
  - router scoring, bias, normalised top-k weights and routed scaling are SU templates, with per-id weights gathered through the I operand (tier T);
  - group-limited routing (DS-V3/R1) chains `IDX.TOPK` per group row, an SU gather-sum, a second `IDX.TOPK`, an indexed `DMA.LOAD` of the selected groups' scores and a final `IDX.TOPK` (tiers T and F);
  - expert weight fetch by id is `SM.MATVEC` with an indexed B descriptor, looped over k (tier F), and variable expert counts use `n` from VM;
  - expert parallelism is unnecessary at batch-1 decode: experts are tensor-parallel and summed by one all-reduce.
- **Linear-attention hybrids** (Gated DeltaNet) are expressible in software (§3.7). Softplus is an SU template sequence.
- **Not expressible on r25:**
  - data-dependent control flow (branching on a computed value, early exit, dynamic layer skipping);
  - expert-parallel all-to-all with token-dependent destinations;
  - non-greedy sampling on the die (sampling stays on the host, or is greedy);
  - Gemma-3's vocabulary (262,208 exceeds 18 bits) and 10M-token contexts (positions are 20 bits);
  - sliding-window and chunked attention, until the reserved window codes are implemented (§10.2);
  - group sizes 16, 32 and 64 (for example Kimi-K2 at TP16), until the collective engine builds them.

*Table 9-1. Capacity limits that bound generality.*

*Units and terms in this table:* Stream unit (SU) · Special-function unit (SFU) · Attention tiles (ATT) · Vector memory (VM).

| Limit | Value | Effect |
|---|---|---|
| Token width | 18 bits: vocabulary ≤ 262,143 | Gemma-3 not expressible |
| Position width | 20 bits: 1,048,576 positions | 10M-context models capped |
| HBM per die | 144 GB (4 stacks × 36 GB) | Kimi-K2 FP8 needs TP ≥ 8 |
| Collective group | 1, 2, 4, 8, 96 (96 = 12 groups of 8; no 96-way ALL_REDUCE_SUM) | Larger tensor-parallel groups need a collective-engine variant |
| VM | 262,144 FP32 words (1 MiB) | Single-pass softmax for heads × rows up to about 200K words |
| Softmax chunk | 640 rows per pass | Longer rows use multipass (rate only) |
| ATT tile | ≤ 16 head lanes; head_dim ≤ 1,024 in multiples of 64; FP8/BF16 rows | head_dim 96 pads to 128; FP32 operands go through the SU |
| Norm engine | d_units 32, 40, 8 or 2; seg 0 or 128 | Other widths run as templates |
| SFU codes | 8 of 8 used | No tanh, erf, log or softplus code: templates instead |
| Units | 12 defined, codes 12–15 reserved | Up to four new engines without a format change |
| Top-k | k ≤ 2,048 | — |

### 9.3 Lessons from other accelerators

Machines designed for generality (Google's TPU, Groq, Cerebras, SambaNova, Tenstorrent, AWS Trainium, GPUs) keep a few fast fixed engines and put all model variation in programs and per-operation operand descriptors. Tenstorrent is the closest analogue: a sequencer issuing operations to fixed engines, with formats in operand descriptors and data movement as explicit operations. SambaNova's lesson is that configuration should be scoped to the operation or section, not global. Fixed-function designs (one model per chip) are the pattern to avoid. HGI-1 follows the first group: three static fields, everything else per operation.

### 9.4 Adding a model

1. Write the model's manifest rows (the encoder generates them from its `config.json` for supported mixer kinds).
2. Write its compiler lowering onto the existing unit operations, choosing tier F or T for each family.
3. Build its golden on the arithmetic library with the chosen bindings, and check it against the reference implementation.
4. Only if a fused path must express something that data, per-operation fields and templates cannot, propose an interface change under §9.5.

### 9.5 Change process and versioning (normative)

- A new field or operation is added only when the model cannot be expressed through data, per-operation fields or templates. The addition must come with its DS reset behaviour and a conformance row.
- Every change bumps the descriptor's minor version (the CP's version check enforces it), regenerates `spec.json`, the manifests and the descriptors with the encoder, and is merged with `--check` passing.
- Encodings are never reused. A removed field's bits stay reserved.

---

## 10. Open questions

### 10.1 Linear-attention state with speculative decoding

The KV cache tolerates speculative decoding because rejected positions are simply never read again. The STATE region of a linear-attention layer is not position-indexed: an MTP verify pass that runs several positions overwrites the state with drafts that may be rejected. Running GDN layers with MTP therefore needs a per-slot state snapshot, or a recompute from the last accepted state. The interface does not define either yet. The question matters only if linear-attention models will run with MTP.

### 10.2 Window and chunk codes

DYN codes 9–14 (`WIN_N0/1`, `WIN_START0/1`, `CHUNK_START`, `CHUNK_N`) and descriptor words 50–52 (their window and chunk parameters) are reserved, not implemented. They would let sliding-window and chunked attention (Mistral v0.1, Gemma-2/3, GPT-OSS, Llama-4) read a linear KV region from the window start, with a few comparators in the sequencer and no change to the KV write-back. Neither target model needs them, so they are built only when a windowed model is scheduled. DS keeps its own window selectors (codes 16–62).

### 10.3 Other items to pin

- **Qwen MTP.** DFlash runs as one program per step (§7.4). It needs no descriptor word; words 49 and 53–55 stay reserved. Its one hardware item is `CTL.TOKX` (Q-MTP-1).
- **SM layout rule.** The row split over 32 SMs and the per-SM weight layout must be pinned from the DS image builder before the Qwen compiler writes weights.
- **DS embedding row stride.** The checkpoint row is 10,240 bytes (BF16 × 5,120). If the DS image keeps the stripe-padded layout of the measured HBM stream bench, the row stride in the embedding descriptor is 12,288 bytes.

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **AR** | Autoregressive decode: one new token per step. |
| **Argmax unit (ARGMAX)** | Unit 7: the local argmax over this die's logit shard. |
| **Attention tiles (ATT)** | Unit 5: the attention tiles, computing QK scores and PV products over KV rows read from HBM. |
| **BF16** | 16-bit brain floating point (8-bit exponent, 7-bit mantissa). |
| **Block-dot** | A dot product over blocks of low-precision values that share one scale (FP8 or FP4 with UE8M0 block scales in DS). |
| **chunk8** | The golden's summation order for attention dot products: chunks of 8, then pairwise. |
| **Command processor (CP, CMDPROC)** | The command processor (`hfd_cmdproc`): the in-order sequencer that fetches and dispatches records and owns the doorbell and configuration path. |
| **Collective engine (COLL)** | Unit 6: the cross-die collective engine (all-reduce, all-gather, top-k merge, argmax merge). |
| **Completion** | The record the CP returns to the host at `CTL.END`: token, position, job, status and cycle count. |
| **CRC-32** | The IEEE CRC-32 checksum over descriptor words 0–62, stored in word 63. |
| **csum8** | The golden's chunked summation order; its streaming binary-counter state carries a multipass softmax sum exactly. |
| **Control (CTL)** | Unit 0: control operations executed by the CP itself. |
| **DMA engine (DMA)** | Unit 8 (direct memory access): row moves between HBM and VM, the KV append, the DS KV write-back and the HBM fence. |
| **Doorbell** | The host's start command for one token: input token, position, job id, generation, entry point and column count. |
| **DS** | DeepSeek-V4.1-Flash, the reference model whose behaviour is the reset state. |
| **DSpark** | DeepSeek-V4.1's built-in multi-token prediction (draft) scheme. |
| **Dynamic values (DYN)** | Small per-token integers (POS, POS1, TOKEN, L, L1, RANK, SLOT, …) computed by the CP at the doorbell and used in address computation. |
| **Engram** | A DeepSeek-V4.1 operator family (hashed n-gram memory lookup). |
| **Entry point** | A record offset in the program image where a pass starts (AR, verify, draft). |
| **Family** | A class of graph operations that share one implementation, for example "prenorm" or "row_scale_qkv". |
| **Fast path** | A fused hardware datapath for a family (norm engine, SwiGLU chain, softmax unit). |
| **FENCE** | `CTL.FENCE` or `DMA.FENCE`: waits until posted HBM writes are visible. |
| **FP8E4M3, FP4E2M1, UE8M0** | 8-bit float (4-bit exponent, 3-bit mantissa); 4-bit float (2-bit exponent, 1-bit mantissa); 8-bit unsigned power-of-two scale. |
| **Fused paths (FUSED)** | Unit 4: the norm engine, the DS hyper-connection norms and the softmax unit. |
| **GDN** | Gated DeltaNet: a linear-attention layer that keeps a per-head state matrix instead of a KV cache. |
| **Golden** | The bit-exact software reference model (`hdc_golden_v41` for DS, `qwen_r25` for Qwen, the GDN golden in `hgi_sim`). |
| **GQA** | Grouped-query attention: several query heads share one KV head (4 per KV head for Qwen3-8B). |
| **HBM** | High-bandwidth memory attached to the die: 144 GB per die in 4 stacks. |
| **Hyper-connections (HC)** | DeepSeek-V4.1's multi-copy residual mixing; unit 10. |
| **HGI-1** | HBM Generic Interface: this specification. |
| **I table** | A VM table of U32 ids named by a record's I operand: row 0 holds ids, row 1 optional counts. |
| **`ibcast`** | Descriptor bit that sets the inner stride to 0, so each row reads one value. |
| **Indexer / top-k (IDX)** | Unit 9: generic top-k (`IDX.TOPK`) and the DS indexer engines. |
| **Image** | The program records stored in HBM, located by `image_base` and `image_pages`. |
| **Indexed descriptor** | A descriptor whose address term comes from an id in VM instead of a DYN value. |
| **INT8 row scale** | Qwen's weight format: signed 8-bit codes with one BF16 scale per output row. |
| **KV cache** | The stored key and value rows of earlier positions, in HBM. |
| **L, L1** | The counters of the level-0 and level-1 loops. |
| **MD** | The model descriptor: 64 words read by hardware at model load. |
| **Manifest** | The per-layer JSON description of a model that software reads; bound to the MD by sha256. |
| **Memory descriptor (MDESC)** | The 256-bit operand description in a record. |
| **MTP** | Multi-token prediction (speculative decoding with draft and verify passes). |
| **OTG-1** | The SIMT instruction set of the GPU-organised ablation's kernels (`tools/gpu_sys`). |
| **o-group** | DS's group of 8 head dies that share one output-projection reduction. |
| **Owner die** | The die that stores a sharded row: for DS compressed rows and index keys, block j of 8 rows lives on rank j mod 96. |
| **PC** | HBM pseudo-channel; a die's KV sweeps stripe over all 32. |
| **POS, POS1** | The token's position, and position + 1 (the number of valid KV rows). |
| **QDQ** | Quantise-dequantise: round a block of values to a low-precision format with a shared scale and convert back, as the golden does. |
| **Quasi-static** | Changed only while the die is idle, so it can be treated as a constant for timing. |
| **r25** | The current revision of the HBM accelerator die. |
| **Rank** | A die's index within its collective group: `die_id mod group_size`. |
| **R-ARITH** | The golden's reduction-order rule: products are taken in K order and combined by the chunked sum (csum). |
| **Record** | One unit operation in a program: header, optional SU template and memory descriptors. |
| **Reset value** | A static field's value before any descriptor load; equal to DS behaviour. |
| **RoPE** | Rotary position embedding: pairs of query/key elements rotated by position-dependent angles. |
| **Special-function unit (SFU)** | Unit 3: the fused SwiGLU chain. (Inside an SU template, `sfu` is also the stage that applies exp, rsqrt, sigmoid and other special functions.) |
| **SIMT engine (SIMT)** | Unit 11 (single-instruction, multiple-thread): an optional kernel engine, absent on r25. |
| **Slot** | A verify column; each slot has its own DYN bank. |
| **Matrix engine (SM)** | Unit 1: one of the die's 32 weight-streaming matrix-vector engines. Each streams weight rows from HBM against an activation vector. The short name is borrowed from GPU naming, but an SM here is not a GPU streaming multiprocessor: it has no instruction stream, threads or register file. |
| **SPMD** | Single program, multiple data: every die of a group runs the same program on its own shard. |
| **STATE** | The HBM region holding linear-attention state and convolution rings. |
| **STREAM** | A hardware FIFO with credit flow control joining a fixed producer and consumer. |
| **Stream unit (SU)** | Unit 2: the programmable vector pipeline, configured per record by a stream-unit template (SUT). |
| **Stream-unit template (SUT)** | The 256-bit configuration of the SU pipeline in a record. |
| **svc** | The HBM service layer that maps sectors to stacks and pseudo-channels. |
| **τ (tau)** | The measured mean number of tokens accepted per MTP verify step. |
| **tc16 ring** | A stage of the SM's accumulation order in the smh arithmetic. |
| **TP** | Tensor parallelism: splitting each layer's matrices over the dies of a group. |
| **Unit operation header (UOP)** | The 128-bit record header. |
| **Verify pass** | The MTP pass that checks several drafted positions in one sweep. |
| **Vector memory (VM)** | The die's 262,144-word FP32 scratch, allocated by the compiler. |
| **`wait` mask** | Header field naming the units that must drain before a record issues. |
| **YaRN** | A RoPE context-extension scheme; only the host's table generator implements it. |

---

## Appendix A. Design decisions

*Units and terms in this table:* Stream unit (SU) · Fused paths (FUSED) · Attention tiles (ATT) · Indexer / top-k (IDX) · SIMT engine (SIMT) · Command processor (CP) · Vector memory (VM) · Dynamic values (DYN).

| Decision | Why |
|---|---|
| A record-and-sequencer model: the CP fetches records from HBM and dispatches them to per-unit queues | One program format reaches every engine, needs no kernel launches or software synchronisation, and replaces per-family command namespaces and launch coalescing. |
| Only three static fields (vocabulary limit, context limit, group size) | A global mode forbids mixing layer types and hard-codes today's two models. Every other setting is expressible per operation at the same hardware cost. |
| Output formats in the O descriptor | Qwen needs FP32 (QK-norm) and BF16 (prenorm) from the same engine in the same layer. |
| RoPE pairing in the weights | An offline row permutation makes every model's pairs adjacent, so DS's existing pair hardware serves all of them and no RoPE mode fork is needed. Partial spans become descriptor ranges. |
| Seven operand slots (A, B, C, D, O, R, I) | The SU pipeline reads four sources and writes an element result and a reduction result; RoPE, every reduce-and-store template and every gather need them. |
| `ibcast` | Per-row scalars (softmax max and sum, per-head gates, norm factors) without copies. |
| 16-bit wait mask, unit codes 12–15 reserved | A later engine is additive and needs no format change. |
| `FUSED.SOFTMAX` with the sink as data | A sink of −2¹⁰⁰ is proved bit-identical to no sink, so no sink mode bit is needed. The multipass carry is the csum8 state, so the fused unit can equal the golden exactly. |
| `IDX.TOPK` and indexed descriptors are required | r25 has no kernel engine. Without them, MoE routing, expert fetch by id and DS selected-row reads have no route. The top-k engine already exists; the new logic is one VM read per record in the unit dispatchers. |
| SIMT optional, DS lowered to native unit operations | r25's SMs are fixed-function. DS needs no kernel engine when its work is expressed as native records. |
| Per-die program images of identical structure, not rank masks | Uneven splits and rank-specific skips are compile-time facts. Writing them into each die's image costs no hardware, while a rank-mask predicate would add header bits and sequencer logic for the same effect. |
| Block quantise-dequantise, sub-group reduce and row gather as engine operations | DS needs them bit-exact; the SU cannot form an exact power-of-two block scale, and the collective already implements the reduce and gather. Exposing them costs dispatcher decode only. |
| Attention over two row sources with a ring | DS attends over its window ring plus the selected compressed rows in one softmax; a second row list and a ring wrap in the ATT front end are the smallest way to keep that one pass. |
| Engram ids on the die | The DS Engram hash engine already keeps the token history and restores it on MTP accept. Host-written ids would add a host step to every token. |
| Two loop levels and 6-bit DYN codes | Per-head replay for linear attention without unrolling; room for window, chunk and verify-slot codes next to the DS selectors. |
| Per-layer manifest instead of geometry in the descriptor | Software needs per-layer detail; hardware needs none of it. A manifest can describe heterogeneous layers and grows without touching hardware. |
| Collective groups 1, 2, 4, 8 and 96 | Groups up to 8 are free on the existing 8-input reduction tree; 96 is DS, whose reductions are 12 groups of 8 (`GROUP_REDUCE_MCAST` s = 8), so 96 needs no new hardware and a 96-way `ALL_REDUCE_SUM` is rejected. Sizes 16–64 cost about nine times the reduction datapath, so they are defined but rejected until a model needs them. |
| Linear attention in software | GDN runs exactly on the existing engines; a dedicated unit would add hardware for a rate gain only. |
| Top-k order bit for k ≤ 8 only | The DS router top-6 emits ids in ascending id order; a small id sort after the top-k costs a few cycles at k ≤ 8. The DS index top-512 is `IDX.SELECT`, which is ascending by construction. A large-k ascending order would need a second pass over A, so it is rejected until a model needs it. |
| Reset equals DS | Every existing DS closure, vector and bench stays valid without loading a descriptor. |

## Appendix B. Sources

- The hbm-generic plan (`results/arch/hbm_generic_20261009/PLAN.md`) and the Qwen-on-r25 study (`results/arch/qwen_on_r25_20261008/PLAN.md`).
- Codex's Qwen family inventory: 871 graph operations, 28 families.
- The r25 block ports: `hfd_cmdproc`, the `smh` operation port with `op_fmt`, the SU operation set of `tools/hdc_isa_v41.py`, `ot_dshbm_argmax`, `ot_dsrom_su_softmax`, `ot_hbm_rope_table`.
- The interface generality review (`review_queue/iface-review.md`), the simulator's findings (`tools/hgi_sim/records.py`, the hbm-sim log) and the collective and stream-engine designs (`review_queue/hbm-forks.md`).
- Owner decisions in REVIEW_20261009.
- Simulator evidence: `results/arch/hgi_sim_20261009/` (Qwen3-8B layer at position 8,191, the GDN layer, the sink proof, the DS round trip, timing).
