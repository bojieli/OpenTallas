# The HBM Generic Interface (HGI-1)

**Programming and configuration specification for the generic HBM accelerator die, version 0.9**

| | |
|---|---|
| Status | **v0.9, frozen for parallel start** (stream hbm-iface, 2026-10-09). Changes follow the change process of §9.5. |
| Applies to | The r25 HBM accelerator die running Qwen3-8B and DeepSeek-V4.1-Flash |
| Machine-readable form | `results/arch/hbm_generic_iface_20261009/spec.json` (authoritative for every bit position) |
| Reference encoder and validator | `tools/hbm_generic_iface.py` (`--out <dir>` writes the spec and both model descriptors; `--check <dir>` fails on any drift) |
| Proposed changes | Chapter 10, **proposed, pending owner approval**. They are not part of the normative v0.9 text. |

## Abstract

The generic HBM die is one accelerator design that must run two very different language models: Qwen3-8B, a dense transformer, and DeepSeek-V4.1-Flash, a large mixture-of-experts model with several unusual operators. HGI-1 is the contract that makes that possible. It defines what software sees of the die: a small set of fixed engines, three kinds of memory, a stream of self-describing *records* that the die executes for every generated token, and a 256-byte *model descriptor* that sets a handful of static hardware modes when a model is loaded.

Every party builds against this one contract. Hardware engineers fork their blocks to it; the simulator models it; the two compilers emit it; the goldens (the bit-exact reference models) compute the same arithmetic it describes. This document explains the machine, shows how a token is computed on it with a fully worked decoder layer, gives the complete encoding reference, and states how conformance is proved.

---

## 1. Introduction

### 1.1 Purpose and audience

This specification is written for an engineer joining the project who needs to program, simulate, verify or modify the generic HBM die. It assumes familiarity with transformer inference (attention, feed-forward layers, the KV cache, tensor parallelism) but not with this project's history or block names. Every term is defined at first use and collected in the glossary (Chapter 11).

Chapters 2 to 4 are explanatory: they describe the machine, the programming model and the ordering rules. Chapters 5 and 6 are the reference: descriptor and record encodings. Chapters 7 and 8 apply the interface to the two target models and define how it is verified. Chapter 9 covers how the interface extends to other models and how it may change. Chapter 10 collects open items and proposed changes, kept apart from the normative text.

### 1.2 Conventions

- **Normative language.** "Must", "must not" and "only" state requirements. Statements in examples, notes and Chapter 10 are informative.
- **Bits and words.** Bit 0 is the least significant bit. A *word* is 32 bits. Multi-word values are little-endian: the lowest word holds the lowest bits. A field written `43.7` is word 43, bit 7.
- **Floating-point constants** are stored as their IEEE-754 binary32 bit pattern.
- **Sizes.** B is bytes; KiB is 1,024 bytes. HBM addresses are in bytes. VM addresses are in 32-bit FP32 words.
- **Engines** are written `UNIT.OP`, for example `SM.MATVEC`.

### 1.3 Scope

HGI-1 defines:

- the **model descriptor**, its load path and its error behaviour (Chapter 5);
- the **program record** format, the unit operations and the address rule (Chapters 3 and 6);
- the **synchronisation and ordering** rules (Chapter 4);
- the **per-die memory map** (§6.8);
- the **simulator contract**, the goldens and the conformance tests (Chapter 8).

It does not define block-internal ports, physical design, clocking beyond what the configuration path needs, or the host software stack.

### 1.4 Design goals

The die serves one user at a time with the lowest possible decode latency, and every result must match the golden bit for bit. Within those two objectives the interface pursues one principle: **keep the hardware minimal and put the complexity in the compiler.** Compilers are written and fixed far more cheaply than silicon, and an interface that asks hardware to understand models becomes obsolete with the next model.

To apply that principle, HGI-1 sorts every way in which one model differs from another into three kinds, and gives each kind exactly one home:

| What differs between models | Where it lives | Hardware cost |
|---|---|---|
| Shape and numeric constants: widths, heads, layers, epsilon, θ, softmax scale, clamp limit, RoPE tables, norm gains, attention sinks, weight scales | **Data and program.** Tables sit in HBM. Constants are template immediates. Counts and strides go in memory descriptors. | None |
| Rigid control inside a fused fast path: token width, norm width, output formats, RoPE pairing, softmax sink, collective group, KV layout | **17 static mode fields in 9 words** (descriptor section C), loaded once per model load | Small mode logic in the blocks the hbm-generic plan already parameterises |
| Per-operator choices that already vary inside one DeepSeek token: weight format, row count, positions, segment length | **Per-operation fields** of the program record (Chapter 6) | None beyond the ports that already exist |

### 1.5 Design principles

Five rules follow from the goals. Each one is normative.

1. **Reset equals DeepSeek.** The reset value of every mode register is today's DeepSeek-V4.1 (DS) behaviour. The DS descriptor's section C therefore equals the reset values, and loading it changes nothing; the reference encoder asserts this. A DS test bench that never loads a descriptor still runs, so every existing DS timing closure and test vector stays valid.
2. **Hardware never derives.** The encoder computes the hardware mode fields (section C) from the model geometry (sections A and B) in one software function, `derive()`. Hardware only latches words and checks the magic number, version, CRC, reserved bits and legal values.
3. **One path per operator family per model.** Each family of operations (for example "RMSNorm before attention") is bound either to a fused fast path or to an exact fallback on the programmable vector unit. The golden uses the arithmetic order of the bound path, so changing a binding is a golden change (§8.2).
4. **Static during decode.** Mode registers change only at a model load, while the die is idle. There is no per-token reconfiguration.
5. **One program format for both models.** The command processor runs a stream of unit-operation records, and every engine is reached the same way. DeepSeek's existing kernels run as one unit operation (`SIMT.RUN`), so the DS evidence carries over unchanged.

### 1.6 Document status and versioning

Version 0.9 is frozen so that hardware forks, the simulator and the compilers can start in parallel. Version 1.0 freezes once the command-processor fork and the simulator have both consumed these encodings without amendment. Until then, changes follow the process in §9.5. Proposed changes from the generality review are listed in Chapter 10 and are not yet part of the interface.

---

## 2. Machine model

### 2.1 Overview

The die is a set of fixed-function and programmable **engines** (also called *units*) driven by a single in-order **command processor**. Weights, the KV cache and constant tables live in HBM. Activations live in an on-die scratch memory, the VM. A few producer–consumer pairs are joined by hardware FIFOs, called STREAM links. Dies of a tensor-parallel group exchange partial results through a collective engine.

```text
                  host: doorbell (token, position, entry)  /  completion (token, status, cycles)
                                       |  ^
                                       v  |
  +----------------------------- CMDPROC (in-order sequencer) ------------------------------+
  |  prefetch ring <- program records from HBM;  predicate;  wait-mask check;              |
  |  effective-address computation (base + L*lstride + DYN*dyn_mul);  dispatch to queues   |
  +-----+--------+--------+--------+--------+--------+--------+--------+---------+---------+
        |        |        |        |        |        |        |        |         |
       SM      SU/SFU   FUSED     ATT      DMA     COLL    ARGMAX   IDX, HC    SIMT
     (x32)   templates  norm,   QK, PV   HBM<->VM  cross-  local    (DS only) OTG-1
     matvec  & GLU      softmax  tiles   KV store  die              kernels
        |        ^                 |        |        |        ^
        |        |                 |        |        |        |
        +--STREAM (SM -> SU lanes) |        |        |        +--STREAM (LM head -> ARGMAX)
        |                          |        |        |
  ======+==========================+========+========+=====  HBM (per die, 40-bit bytes)
        weights, KV cache, tables, scales, embedding, program image, scratch
  ---------------------------------------------------------  VM (262,144 FP32 words, on die)
        activations, staged tables; every address chosen by the compiler
```

*Figure 2-1. The die as the program sees it. Each engine has its own in-order queue. STREAM links carry data directly between engines without passing through VM.*

### 2.2 The command processor

The **command processor** (CP, block `hfd_cmdproc`) is the only control engine. It is an in-order sequencer:

1. It fetches **records** from the program image in HBM through a prefetch ring.
2. It evaluates each record's predicate and skips records whose predicate is false.
3. It holds the record until the record's `wait` mask is satisfied (Chapter 4).
4. It computes the effective base address of each operand (§3.3).
5. It dispatches the record to the target unit's queue.

Each unit retires its queue in order and reports an outstanding-work count back to the CP. The CP also owns the doorbell and completion interface to the host, the per-slot DYN registers (§3.3) and the model-descriptor load path (Chapter 5).

### 2.3 The engines

Every engine is addressed by a 4-bit **unit code** in the record header. The table lists them with their purpose; Chapter 6 gives the operations each one accepts.

| Code | Unit | What it does | Main blocks |
|---:|---|---|---|
| 0 | CTL | Control steps run by the CP itself: loop, fence, end of token, MTP control | `hfd_cmdproc` |
| 1 | SM | Matrix-vector product: streams weight rows from HBM against an activation vector. Weight format is chosen per operation (BF16, FP8 block, FP4 block, INT8). 32 SMs per die. | `hfd_sm`, `smh_front_*`, tiles |
| 2 | SU | The programmable vector pipeline. A 256-bit *SU template* configures its stages (multiply, add, special function, reduce, round). Exact fallbacks run here. | `hfd_su` lanes, `su_red`, `su_full` |
| 3 | SFU | The fused SwiGLU chain | `hfd_sfu` |
| 4 | FUSED | Fused fast paths: the norm engine and fused SU chains (RMSNorm, the DS hyper-connection norm, softmax) | `norm_engine_view`, `ot_dsrom_su_softmax` |
| 5 | ATT | Attention tiles: QK scores and PV products over KV rows in HBM | `hfd_attn_half_*` |
| 6 | COLL | Cross-die collectives: all-reduce, all-gather, top-k merge, argmax merge | `hfd_coll` |
| 7 | ARGMAX | Local argmax over a logit shard | `ot_dshbm_argmax_m` |
| 8 | DMA | Row moves between HBM and VM, the KV append and the HBM write fence | svc, `hfd_loader`, kvwb |
| 9 | IDX | DeepSeek indexer and top-k selection | DS engines |
| 10 | HC | DeepSeek hyper-connection mix | `hfd_hc` |
| 11 | SIMT | Launches an existing OTG-1 SIMT kernel (DeepSeek's general-purpose kernels) | SIMT path |

### 2.4 The memory hierarchy

A record names each operand by a **memory descriptor** whose `space` field selects one of three memories (or none):

- **HBM** is one die-local byte address space, 40 bits wide, organised in 32-byte sectors. It holds everything large or persistent: weights, the KV cache, constant tables (RoPE, norm gains, sinks, scales), the embedding table, the program image and spill space. The service layer (svc) maps sectors onto stacks and pseudo-channels (PCs) with a fixed map that is the same in both model modes.
- **VM** (vector memory) is the on-die scratch: 262,144 FP32 words per die, addressed in words. It holds activations and staged tables. The compiler allocates every VM address; hardware has no allocator.
- **STREAM** is a hardware FIFO between a fixed producer and a fixed consumer, for example SM results into SU lane registers, or the LM-head matvec into ARGMAX. Data on a STREAM never touches VM. The set of stream ids a die supports is fixed by its wiring.

STREAM operands implement the project's dataflow rule that a value returns to shared memory only when another lane, unit or die needs it (AGENTS.md dataflow level 2). Using a STREAM removes a VM round trip from a serial chain.

### 2.5 Data flow through a token

For one token, data moves in a fixed pattern:

- **Weights** flow from HBM through the SMs once per token and are never stored on die.
- **Activations** stay in VM (or in STREAM links) from the embedding lookup to the final logits.
- **New KV rows** are written from VM to HBM by `DMA.STORE`; **old KV rows** flow from HBM into the ATT tiles.
- **Partial sums** of tensor-parallel matrix products cross dies through `COLL`.
- **The next token** leaves the die in the completion record.

### 2.6 Die groups and SPMD execution

A model runs on a **group** of dies that split each layer's matrices between them (tensor parallelism, TP): Qwen3-8B uses 4 dies, DeepSeek-V4.1-Flash 96. Every die of a group runs the **same program** (single program, multiple data, SPMD). Where a die needs its own slice of a table, the program addresses it with the DYN value `RANK` (§3.3).

Groups are **aligned** blocks of die ids. A die's rank is `die_id mod group_size`, its group is `die_id div group_size`, and reductions combine contributions in rank order. No member map or owner table is needed while boot partitioning keeps groups aligned.

---

## 3. Programming model

### 3.1 Programs, images and entry points

A **program** is a sequence of records stored in the **program image**, a region of HBM placed by the compiler. The model descriptor records the image's base and size (in 4 KiB pages) and up to three **entry points**, each a record offset into the image in 16-byte units:

- `entry_ar`: the normal autoregressive (AR) decode step, one token;
- `entry_verify`: the MTP verify pass (0 if absent);
- `entry_draft`: the MTP draft pass (0 if absent).

### 3.2 The record

A **record** is one unit operation with everything it needs. It has three parts:

1. a **128-bit header** (UOP) naming the unit and operation, the wait mask, a predicate, which operand descriptors follow, an integer parameter and two 32-bit immediates;
2. optionally, a **256-bit SU template** (SUT), present when the header's `tmpl` bit is set, that configures the vector pipeline;
3. one **256-bit memory descriptor** (MDESC) for each operand the record names, in the order A, B, C, O.

A record is therefore 16 to 176 bytes long. Because each record carries its own addresses, counts and formats, one SU template can serve every layer, and two consecutive records may use the same engine in different ways. Chapter 6 gives every bit.

### 3.3 Addressing: descriptors, loops and DYN values

A memory descriptor describes a two-level array: `n` elements at inner stride `istride`, repeated `m` times at outer stride `stride`. Its element format is `fmt`. The CP computes one effective base per descriptor:

> **effective base = base + L · lstride + DYN[dyn_sel] · dyn_mul**

This is the only address arithmetic the hardware performs on the program's behalf. Its terms are:

- **`L`**, the loop counter of the enclosing `CTL.LOOP` (0 outside a loop). With `lstride` set to the per-layer size of a weight block, one record addresses every layer's weights.
- **DYN values**, small per-token integers the CP computes when the doorbell arrives. `POS` (the token's position) addresses the RoPE row and the KV append slot; `TOKEN` addresses the embedding row; `RANK` addresses a die's shard; `POS1 = pos + 1` is the number of valid KV rows. The complete list is in §6.7.

A descriptor's count can also be dynamic: when `n_sel` is non-zero, `n = DYN[n_sel]`. Attention uses this to read exactly `pos + 1` KV rows.

Each verify column (a *slot*) has its own DYN bank, so a verify pass over several positions issues the same records with different `slot` values.

### 3.4 Predicates and loops

A record's 2-bit **predicate** decides whether it runs: always, only at position 0, only at positions other than 0, or only on the last loop iteration. A skipped record has no effect.

`CTL.LOOP count` and `CTL.ENDLOOP` bracket a body that runs `count` times with `L = 0 … count − 1`. Loops have one level. The body replays from the prefetch ring, so it must fit the ring. Unrolled programs are equally legal.

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

**Doorbell.** The host starts a token by ringing the doorbell with `{token 18, pos 20, job 32, gen 4, entry 2, ncol 4}` (field widths in bits). `token` is the input token (the previous step's output), `pos` its position, `entry` selects the entry point (AR, verify, draft), and `ncol` is the number of positions for a verify pass (1 at AR). The CP refuses the doorbell (`db_rdy` = 0) while a descriptor commit is settling (§5.4).

**Records.** The CP fills the DYN banks and runs records from the entry point. The token's work is entirely described by the records; no engine starts on its own.

**Completion.** `CTL.END` names a U32 operand whose element 0 is the result token. The CP range-checks it against `cp_vocab` and returns the completion `{token 18, pos 20, job, gen, status 4, cycles}`. Status codes are those of today's CP: 0 OK, 1 unit fault, 2 no result, 3 bad command or range.

### 3.6 Worked example: one Qwen3-8B decoder layer

This section traces one decoder layer of Qwen3-8B on one die of a 4-die group (TP4) at AR decode. It shows how the families of §7.2 become records and what each descriptor contains.

**Shapes.** Qwen3-8B has a hidden width of 4,096, 36 layers, 32 query heads and 8 KV heads of dimension 128, and an FFN width of 12,288 (from `compiler/models/qwen3-8b/config.json`). At TP4 each die holds 8 query heads and 2 KV heads, so its QKV projection has 1,024 + 256 + 256 = 1,536 rows, its output projection takes 1,024 inputs, and its gate/up and down projections cover 3,072 FFN columns. Weights are INT8 with one BF16 scale per row.

**Placement.** The layer order and the VM placement below follow the committed TP4 lowering (`tools/qwen_r25_decode_program.py`): the residual stream lives at VM word 229,376, the "next" buffer at 233,472, and scratch starts at word 0. HBM bases are written symbolically because the compiler places them: `Wqkv`, `Wo`, `Wgu`, `Wdown` are this die's weight blocks for layer 0; `Sw` is the per-layer stride of each block; `Tbl` is the layer's small tables (norm gains and row scales); `KV` is this die's KV region. The weight blocks follow the SM layout rule, which is still an open item (§10.1, item 2).

**The prologue** runs once per token before the layer loop: the embedding row is fetched with `DMA.LOAD` at `TOKEN · emb_row_bytes` and dequantised by an `SU.VOP`, and the RoPE cos/sin row for this position is fetched with `DMA.LOAD` (`dyn_sel = POS`) into VM. The layer body is then wrapped in `CTL.LOOP 36` … `CTL.ENDLOOP`, so `L` is the layer index.

*Table 3-1. Records of one decoder layer on one die (L = layer index).*

| # | Record | Operands (space, base, shape, format) | `param`, immediates | `wait` | Family |
|---:|---|---|---|---|---|
| 1 | `DMA.LOAD` | A: HBM `Tbl + L·lstride`; O: VM table area | — | SU, FUSED | staging |
| 2 | `FUSED.ROW_NORM` | A: VM 229,376, n = 4,096; B: gain (VM table area); O: VM 20,480 | seg = 0; `imm_a` = eps 1e-6 (`0x358637BD`) | DMA, SU | prenorm |
| 3 | `SM.MATVEC` | A: VM 20,480, n = 4,096; B: HBM `Wqkv + L·Sw`, m = 1,536 rows of n = 4,096, INT8; O: STREAM to SU | fmt = 3 (INT8), positions − 1 = 0 | FUSED | qkv |
| 4 | `SU.VOP` + template | A: STREAM from SM; B: VM row scales (1,536); O: VM 0, n = 1,536 | template: M1 = A·B | — | row_scale_qkv |
| 5 | `FUSED.ROW_NORM` | A: VM 0, n = 128, m = 8; B: q-norm gain; O: VM 16,384 | seg = 128; `imm_a` = eps | SU | QK-norm (q) |
| 6 | `FUSED.ROW_NORM` | A: VM 1,024, n = 128, m = 2; B: k-norm gain; O: VM 17,408 | seg = 128; `imm_a` = eps | — | QK-norm (k) |
| 7 | `SU.VOP` + template | A: VM 16,384, the 10 normalised q and k heads; C: the same vector, read at the pair partner; B and D: the cos and sin rows staged by the prologue; O: VM 8,192 (q) and 9,216 (k) | template: `c_pair` (partner i XOR 64, from `rope_half`) | FUSED | RoPE |
| 8 | `SU.VOP` + template | A: VM 8,192, n = 1,024 (rotated q); O: in place | template: `rnd` (Q rounded to BF16) | SU | roundQ |
| 9 | `DMA.STORE` | A: VM 9,216 (rotated k) and 1,280 (v), 4 rows of 128; O: HBM `KV + L·lstride + POS·128`, m = 4 rows (K and V of 2 heads) of n = 128 B, FP8 | `dyn_sel` = POS, `dyn_mul` = 128 | SU | kv_append |
| 10 | `DMA.FENCE` | — | — | — | kv_fence |
| 11 | `ATT.QK` (×2, one per KV head) | A: VM 8,192 + 512·h, the 4 query heads that share KV head h; B: HBM K rows of this head, `n_sel` = POS1; O: VM scores area | lanes = 4, slices − 1 = 1 (2 × 64) | DMA | attention_qk |
| 12 | softmax (`FUSED`) | A: VM scores, pos + 1 rows per head; O: VM exponentials and denominators | multipass (`sfx_multipass` = 1), no sink | ATT | softmax |
| 13 | `ATT.PV` (×2) | A: VM exponentials; B: HBM V rows, `n_sel` = POS1; O: VM | lanes = 4, slices − 1 = 1 | FUSED | attention_pv |
| 14 | softmax pass 3 (`FUSED`) | A: VM PV result; O: VM attention output (1,024) | — | ATT | pv_normalize |
| 15 | `SM.MATVEC` | A: VM attention output, n = 1,024; B: HBM `Wo + L·Sw`, m = 4,096 rows of n = 1,024, INT8; O: VM partial | fmt = 3 | FUSED | o |
| 16 | `COLL.ALL_REDUCE_SUM` | A: VM partial (4,096); O: VM sum | group of 4, rank-order reduction | SM | all_reduce_o |
| 17 | `SU.VOP` + template | A: VM sum; B: VM o row scales; O: VM 233,472 | M1 = A·B | COLL | row_scale_o |
| 18 | `SU.VOP` + template | A: VM 229,376; C: VM 233,472; O: VM 229,376 | AD = +C | SU | residual |
| 19 | `FUSED.ROW_NORM` | as record 2, with the post-attention gain | seg = 0 | SU | prenorm |
| 20 | `SM.MATVEC` | A: VM 20,480, n = 4,096; B: HBM `Wgu + L·Sw`, m = 6,144 rows (gate then up), INT8; O: VM 0, n = 3,072, m = 2, stride = 4,096 | fmt = 3 | FUSED | gu |
| 21 | `SU.VOP` + template | A: VM 0, n = 3,072, m = 2, stride = 4,096; B: VM gate/up row scales; O: in place | M1 = A·B | SM | row_scale_gu |
| 22 | `SFU.GLU` | A: VM 0 (gate); B: VM 4,096 (up); O: VM 8,192, n = 3,072 | — (`glu_*` modes: BF16 out, no clamp, no route weight) | SU | SwiGLU |
| 23 | `SM.MATVEC` | A: VM 8,192, n = 3,072; B: HBM `Wdown + L·Sw`, m = 4,096 rows of n = 3,072, INT8; O: VM partial | fmt = 3 | SFU | down |
| 24 | `COLL.ALL_REDUCE_SUM` | A: VM partial; O: VM sum | group of 4 | SM | all_reduce_down |
| 25 | `SU.VOP` + template | A: VM sum; B: VM down row scales; O: VM 233,472 | M1 = A·B | COLL | row_scale_down |
| 26 | `SU.VOP` + template | A: VM 229,376; C: VM 233,472; O: VM 229,376 | AD = +C | SU | residual |

The table uses the unit's own wait bit (for example SU after SU) wherever a record reads what the previous record of the same unit wrote; §4.2 explains why.

**Walking through the layer.**

- **Staging (1).** The layer's norm gains and row scales are small, so the program copies them into VM once per layer. Its wait mask drains SU and FUSED so that the previous layer's readers of the staging area have finished (a write-after-read hazard).
- **Pre-attention norm (2).** The norm engine reads the residual stream, the gain and epsilon (an immediate), and publishes BF16 because `norm_out_bf16` = 1 for Qwen. `seg = 0` means one norm over the full 4,096-wide vector (`norm_d_units` = 32). The output goes to VM 20,480, apart from the projection outputs at word 0, so that no record overwrites a vector another engine may still be reading (a write-after-read hazard that placement removes without a wait).
- **QKV projection and row scale (3, 4).** The SM streams 1,536 INT8 rows from HBM. Its output goes to a STREAM link, so the SU template that applies the per-row BF16 scale consumes it straight from the SM with no VM round trip and no wait bit: the STREAM credits order the two records. The scale multiply is the golden's rounding point (one FP32 round-to-nearest-even multiply).
- **QK-norm (5, 6).** Qwen normalises each query and key head separately. `seg = 128` makes the norm engine produce one result per 128-element segment: 8 query heads in record 5 and 2 key heads in record 6, each with its own gain.
- **RoPE and rounding (7, 8).** Rotary position embedding is an SU template with `c_pair`: element i is combined with its partner i XOR 64; it writes to a separate area because each element also reads its partner (split-half pairing, selected by `rope_half` = 1 over all 128 dimensions, `rope_rot_log2` = 7). The cos/sin values are ordinary HBM data fetched for this position, so there is no θ or YaRN logic in hardware. Q is then rounded to BF16; K and V are converted to FP8 by the append. *Note:* the template's D source (the sine) has no descriptor slot in v0.9's A, B, C, O order. This is proposed change C2 (§10.3).
- **KV append and fence (9, 10).** With `kv_dense` = 1, `DMA.STORE` writes the new K and V rows into the dense per-head layout `[layer][kv head][K|V][pos][128]` in FP8, at `POS · 128` bytes into each row plane. `DMA.FENCE` makes the posted writes visible before attention reads them.
- **Attention (11–14).** Each KV head serves 4 query heads, so one ATT tile uses 4 of its 16 lanes. `n_sel = POS1` makes the tile read exactly the `pos + 1` valid KV rows, and the cache-length mask follows from that count. The softmax runs in multipass mode because rows can exceed the 640 a single pass holds: pass 1 finds the global maximum, pass 2 sums exponentials over fixed 640-row chunks in chunk order, and pass 3 (record 14) applies the normalisation to the PV result. There is no attention sink for Qwen (`sfx_sink_off` = 1). The softmax scale is the golden's literal FP32(128^−0.5) = `0x3DB504F3` (descriptor word 17). It is an SU immediate on the record that applies it and is never folded into the weights; v0.9 does not fix which record that is. *Note:* the softmax operation is used here but missing from the v0.9 operation table (proposed change C1).
- **Output projection and all-reduce (15–17).** Each die multiplies its 1,024 attention outputs by its slice of W_o and produces a 4,096-wide partial sum. `COLL.ALL_REDUCE_SUM` adds the four partials in rank order on every die. The row scale is applied to the reduced sum, as the lowering specifies.
- **Residual (18).** The SU adds the projected output to the residual stream in place.
- **Feed-forward (19–23).** A second norm, the gate/up projection (6,144 rows written as two 3,072-word halves, using `m = 2` and `stride = 4,096` in the output descriptor), the row scales, the SwiGLU chain on the SFU (with BF16 output, no clamp and no route weight, because the `glu_*` modes say so for Qwen), and the down projection.
- **Second all-reduce and residual (24–26).** As for attention.

After 36 iterations, the epilogue runs the final norm, the LM head (37,984 vocabulary rows per die, streamed), its row scale, `ARGMAX.LOCAL`, `COLL.ARGMAX_MERGE` (which converts local ids to global ids using `coll_head_rows`) and `CTL.END`.

---

## 4. Synchronisation and ordering

### 4.1 Ordering within a unit

Each unit receives records in program order and retires them in order. Results and faults of one unit therefore appear in program order. Ordering *between* units is established only by the four mechanisms below.

### 4.2 The four mechanisms

There are exactly four synchronisation mechanisms. There are no semaphores, events or kernel-level barriers.

**1. The `wait` mask: unit drain.** The header carries 12 wait bits, one per unit. The CP issues the record only when every unit named in the mask has nothing outstanding. The compiler computes the mask from region hazards (read-after-write, write-after-read, write-after-write on VM or HBM), as `tools/hdc_program_v41.py schedule()` does today.

*Example:* in Table 3-1, record 3 (`SM.MATVEC`) reads the normalised vector that record 2 (`FUSED`) wrote, so it waits on FUSED. Record 1 overwrites the staging area, so it waits on SU and FUSED, which read the previous layer's copy.

*Hazards covered:* all cross-unit memory dependences. v0.9 states that cross-unit dependences use `wait` and that each unit retires in order; it does not state whether a unit may begin a record before an earlier record of the same unit has completed its writes. Setting the unit's own bit is always safe, which is why the worked example does so (see §10.4).

**2. STREAM credits: producer to consumer.** When a producer and a consumer are joined by a STREAM link, the consumer's record needs no wait bit. The FIFO's credit flow control orders the data: the consumer cannot read an element before the producer has written it, and the producer cannot overrun the consumer.

*Example:* records 3 and 4 (SM to SU), and the LM head into `ARGMAX.LOCAL`.

*Hazards covered:* read-after-write on the streamed data, at element granularity, while both engines run concurrently.

**3. Collective arrival: cross-die.** Collectives synchronise themselves by data arrival. Every die of a group issues the same collectives in the same program order, and the collective endpoint matches them with a per-group sequence counter. A die's `COLL` record completes when the contributions it needs have arrived.

*Example:* record 16 completes on each die only when all four partial sums have arrived; record 17 waits on COLL.

*Hazards covered:* cross-die data dependences. Because the group runs one SPMD program, no explicit barrier is needed.

**4. `CTL.FENCE` and `DMA.FENCE`: HBM write visibility.** HBM writes are posted. A fence waits for all units and for every posted HBM write to be visible. `DMA.FENCE` makes a KV append visible to the next ATT read.

*Example:* record 10 orders the KV append before the attention reads in records 11 and 13.

*Hazards covered:* read-after-write through HBM, where the writer's completion count alone does not guarantee visibility.

### 4.3 The head-of-line and drain caveat

Two consequences of this model affect performance, not correctness:

- **Drain is coarse.** A wait bit waits for the whole unit to drain, not for one specific earlier record. A record that depends on an early record of a busy unit also waits for every later record of that unit.
- **The sequencer is in order.** A record held by its wait mask also holds every record behind it, including records for idle units with no dependence on it (head-of-line blocking).

The compiler hides both by ordering records so that independent chains are interleaved (AGENTS.md dataflow level 4) and by using STREAM links where a fixed producer-consumer pair exists. The simulator models both effects (§8.1), so their cost appears in the timing results.

### 4.4 Transaction-level exactness

Latency may change between implementations, but the order of results and faults may not: it is fixed by program order within a unit and by the four mechanisms. Every result is bit-exact against the golden regardless of timing.

---

## 5. Model configuration

### 5.1 Purpose

The **model descriptor** (MD) is a 64-word, 256-byte image that tells the die which model it runs. It has two audiences:

- **Hardware** reads only the header, the 9 block-mode words of section C, the program words of section D and the CRC.
- **Software** (compiler, golden, simulator, table generator, validator) reads the whole descriptor, including a complete geometry table (section B), so that every tool reads one table instead of each parsing Hugging Face configuration files.

### 5.2 Layout

The descriptor is 64 little-endian 32-bit words. Every reserved bit must be 0. `spec.json` → `md_fields` is the authority for every bit position; §6.10 reproduces it.

| Words | Section | Read by | Content |
|---|---|---|---|
| 0–3 | A, header | CP (words 0–1), software | magic `0x31494748` ("HGI1"), version 0.9, length 64, model class (1 DS-V4.1-Flash, 2 Qwen3 dense), feature flags (MOE, INDEXER, HC, ENGRAM, MTP, QK_NORM, ATTN_SINK, KV_COMPRESS, SHARED_LATENT_KV, Q_LORA, O_GROUPS, SWIGLU_CLAMP) |
| 4–31 | B, geometry | software only | hidden width, layers, MTP layers, query and KV heads, head dimension, vocabulary, FFN and MoE widths, norm type and epsilon, activation, RoPE {pairing, dims, offset, scaling, θ, factor, YaRN β, compressed θ}, window, context, softmax-scale literal, SwiGLU limit, weight/KV/activation/scale/expert formats, MoE {experts, shared, top-k, scoring, normalisation, scaling}, indexer, candidate selection, HC {copies, Sinkhorn iterations, epsilon}, Engram, MTP {kind, block, Markov rank, draft experts, noise token}, q/o LoRA ranks, o groups, TP size |
| 32–39 | B, identity | software | sha256 of the model's `config.json`, which binds the descriptor to one model |
| 40–48 | **C, block modes** | **hardware** | the 17 mode fields of §5.3 |
| 49–55 | C, reserved | — | 0 (held for the Qwen MTP fields, §10.2 D4) |
| 56–61 | D, program | CP | entry offsets (AR, verify, draft) and the program image's HBM base and size |
| 62 | — | — | 0 |
| 63 | CRC | CP | IEEE CRC-32 of words 0–62 |

Section B is deliberately complete. Per-layer lists (compression ratios, Engram layer ids, KV-source and index-source layer ids) stay in the program and in the bound configuration file (identified by its sha256), not in the descriptor.

### 5.3 The block-mode fields

A mode field exists only where a fused fast path cannot express a model through data or a per-operation field. These are exactly the parameters of the approved hbm-generic list, and nothing else. The DS value of every field is its reset value.

*Table 5-1. Section C mode fields.*

| Block | Field (word.bit) | Bits | Legal | DS (reset) | Qwen3-8B | What the field does, and why it is a mode |
|---|---|---:|---|---:|---:|---|
| CP (`hfd_cmdproc_n/s`) | `cp_vocab` (40.0) | 18 | 1 … 2¹⁸ | 129,280 | 151,936 | Range check for doorbell and completion tokens, against a register instead of the `VOCAB_SIZE` parameter. The token width is **18 everywhere**, with no field; DS ids are below 2¹⁷ and leave bit 17 at 0. |
| | `cp_ctx_max` (41.0) | 21 | 1 … 2²⁰ | 2²⁰ | 40,960 | Range check for the doorbell position, against a register. The position width stays 20. |
| RoPE chains (q/kv chains in `hfd_su`) | `rope_half` (42.0) | 1 | 0, 1 | 0 | 1 | Pair partner i XOR 1 (adjacent pairs, DS) or i XOR dims/2 (split-half, Qwen). The sign of the partner term comes from the same bit of i. It costs one operand-offset multiplexer; on the c12 lanes, an XOR on a lane-index bit of `ld_c`. |
| | `rope_rot_log2` (42.1) | 3 | 6, 7 | 6 | 7 | Rotated span: the last 64 dimensions (the DS tail) or all 128. The start offset is head_dim − 2^k, from the operation's descriptor. The tables are **HBM data** fetched per position; there is no θ or YaRN in hardware. |
| Norm engine (`norm_engine_view`, grp16, fused norm chains) | `norm_d_units` (43.0) | 6 | 32, 40 | 40 | 32 | Vector width 4,096 or 5,120. The D4096 reduction tree is the D5120 tree with a tail padded with +0, which is exact (x + 0 = x on the pairwise levels). The 1/D divide set already holds 2¹². |
| | `norm_hc_off` (43.6) | 1 | 0, 1 | 0 | 1 | Bypass the DS hyper-connection pre-mix; the input is the residual itself. |
| | `norm_out_bf16` (43.7) | 1 | 0, 1 | 0 | 1 | Publish BF16 (round to nearest even) instead of the FP8-quantised output. |
| | *(per op)* `seg` | — | 0, 128 | 0 | 0 (RMSNorm), 128 (QK-norm) | **Per operation, not static**: Qwen issues both segment lengths in every layer. It is carried in the `param` of `FUSED.ROW_NORM`. A segmented reduction produces one result per 128-element segment. |
| Softmax (`ot_dsrom_su_softmax`) | `sfx_sink_off` (44.0) ¹ | 1 | 0, 1 | 0 | 1 | Remove the attention sink from the maximum and from the denominator. Feeding a sink of −2¹⁰⁰ as data would also be exact, but the bit avoids a fake table; the hbm-generic plan approved the bit. |
| | `sfx_multipass` (44.1) | 1 | 0, 1 | 0 | 1 | For rows longer than NVMAX·LPH (640): pass 1 finds the global maximum; pass 2 computes exponentials and their sum over fixed 640-row chunks with carry-in, in chunk order; pass 3 scales (the PV normalise). NVMAX stays 40. 8,192 rows are 13 chunks. |
| SwiGLU fused chain (`hfd_sfu`) | `glu_out_bf16` (45.0) | 1 | 0, 1 | 0 | 1 | Skip the FP8 `PUBLISH_QUANT` and publish BF16. |
| | `glu_clamp_off` (45.1) | 1 | 0, 1 | 0 | 1 | Skip the `swiglu_limit` clamp. |
| | `glu_routew_off` (45.2) | 1 | 0, 1 | 0 | 1 | Skip the route-weight multiply (equivalent to × 1.0, exact). |
| Collective (`hfd_coll`, truecredit, owner half) | `coll_group_size` (46.0) | 8 | 4, 8, 96 | 96 | 4 | Groups are aligned blocks of die ids (§2.6). The fixed-order reduction is unchanged. |
| | `coll_head_rows` (46.8) | 18 | 0 … 2¹⁸ − 1 | 0 | 37,984 | The argmax merge carries 18-bit ids: global id = rank · rows + local id. Ties go to the lowest global id (numpy semantics). 0 means the ids are already global (DS today). |
| KV write-back, ingest, causal mask (`hfd_kvwb_native`, `hfd_host_ingest`, `ot_qwen_r25_causal_mask`) | `kv_dense` (47.0) | 1 | 0, 1 | 0 | 1 | 0 = DS: window ring (WR ≥ W + PMAX), selected rows, ROWS/IKEY ingest. 1 = dense per-head linear layout `[layer][kvh][K\|V][pos][head_dim]` in FP8, cache-length mask (rows ≤ pos), and QKV NHD → FP8 per-head-row ingest. The layout base and per-layer strides come from the operation's descriptor. One bit drives all three blocks because they always change together. |
| Embedding fetch (svc row + SU dequantisation) | `emb_int8` (48.0) | 1 | 0, 1 | 0 | 1 | Row = INT8 codes plus a BF16 row scale, dequantised on the SU (DS uses BF16 rows). |
| | `emb_row_bytes` (48.1) | 16 | 1 … 65,535 | 10,240 | 4,128 | Row stride, 32-byte aligned (Qwen: 4,096 codes + BF16 scale + padding). Row address = base + token · stride, with an 18-bit token. |

¹ Owner decision D3 (approved after the v0.9 freeze) drops this bit in favour of a −2¹⁰⁰ sink passed as data, subject to a bench. It is not yet applied to the encoding; see §10.2.

**Hardware changes that need no mode field.** Several blocks change for Qwen without a mode, because the change is per-operation, universal, or only reachable from programs:

| Block | Change | Why there is no mode field |
|---|---|---|
| SM (`smh_front_c/n/s`, tiles) | `op_fmt` 3 = INT8 → BF16 unpack plus half-line issue | The format is **per operation**: DS mixes BF16, FP8 and FP4 inside one token. The latency of formats 0–2 is bypass-matched, so DS cycles are unchanged. The per-row BF16 scale is applied by the consuming SU operation (§7.2). |
| `ot_dshbm_argmax_m` | index width 17 → 18 | Universal. DS ids keep bit 17 at 0. |
| svc segments (`hfd_svc_*`) | Kind-1 KV reads and kind-2 index-key reads striped over all 32 PCs; posted-write merge | Both models need it (Qwen for bandwidth, DS for the native indexer). It is the same function in both modes. |
| Attention tiles (`hfd_attn_half_*`) | none | The GQA head mapping is a program choice: one KV head per tile, with 4 of 16 lanes at AR and 16 at verify with 4 positions. A per-lane KV select is rejected: it would reopen closed blocks while attention is KV-bound. |
| `hfd_su` lanes, `hfd_sfu`, `su_red`, `su_full` | none | Generic. They run the exact fallbacks (row scale, residual, embedding dequantisation, argmax-merge fallback). |
| `hfd_mtp`, `dspark_ctl`, `hdc_accept` | token width 18 when reopened | Qwen MTP comes after the owner's τ measurement. Its parameters (B, STAGES, MARKOV_EN, UNION_EN) are **not** in v0.9; they get descriptor words 49–55 at that decision. |
| `hfd_hc`, HCP, indexer, Engram | none | DS only. Qwen programs never issue them. |

### 5.4 The configuration path

The descriptor reaches the blocks through the existing 64-bit host write port of the CP (`cmd_we`, `cmd_addr`, `cmd_wdata`). No new pin is needed.

1. **CFG window.** Writes to addresses with the window bit set place descriptor word pairs (word 2a in bits 31:0, word 2a + 1 in bits 63:32) into the CP's 64-word staging buffer. One further address is `CFG_COMMIT`.
2. **Commit.** At `CFG_COMMIT` the CP runs the hardware check (§5.6). On success it broadcasts the section-C words on the **configuration bus** `cfg_v, cfg_addr[5:0], cfg_data[31:0], cfg_commit`. The bus is registered at every station it crosses and passes through the clock-crossing synchronisers into the 0.9 GHz serial-chain domain.
3. **Latch.** Each block decodes only its own word addresses into shadow registers. On `cfg_commit` it copies the shadow registers into its active registers.
4. **Settle.** The CP waits `CFG_SETTLE` cycles (at least the deepest bus latency plus 16; 64 by default), then sets `CFG_STATUS.loaded`. Doorbells are refused (`db_rdy` = 0) while a commit settles.

Because active registers change only while every unit is idle, they are **quasi-static**:

- synthesis treats them as constants for timing (`set_false_path -from` the `*cfg_act*` registers, with the settle interval as the hold-off);
- no mode register sits on a 1.2 GHz path as a timed launch point;
- a fork whose active registers are held at reset must be equivalent to the legacy block (conformance test CF-1, §8.4).

### 5.5 Load sequence

Once per model load:

1. The host writes the model image into HBM through `hfd_loader`: weights, tables, scales, the embedding and the program records (§6.8).
2. The host writes the 32 descriptor word pairs into the CFG window, then writes `CFG_COMMIT`.
3. The CP checks the descriptor, broadcasts, settles and sets `loaded`. On an error it sets `CFG_STATUS.err`, broadcasts nothing and keeps the previous active values.
4. The host reads `CFG_STATUS`. On `loaded` it rings the first doorbell.

Reloading the same model is idempotent. Switching models repeats steps 1–4 with the die idle. That takes seconds and is off the token path.

### 5.6 Validation and errors

The hardware checks are implemented once, in `tools/hbm_generic_iface.py` `hw_check()`. The CP RTL must match them case for case (conformance test CF-0).

| Code | Name | Condition | Effect |
|---:|---|---|---|
| 0 | OK | — | Modes become active after the settle interval |
| 1 | E_MAGIC | word 0 ≠ `0x31494748` | Refused; previous modes kept |
| 2 | E_VERSION | major.minor ≠ 0.9, or length ≠ 64 | Refused |
| 3 | E_CRC | CRC-32 of words 0–62 ≠ word 63 | Refused |
| 4 | E_BUSY | Commit while a job runs or any unit queue is non-empty | Refused |
| 5 | E_RANGE | A section-C field outside its legal set (Table 5-1) | Refused |
| 6 | E_RESERVED | A reserved bit set in a hardware-read word | Refused |

- **Before any load**, the reset (DS) values apply and doorbells are accepted. This keeps every existing DS bench valid.
- **After an error**, the last good values stay active.
- **Software-only check:** section C must equal `derive(A, B)`. The encoder and the conformance harness run this check; hardware does not.

### 5.7 The two descriptors

The encoder generates both descriptors from the checked-in `compiler/models/*/config.json` files and writes them as `md_ds_v41_flash.{hex,json}` and `md_qwen3_8b.{hex,json}`.

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
| CRC-32 (word 63) | `0x4536bf09` | `0xfd057015` |

---

## 6. Record and descriptor encoding reference

This chapter is the bit-level reference. `spec.json` is authoritative; these tables reproduce it.

### 6.1 Record layout

| Part | Size | Present when |
|---|---|---|
| Header (UOP) | 128 bits (16 B) | always |
| SU template (SUT) | 256 bits (32 B) | header bit `tmpl` = 1 |
| Memory descriptors (MDESC) | 256 bits (32 B) each | one per set bit of `opnd`, in A, B, C, O order |

A record is 16 to 176 bytes long.

### 6.2 Header (UOP, 128 bits)

| Bits | Field | Meaning |
|---|---|---|
| 127:124 | `unit` | Unit code (§2.3) |
| 123:118 | `op` | Operation within the unit (§6.5) |
| 117:106 | `wait` | Unit drain mask: one bit per unit (§4.2) |
| 105:104 | `pred` | Predicate (§6.3) |
| 103:100 | `opnd` | Which of the A, B, C, O descriptors follow |
| 99 | `tmpl` | An SU template follows |
| 98:96 | `slot` | Position slot (verify column) whose DYN bank this operation uses |
| 95:64 | `param` | Unit-specific integer (§6.5) |
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

| Bits | Field | Width | Meaning |
|---|---|---:|---|
| 1:0 | `space` | 2 | 0 HBM, 1 VM, 2 STREAM, 3 NONE |
| 4:2 | `fmt` | 3 | Element format (table below) |
| 47:8 | `base` | 40 | HBM byte address (32 B aligned), or VM FP32-word address |
| 67:48 | `n` | 20 | Inner count |
| 87:68 | `m` | 20 | Outer count |
| 119:88 | `stride` | 32 | Outer stride |
| 135:120 | `istride` | 16 | Inner element stride (0 means 1) |
| 167:136 | `lstride` | 32 | Per-loop-iteration stride |
| 172:168 | `dyn_sel` | 5 | DYN value added to the base (§6.7) |
| 199:173 | `dyn_mul` | 27 | Multiplier of that DYN value |
| 204:200 | `n_sel` | 5 | 0: static `n`; otherwise `n` = DYN[`n_sel`] |

Bits 7:5 and 255:205 are reserved. The effective base is `base + L·lstride + DYN[dyn_sel]·dyn_mul` (§3.3).

| `fmt` | Format |
|---:|---|
| 0 | FP32 |
| 1 | BF16 |
| 2 | FP8E4M3 |
| 3 | FP4E2M1 |
| 4 | INT8 |
| 5 | U32 |
| 6 | UE8M0 |

### 6.5 Unit operations

Operations are listed per unit in `spec.json` → `uop.ops`, in the order shown.

| Unit.op | Operands | `param` | Semantics (bit-exact reference) |
|---|---|---|---|
| CTL.NOP, CTL.FENCE | — | — | FENCE waits for all units and for every posted HBM write to be visible |
| CTL.LOOP, CTL.ENDLOOP | — | count (LOOP) | One level; L = 0 … count − 1; the body replays from the prefetch ring and must fit it. Unrolled programs are equally legal. |
| CTL.END | A = U32 token | — | Completion token = A[0], range-checked against `cp_vocab` |
| CTL.TOKX, CTL.AMAX, CTL.ACCEPT | A | slot | The existing MTP control steps of `hdc_isa_v41`; reserved until the Qwen MTP decision (DS keeps its `dspark_ctl`) |
| SM.MATVEC | A = x (VM or STREAM), B = weights (HBM, fmt), O = y (VM or STREAM) | [1:0] format (0 BF16, 1 FP8 block-dot, 2 FP4 block-dot, 3 INT8); [4:2] positions − 1 (one weight read shared by up to 8 slots) | smh arithmetic (tc16 ring, column tree, stack pairing). Rows are split over the die's 32 SMs by the SM layout rule (§10.1, item 2). |
| SU.VOP | template, A–D, O | — | `Machine.su1` |
| SFU.GLU | A = gate, B = up, C = route weight, O | — | The fused SwiGLU chain under the `glu_*` modes |
| FUSED.HC_PRE_NORM, ROW_NORM, HC_POST | A, B = gain, O | [7:0] seg (0 or 128) for ROW_NORM | The norm engine under the `norm_*` modes; `imm_a` = epsilon |
| ATT.QK, ATT.PV | A = q or p (VM), B = K or V rows (HBM, `n_sel` = POS1), O | [3:0] head lanes used; [7:4] 64-element slices per head − 1 | Tile chunk8 plus pairwise per 64-element slice, then the slices in slice order |
| COLL.ALL_REDUCE_SUM, ALL_GATHER, TOPK_MERGE, ARGMAX_MERGE | A = local, O = result | — | The owner's fixed-order reduction in rank order. ARGMAX_MERGE uses `coll_head_rows`. |
| ARGMAX.LOCAL | A = logits (STREAM or VM), O = {value, id} | — | numpy argmax: lowest index on ties; NaN flag reported |
| DMA.LOAD, STORE, FENCE | A = source, O = destination | — | HBM ↔ VM row moves (embedding row, RoPE row at POS, sinks, scales). A STORE under `kv_dense` is the KV append; FENCE makes it visible to the next ATT read. |
| IDX.INDEX_Q, INDEX_SCORES, TOPK_LOCAL, SELECT; HC.HC_MIX | DS only | — | Today's DS engines |
| SIMT.RUN | — | entry PC (14 bits) | Launches an existing OTG-1 kernel on the SM mask in `imm_a` and waits for it to finish. **This is how every committed DS kernel runs unchanged.** |

### 6.6 SU template (SUT, 256 bits)

The SU template carries the pipeline fields of the existing SU operation set (`tools/hdc_isa_v41.py`). Its semantics are `tools/hdc_program_v41.py` `Machine.su1` (R-ARITH chunk8). `spec.json` lists the fields in this order with these widths; 142 of the 256 bits are used.

| Group | Fields (width in bits) |
|---|---|
| Operand sources | `a_src` 2, `a_ind` 2, `b_src` 2, `b_half` 1, `c_src` 2, `c_pair` 1, `d_src` 2 |
| Pre-operations | `a_rnd` 1, `a_relu` 1, `a_min` 1, `c_clip` 1 |
| Pipeline stages | `m1` 3, `m2` 2, `qm` 3, `ad` 3, `sfu` 3, `e1` 3, `e2` 2, `rnd` 1 |
| Destination and reduction | `dst` 2, `red` 2, `red_sq` 1, `red_whole` 1, `red_rnd` 1, `su_vec` 2, `red_tree` 1 |
| Immediates | `imm1` 32, `imm2` 32, `imm3` 32 |

The only semantic change from `hdc_isa_v41` is that the partner and sign of `c_pair` follow `rope_half` and `rope_rot_log2` (partner i XOR 1 for DS, i XOR dims/2 under `rope_half`). The bases and strides that the 1,536-bit `hdc_isa_v41` instruction word carried move into the memory descriptors, so one template serves every layer.

### 6.7 DYN values

The CP computes the DYN values at the doorbell, one bank per slot.

| Code | Name | Value |
|---:|---|---|
| 0 | ZERO | 0 |
| 1 | POS | the token's position |
| 2 | POS1 | pos + 1, the number of valid KV rows |
| 3 | TOKEN | the doorbell token |
| 4 | L | the loop counter |
| 5 | RANK | the die's rank in its group |
| 6 | SLOT | the slot (verify column) |
| 7 | POS_SLOT | pos + slot |
| 8–31 | DS selectors | the window and compressed-row counts of `hdc_isa_v41.FULL_DYN`, unchanged |

### 6.8 Memory map (per die)

**HBM** is one die-local, 40-bit byte address space with 32-byte sectors. The svc address map (sector → stack and PC) is fixed and the same in both modes.

**Required:** a contiguous KV or index-key sweep must spread over all 32 PCs (the svc striping fork). The old fixed `KV_PC` path is not a legal target for `kv_dense` reads.

**Regions** are placed by the compiler and recorded in the image manifest, not in hardware:

| Region | Content |
|---|---|
| IMAGE | Program records; `image_base` and `image_pages` in descriptor section D |
| TABLES | RoPE cos/sin rows per position (Qwen: one set, θ = 10⁶, 128 dims; DS: plain, YaRN and compressed sets), norm gains, sinks, softmax-scale-free constants |
| SCALES | INT8 per-row BF16 scales (Qwen) or UE8M0 block scales (DS) |
| WEIGHTS | Per-SM layout by the SM layout rule |
| EMBED | Row stride `emb_row_bytes`, replicated per die |
| HEAD | This die's vocabulary shard, `coll_head_rows` rows |
| KV | Qwen: `[layer][kvh][K\|V][pos][128]` FP8, 2 KV heads per die at TP4. DS: today's ring layout. |
| SCRATCH | Spills and collective staging |

**VM** is FP32-word addressed (the 262,144-word VM of a die) and allocated by the compiler.

**Alignment.** HBM bases are 32-byte aligned; KV rows are whole sectors.

### 6.9 Doorbell and completion

| Record | Fields (width in bits) |
|---|---|
| Doorbell | `token` 18, `pos` 20, `job` 32, `gen` 4, `entry` 2, `ncol` 4 |
| Completion | `token` 18, `pos` 20, `job`, `gen`, `status` 4, `cycles` |

Completion status: 0 OK, 1 unit fault, 2 no result, 3 bad command or range.

### 6.10 Model-descriptor bit map

Every field, as `spec.json` → `md_fields` lists it. "SW" means read by software only.

| Field | Word | LSB | Width | Reader | Meaning |
|---|---:|---:|---:|---|---|
| `magic` | 0 | 0 | 32 | CP | Rejects a non-HGI image |
| `ver_minor` | 1 | 0 | 8 | CP | Rejects an incompatible layout |
| `ver_major` | 1 | 8 | 8 | CP | Rejects an incompatible layout |
| `n_words` | 1 | 16 | 8 | CP | Fixed at 64; guards a truncated load |
| `model_class` | 2 | 0 | 8 | SW | 1 DeepSeek-V4.1-Flash, 2 Qwen3 dense; names the golden |
| `features` | 3 | 0 | 12 | SW | Operator families the program contains (bit order as in §5.2) |
| `hidden` | 4 | 0 | 16 | SW | Residual width |
| `layers` | 4 | 16 | 8 | SW | Backbone layers |
| `mtp_layers` | 4 | 24 | 4 | SW | Built-in draft layers (DSpark 3) |
| `q_heads` | 5 | 0 | 8 | SW | Attention heads |
| `kv_heads` | 5 | 8 | 8 | SW | KV heads (1 = shared latent / MQA) |
| `head_dim` | 5 | 16 | 12 | SW | Per-head width |
| `vocab` | 6 | 0 | 18 | SW | Vocabulary (151,936 needs 18 bits) |
| `ffn_inter` | 7 | 0 | 16 | SW | Dense FFN width (0 = none) |
| `moe_inter` | 7 | 16 | 16 | SW | Expert FFN width (0 = none) |
| `norm_type` | 8 | 0 | 2 | SW | 0 RMSNorm |
| `act` | 8 | 2 | 2 | SW | 0 SiLU-gated (SwiGLU) |
| `norm_eps` | 9 | 0 | 32 | SW | RMSNorm epsilon (DS 1e-20, Qwen 1e-6); an SU template immediate |
| `rope_pair` | 10 | 0 | 2 | SW | 0 adjacent (2i, 2i+1), 1 half (i, i + dims/2) |
| `rope_dims` | 10 | 2 | 10 | SW | Rotated dimensions per head (DS 64, Qwen 128) |
| `rope_offset` | 10 | 12 | 10 | SW | First rotated dimension (DS head_dim − 64, Qwen 0) |
| `rope_scaling` | 10 | 22 | 2 | SW | 0 none, 1 YaRN; only the host's table generator reads it |
| `rope_theta` | 11 | 0 | 32 | SW | Table generator only |
| `rope_factor` | 12 | 0 | 32 | SW | YaRN factor (0 = none); table generator only |
| `yarn_beta_fast` | 13 | 0 | 8 | SW | Table generator only |
| `yarn_beta_slow` | 13 | 8 | 8 | SW | Table generator only |
| `yarn_orig_log2` | 13 | 16 | 6 | SW | log2 of the original maximum positions; table generator only |
| `compress_rope_theta` | 14 | 0 | 32 | SW | DS compressed-KV RoPE tables; table generator only |
| `window` | 15 | 0 | 17 | SW | Sliding-window rows (0 = dense) |
| `ctx_max` | 16 | 0 | 21 | SW | Deployed context (positions) |
| `attn_scale` | 17 | 0 | 32 | SW | The golden's softmax-scale literal, FP32(head_dim^−0.5); an SU immediate, never folded |
| `swiglu_limit` | 18 | 0 | 32 | SW | SwiGLU clamp (0 = none) |
| `weight_fmt` | 19 | 0 | 3 | SW | Dense weight format |
| `kv_fmt` | 19 | 3 | 3 | SW | KV cache format |
| `act_quant` | 19 | 6 | 3 | SW | Matvec activation format (FP8 block for DS, BF16 for Qwen) |
| `scale_kind` | 19 | 9 | 3 | SW | Weight scale: 0 none, 1 per-row BF16, 2 UE8M0 block |
| `wblock` | 19 | 12 | 6 | SW | Weight block size (DS 32) |
| `expert_fmt` | 19 | 18 | 3 | SW | Expert weight format (DS FP4) |
| `n_routed` | 20 | 0 | 10 | SW | MoE routed experts |
| `n_shared` | 20 | 10 | 3 | SW | MoE shared experts |
| `moe_topk` | 20 | 13 | 4 | SW | Experts per token |
| `moe_scoring` | 20 | 17 | 2 | SW | 0 softmax, 1 sqrt(softplus) |
| `moe_norm_topk` | 20 | 19 | 1 | SW | Normalise the top-k weights |
| `routed_scaling` | 21 | 0 | 32 | SW | Routed scaling factor |
| `idx_heads` | 22 | 0 | 8 | SW | Indexer heads |
| `idx_head_dim` | 22 | 8 | 10 | SW | Indexer head dimension |
| `idx_topk` | 22 | 18 | 12 | SW | Indexer top-k |
| `cand_topk_blocks` | 23 | 0 | 12 | SW | Candidate blocks |
| `cand_block` | 23 | 12 | 6 | SW | Candidate block size |
| `cand_src_layer` | 23 | 18 | 8 | SW | Candidate source layer |
| `hc_mult` | 24 | 0 | 4 | SW | Hyper-connection copies |
| `hc_sinkhorn_iters` | 24 | 4 | 6 | SW | Sinkhorn iterations |
| `hc_eps` | 25 | 0 | 32 | SW | Sinkhorn epsilon |
| `engram_heads` | 26 | 0 | 4 | SW | Engram heads |
| `engram_head_dim` | 26 | 4 | 10 | SW | Engram head dimension |
| `engram_max_ngram` | 26 | 14 | 3 | SW | Engram n-gram order |
| `engram_layers` | 26 | 17 | 3 | SW | Engram layer count (ids in the configuration) |
| `mtp_kind` | 27 | 0 | 2 | SW | 0 none, 1 DSpark |
| `mtp_block` | 27 | 2 | 4 | SW | Draft block |
| `mtp_markov_rank` | 27 | 6 | 10 | SW | DSpark Markov rank |
| `mtp_experts` | 27 | 16 | 9 | SW | Draft routed experts |
| `mtp_topk` | 27 | 25 | 4 | SW | Draft experts per token |
| `mtp_noise_token` | 28 | 0 | 18 | SW | DSpark noise token |
| `q_lora` | 29 | 0 | 12 | SW | q LoRA rank |
| `o_lora` | 29 | 12 | 12 | SW | o LoRA rank |
| `o_groups` | 29 | 24 | 4 | SW | o groups |
| `tp_size` | 30 | 0 | 8 | SW | Dies in the tensor-parallel group |
| `cfg_sha256` | 32–39 | 0 | 256 | SW | sha256 of the model's `config.json`; binds the descriptor to one model |
| `cp_vocab` … `emb_row_bytes` | 40–48 | | | blocks | The 17 mode fields of Table 5-1 |
| `entry_ar` | 56 | 0 | 32 | CP | AR decode step: record offset in the image (16 B units) |
| `entry_verify` | 57 | 0 | 32 | CP | MTP verify pass (0 = absent) |
| `entry_draft` | 58 | 0 | 32 | CP | MTP draft pass (0 = absent) |
| `image_base` | 60 | 0 | 28 | CP | Program image base in HBM, in 4 KiB pages |
| `image_pages` | 61 | 0 | 28 | CP | Program image size, in 4 KiB pages |
| `crc32` | 63 | 0 | 32 | CP | IEEE CRC-32 of words 0–62 |

Words 31, 49–55, 59 and 62 are reserved.

---

## 7. Mapping the two target models

### 7.1 DeepSeek-V4.1-Flash: existing kernels as records

DeepSeek keeps its kernels and engines. Its program is a record stream of:

- `SIMT.RUN(pc)` for every committed OTG-1 kernel;
- the native engine operations (`FUSED.HC_PRE_NORM`, `IDX.*`, `HC.HC_MIX`, `COLL.*`, `DMA.*`) where the DS composition already uses them.

With section C at reset, every block behaves as today. The DS lowering is a re-encoding, not a re-design. Its acceptance test is identical tokens and identical per-unit outputs against the existing DS evidence (§8.2).

### 7.2 Qwen3-8B: the 28 families as unit operations

A *family* is a class of graph operations that share one implementation; Qwen3-8B's 871 graph operations per token fall into 28 families. The table shows which unit operation implements each family and whether it runs on a fused fast path or the programmable SU. The counts are operations per token.

| Family (operations per token) | Unit operation | Path |
|---|---|---|
| qkv, o, gu, down (144), head (1) | `SM.MATVEC` format 3 | Fast path (format 0, a BF16-widened image, for bring-up; bit-identical) |
| row_scale_qkv/o/gu/down (144), head_scale (1) | The consuming `SU.VOP` takes B = scale with M1 = A·B (one FP32 round-to-nearest-even multiply, the golden's rounding point) | SU; no separate operation where the consumer's first stage is free |
| prenorm (73) | `FUSED.ROW_NORM` seg 0 | Fast path (`norm_*`) |
| QK-norm (36) | `FUSED.ROW_NORM` seg 128 | Fast path |
| RoPE (36) | `SU.VOP` with `c_pair`; tables by `DMA.LOAD` at POS | Fast path (`rope_*`) |
| roundQ (36) | `SU.VOP` with `rnd` (FP8 for KV) | SU |
| attention_qk, attention_pv (72) | `ATT.QK`, `ATT.PV`, 4 lanes per KV head | Tiles |
| softmax (36) + pv_normalize (36) | FUSED softmax, `sfx_multipass` (pass 3 normalises) | Fast path |
| SwiGLU (36) | `SFU.GLU` | Fast path (`glu_*`) |
| residual (72) | Folded into the next ROW_NORM input, otherwise an `SU.VOP` add | Fast path or SU |
| all_reduce_o, all_reduce_down (72) | `COLL.ALL_REDUCE_SUM`, group of 4 | Collective |
| kv_append, kv_fence (72) | `DMA.STORE` (`kv_dense`), `DMA.FENCE` | kvwb |
| embedding (1) | `DMA.LOAD` (TOKEN · `emb_row_bytes`) + `SU.VOP` dequantisation | svc + SU |
| argmax_local, argmax_gather, argmax_merge (3) | `ARGMAX.LOCAL` + `COLL.ARGMAX_MERGE` | Fast path |
| (end of token) | `CTL.END` | — |

The 28 families run on 12 unit operations plus SU templates.

**Migrating Codex's six joined descriptors.** Codex's six SU-ROM entries (prenorm 0/4, QK 4/6, RoPE 10/6, roundQ 16/1, SwiGLU 17/2, softmax 19/23) translate mechanically: each ROM slot becomes one `SU.VOP` record, its pipeline fields go into the template and its bases go into the descriptors.

**What this supersedes.** The CP namespace `0x53550000..05`, the two-half launch coalescer and the per-family owner frames have no place in HGI-1: the sequencer dispatches SU records directly (owner decision D1). Those sources stay as history.

---

## 8. Verification

### 8.1 The simulator contract

The simulator (`tools/hgi_sim/`, new) is the arbiter between the compilers and the hardware. It must model the following.

**Inputs and outputs.** The inputs are the artifacts the die consumes: the descriptor (64 words), the program image (records), the HBM image and the doorbells. The outputs are:

- completions;
- a per-record trace: issue cycle, retire cycle, unit, and a hash of each operand and result buffer;
- an HBM and VM write log;
- fault codes.

**Functional model (bit-exact).** Each unit operation is computed by one shared **arithmetic library**, whose order functions are each pinned to an RTL bench:

- SM: per-format leaf, tc16 ring, column tree, stack pairing;
- ATT: chunk8 plus pairwise per 64-element slice;
- SU: `Machine.su1` / R-ARITH csum;
- norm, softmax (including the multipass chunk order) and SwiGLU, under every mode value;
- collective: rank-order reduction;
- argmax: lowest index.

The simulator and the golden both call this library. Nothing else is shared, so a compiler error (a wrong address, stride, wait mask or binding) shows up as a mismatch.

**Control model:**

- the CP sequencer: prefetch, predicate, `wait`, LOOP and the DYN banks;
- unit queues and STREAM credits;
- collective matching by group sequence;
- fence visibility;
- the configuration path, including every error code of §5.6 and the settle hold-off.

**Timing model (transaction-level):**

- per unit: issue rate, pipeline depth and per-operation setup cycles, from a calibration table (`hgi_sim/calibration.json`) in which every entry carries a record pin and a grade (measured or estimate);
- HBM: per-PC bandwidth, 32-byte sectors, request queue depth;
- collective: the measured endpoint latency plus a per-crossing budget.

Cycle results are pathfinding until every entry is measured. The bar is timing within ±2 % of each stage bench; exactness is never a tolerance.

**Faults.** Every fail-closed condition of the RTL (SU domain faults, non-finite FP values, a descriptor out of range, an `END` token ≥ `cp_vocab`) must produce the same fault and the same completion status in the simulator.

**Out of scope:** wires, clock crossings beyond fixed latencies, and physical faults.

**Proof obligations:**

- (a) the simulator's functional mode equals the golden bit for bit on every token of the test set;
- (b) every RTL stage bench equals the simulator's per-record buffers for the same records;
- (c) the simulator's cycles track the stage benches within tolerance, and published numbers use measured entries only.

### 8.2 Goldens

A **golden** is the bit-exact software reference that hardware and simulator must reproduce.

- **DS: unchanged.** `hdc_golden_v41` (chunk8) and the existing campaigns remain the reference. HGI-1 only adds a re-encoded program, which must reproduce the same tokens and buffers.
- **Qwen: `qwen_r25`** (new). It is the Qwen3-8B graph in r25 order, built on the arithmetic library and parameterised by the descriptor.
  - Its path bindings are those of §7.2: fast paths for norm, QK-norm, RoPE, softmax and SwiGLU.
  - The SU fallbacks are the documented alternative; binding one is a golden change.
  - Owner sign-off rests on one contract quality run in r25 order (about 2.2 GPU-hours); the INT8 per-row contract must stay within the pre-committed PPL/MMLU rule.
  - The bring-up image (format 0, BF16-widened INT8) uses the same golden bit for bit.

### 8.3 The verification ladder

Each model climbs the same four levels.

| Level | Vehicle | Pass criterion |
|---|---|---|
| L0 | The arithmetic library against each block's pinned bench vectors | Bit-exact, with every mode value covered |
| L1 | Simulator (functional) against the golden | Every token of the test set: AR at position 8,191 (Qwen), the DS reference positions |
| L2 | RTL stage benches (one stage per layer type plus the head, following the owner's "minimum component" rule) against the simulator's per-record buffers | Bit-exact, each with a negative mutant |
| L3 | Composition: simulator timing with measured entries | Published only as a measured composition |

### 8.4 Conformance tests

Every hardware fork must pass the tests in its row, in both modes.

| ID | Block | DS mode (reset) | Qwen mode |
|---|---|---|---|
| CF-0 | Configuration path | DS descriptor load causes no change. Each error code, with the active values kept. A doorbell before any load runs DS. A commit while busy is refused. Settle hold-off. | Qwen descriptor load; read-back of every section-C field |
| CF-1 | Mode-0 equivalence | A fork with its active registers at reset is equivalent to the legacy block: formal equivalence where the block is small (CP, argmax, collective owner half, kvwb), otherwise byte-identical replay of the block's committed DS vectors **and** identical cycle counts | — |
| CF-SM | `smh_front_c` format 3 | Format 0–2 vectors identical; latency bypass-matched | Format 3 output equals format 0 on the BF16-widened image, bit for bit; INT8 rows of −128, 127 and 0 |
| CF-CP | CP | The 17-bit DS token set | Ids 131,071, 131,072 and 151,935; position 2²⁰ − 1; range refusal at `cp_vocab` and `cp_ctx_max` |
| CF-ROPE | RoPE chain | Adjacent 64-tail vectors | Split-half 128 against the golden; mutant: `rope_half` = 0 must fail |
| CF-NORM | Norm engine | D5120, HC and FP8 vectors | D4096 with HC off and BF16 output; seg 128 QK-norm (32 + 8 heads); mutant: an unpadded tail |
| CF-SFX | Softmax | Sink vectors | 8 heads × 8,192 rows multipass against the golden's chunk order; T = 1, 640, 641 and 8,192 |
| CF-GLU | SwiGLU | FP8, clamp and route-weight vectors | BF16, no clamp, no route weight, 3,072 per die |
| CF-COLL | Collective | TP-96 vectors | TP4 and TP8 all-reduce (256 words) in rank order; ARGMAX_MERGE ties across shards; group isolation (no cross-group delivery) |
| CF-ARG | Argmax | 17-bit ids | Id 151,935; lowest-index tie; NaN flag |
| CF-KV | kvwb, ingest, mask | Ring, selected-row and ROWS/IKEY vectors | Linear append at pos; fence-before-read negative; cache-length mask at len − 1, len and len + 1; ingest NHD → FP8 rows |
| CF-EMB | Embedding | BF16 rows | Row 151,935; INT8 plus scale dequantisation |
| CF-SVC | KV striping | DS index-key sweep | Qwen 8K dense sweep at ≥ 90 % of die bandwidth (owner rule) |
| CF-PROG | Sequencer | DS program re-encoded: same tokens and buffers as today | Qwen layer and head records against the simulator, with `wait`, STREAM, LOOP and FENCE negatives |

---

## 9. Extensibility

### 9.1 How generality is achieved

HGI-1 is generic not because its 17 mode fields cover many models, but because it has a **programmable escape**: SU templates (a configurable vector pipeline) and `SIMT.RUN` (general OTG-1 kernels with loads, stores, branches and a tensor core). The generality review (`review_queue/iface-review.md`, 2026-10-09) mapped eleven architectures onto v0.9 and graded each operator in four tiers:

| Tier | Meaning |
|---|---|
| **F**, fast | A fused path (norm engine, `SFU.GLU`, softmax, RoPE chain, an `SM.MATVEC` format, ATT) runs it with legal mode values. |
| **T**, template | One or more `SU.VOP`, `DMA` or `SM.MATVEC` records with SU templates and data tables. Exact under its own golden; slower. |
| **K**, kernel | `SIMT.RUN` of an OTG-1 kernel (lane-wise FP32 and integer operations, register-to-address, loads and stores, branches, divide and square root, block-dot tensor core). DS does expert dispatch this way today. |
| **X** | Not expressible without a hardware or encoding change. |

### 9.2 What other architectures need (review summary)

- **Dense transformers** (Llama-3, Mistral, Phi, GPT-2/NeoX) and **MoE transformers** (Mixtral, Qwen3-MoE, DeepSeek-V3/R1, Kimi-K2, GLM-4.5, GPT-OSS, Llama-4) are expressible. Many of their operators run at tier T or K rather than F: other norm widths, LayerNorm, GELU variants, biases, router top-k and expert fetch by id. The hbm-generic plan measured the fast paths at only 4–7 % of a Qwen token, because the weight stream dominates, so this costs little.
- **Not expressible today:**
  - **Sliding-window and chunked attention** (Mistral v0.1, Gemma-2/3, GPT-OSS, Llama-4): the program cannot say where the window starts.
  - **Group sizes other than 4, 8 or 96 dies**, for example TP2 or Kimi-K2 at TP16.
  - **Gemma-3's vocabulary** (262,208), 65 tokens beyond the 18-bit token width.
  - **Llama-4 Scout at 10M context**: positions are 20 bits, capping context at 1,048,576.
- **Hybrid state-space models** (Jamba, Mamba) are out of scope: there is no softplus or log function, no recurrent-state region, and a Jamba layer state would take half the VM.
- **Assumption to confirm.** Tier K depends on the r25 die's SMs executing OTG-1 kernels, and on the loader installing new kernels. The review found the OTG-1 instruction memory in the DS cluster integration but not in the r25 SM master. If r25 has no OTG-1 core, every K cell becomes X unless indexed descriptors and a top-k operation are added (§10.3, V0 and C3b).

*Table 9-1. Capacity limits that bound generality (from the review).*

| Limit | Value | Effect |
|---|---|---|
| Token width | 18 bits: vocabulary ≤ 262,143 | Gemma-3 not expressible |
| Position width | 20 bits: 1,048,576 positions | 10M-context models capped |
| HBM per die | 144 GB (4 stacks × 36 GB) | Kimi-K2 FP8 needs TP ≥ 8 |
| Collective group | {4, 8, 96} | TP1, 2, 16, 32 illegal |
| VM | 262,144 FP32 words (1 MiB) | Single-pass softmax for heads × rows up to about 200K words |
| Softmax chunk | 640 rows per pass | Longer rows need multipass (rate only) |
| ATT tile | ≤ 16 head lanes; head_dim ≤ 1,024 in multiples of 64 | head_dim 96 pads to 128 |
| Norm engine | D ∈ {4,096, 5,120}; seg ∈ {0, 128} | Other widths run as templates |
| SFU codes | 8 of 8 used | No tanh, erf, log or softplus |
| Record header | 128 bits, 0 spare | A new unit needs a format change |

### 9.3 Lessons from other accelerators

The review compared HGI-1 with machines designed for generality: Google's TPU, Groq, Cerebras, SambaNova, Tenstorrent, AWS Trainium and GPUs. The extensible machines keep a few fast fixed engines, put all model variation in **programs and per-operation operand descriptors**, and keep one **general-purpose escape engine**. HGI-1 already has both halves (records with memory descriptors, and `SIMT.RUN`). Tenstorrent is the closest analogue: a sequencer issuing operations to fixed engines, with formats in operand descriptors and data movement as explicit operations. Fixed-function designs (one model per chip) are the pattern to avoid; each global mode bit is a small step in that direction.

### 9.4 Adding a model under v0.9

Under the current interface, a new model is added as follows:

1. Write its compiler lowering onto the existing unit operations, choosing F, T or K for each family.
2. Generate its descriptor with the encoder. If `derive()` cannot express the model (see §10.3, C9), extend `derive()`, not the hardware.
3. Build its golden on the arithmetic library with the chosen bindings.
4. Only if a fused fast path must express something that data and per-operation fields cannot, propose a new mode field under §9.5.

### 9.5 Change process and versioning (normative)

- A field is added only when a fused path cannot express a model through data or a per-operation field. The addition must come with its DS reset value and a conformance row.
- Every change bumps the minor version (the CP's version check enforces it), regenerates `spec.json` and both descriptors with the encoder, and is merged with `--check` passing.
- Encodings are never reused. A removed field's bits stay reserved.

---

## 10. Open items and proposed v1.0 changes

> **Proposed, pending owner approval.** Nothing in §10.3 is part of the v0.9 interface. The normative text of Chapters 2 to 9 is unchanged by it. Each item becomes normative only after an owner decision and a version bump under §9.5.

### 10.1 Open items carried by v0.9

These items are part of the frozen v0.9 and must be closed before v1.0.

1. **The svc KV path (high priority).** Until the striping fork (H8) lands, Qwen attention runs at about 1/32 of the HBM bandwidth. `kv_dense` reads must not target the fixed `KV_PC` path.
2. **The SM layout rule.** The row split over 32 SMs and the per-SM weight layout must be pinned from the DS image builder before the Qwen compiler writes weights. Owner: the H10 SM dispatcher, within one day.
3. **`attn_scale` literal (resolved).** Descriptor word 17 = FP32(head_dim^−0.5), matching `hdc_golden_v41` (`F(self.hd ** -0.5)`) bit for bit for head dimensions 512 and 128.
4. **DS embedding row stride.** 10,240 (BF16 × 5,120) is taken from the model shape and must be confirmed against the DS image.
5. **Physical split of the CP** (north and south halves, 16 SMs each). The specification defines one logical sequencer; work item C2 decides the split.
6. **Qwen MTP** (after the τ measurement). Fields for B, STAGES, MARKOV_EN and UNION_EN go into descriptor words 49–55 at that decision. `CTL.TOKX`, `AMAX` and `ACCEPT` are reserved for it.

### 10.2 Owner decisions recorded after the freeze

The owner approved v0.9 as the frozen interface (REVIEW_20261009, "Decisions … HGI-1 v0.9 interface"):

- **D1, approved.** The record-and-sequencer model replaces Codex's CP namespace interception and two-half coalescer. DS kernels run as `SIMT.RUN(pc)`. *Reflected in v0.9.*
- **D2, approved.** Aligned collective groups (rank = die id mod group size, rank-order reduction). *Reflected in v0.9.*
- **D3, approved, not yet applied.** Drop the softmax sink-off bit and pass a −2¹⁰⁰ sink as data. This requires a bench proving bit-identical Qwen softmax (the exponential of the sink underflows to exactly +0 in the r25 exponential unit). If that ever fails, the bit comes back. Until applied, `sfx_sink_off` remains in the encoding (proposed change C10).
- **D4, approved.** Qwen MTP fields are reserved in words 49–55 until τ is measured. *Reflected in v0.9.*
- **Work split correction.** The CP configuration path, the sequencer and configuration receiver, and the Qwen compiler are Claude streams, not Codex (Appendix A shows the v0.9 assignment).
- **Open items to pin:** the striped KV read path (first), the SM row split and weight layout, the DS embedding row stride, and the CP north/south split (§10.1).

### 10.3 Proposed v1.0 changes (generality review)

The generality review found v0.9 extensible in principle but not ready to freeze as v1.0. It proposes about ten changes, ranked by hardware cost. All but two are encoding, compiler or data changes.

| Rank | Item | Change | Hardware |
|---:|---|---|---|
| 1 | **C1** | Add the missing operations: `FUSED.SOFTMAX` (A = scores, B = sink row as data per D3, O; `param` = chunk/multipass), which §7.2 uses but the operation table omits. Document `IDX.TOPK_LOCAL` as a generic top-k (n and k from descriptors, lowest-index ties, sorted ids out) for MoE routers. | 0 |
| 2 | **C2** | SU template operand slots. `Machine.su1` reads A, B, C and **D** (the RoPE sine), writes O **and** a reduction target, and gathers through an index base. The record carries only A, B, C, O. Map the template's active sources in the order A, B, C, D, O, R, I. Without this, Qwen RoPE, every reduce-and-store template and every gather are unencodable. | 0 |
| 3 | **C3a** | Reserve header room. The header has 0 spare bits: `wait` is 12 bits for exactly 12 units. Take 4 bits from `param` (32 → 28) to make `wait` 16 bits and reserve unit codes 12–15, so a later unit is additive. | 0 |
| 4 | **C9**, **C10** | Fix `derive()`, which silently mis-derives for some models: `sfx_multipass = (window == 0)` gives Mistral v0.1 the value 0; `kv_dense = kv_heads > 1` gives MQA models the DS ring; `rope_rot_log2` truncates a 96-dim span to 64; `norm_d_units = hidden // 128` truncates GPT-OSS's 2,880; and the `cp_vocab` legal range admits 2¹⁸, which does not fit 18 bits. Apply D3: mark `sfx_sink_off` (44.0) reserved and never reuse it. | 0 |
| 5 | **C5** | RoPE pairing as data: permute the q and k output rows of W_q and W_k (and the QK-norm gains) offline so that split-half pairs become adjacent. Partial or odd spans become descriptor ranges. This removes `rope_half`, `rope_rot_log2` and the H2 fork. It changes the q·k summation order, which is allowed because the `qwen_r25` golden is new. | 0, and less |
| 6 | **C7** | Remove or merge 12 mode fields (below). | 0 or less |
| 7 | **C8** | Move section B (software-only, global, DS- and Qwen-shaped geometry) into a versioned JSON model manifest with per-layer rows, bound to the descriptor by `cfg_sha256`. Keep words 4–31 reserved. | 0 |
| 8 | **V0** | Pin the `SIMT.RUN` interface as the official escape: arguments, SM mask, instruction-memory budget (2¹⁴ words), kernel installation through `hfd_loader`, an arithmetic-library entry for kernels. Confirm that the r25 die's SMs execute OTG-1. | 0 (verification) |
| 9 | **C6** | Collective group sizes {1, 2, 4, 8, 16, 32, 64, 96}: a constant-table change in `hfd_coll`, which H6 is forking anyway. Needed for Qwen TP2 and Kimi-K2 TP16. | Tiny, open block |
| 10 | **C4** | Reserve generic window and chunk DYN codes (`WIN_N`, `WIN_START`, `CHUNK_START`, `CHUNK_N`) and section-C words 50–52 for their parameters; implement in the new sequencer when a windowed model is scheduled. | Tiny, new RTL; encoding now |

**The proposed mode-field simplification (C7).** A mode stays only when no opcode, descriptor field or data constant can express the same thing:

| Field | Proposed verdict | Replacement |
|---|---|---|
| `sfx_sink_off` | Remove (D3) | Sink row of −2¹⁰⁰ as data |
| `glu_routew_off` | Remove | C descriptor pointing at a constant 1.0 |
| `glu_clamp_off` | Remove | Clamp limit as the record immediate; FLT_MAX disables it exactly |
| `norm_hc_off` | Remove | The opcode already distinguishes `ROW_NORM` from `HC_PRE_NORM` |
| `norm_out_bf16`, `glu_out_bf16` | Merge into the O descriptor | `O.fmt` per operation |
| `emb_int8`, `emb_row_bytes` | Remove | The `DMA.LOAD` descriptor already describes the row |
| `rope_half`, `rope_rot_log2` | Remove | C5 weight permutation plus descriptor range |
| `kv_dense` | Make it an opcode distinction | Generic linear append via `DMA.STORE`; DS keeps its native op; the mask is `n_sel = POS1` |
| `coll_head_rows` | Merge into `ARGMAX.LOCAL` | Id offset = `DYN[RANK] · imm_a` per operation |
| `sfx_multipass` | Keep as a convenience, per operation | A 3-pass SU program expresses it exactly |
| `norm_d_units` | Keep, as a per-operation `param` field | Same hardware |
| `cp_vocab`, `cp_ctx_max`, `coll_group_size` | Keep | Safety range checks and genuine static configuration |

The result would leave three static fields (plus the reserved C4 window words) and per-operation fields; the H2 fork and the embedding part of H9 would disappear, and H5 would lose two of its three bits. Rule 1 (reset = DS) still holds, because DS records carry DS descriptor values.

**Deferred ("future, not now").** C3b indexed descriptors (expert fetch by id at record level), C11 token width 19 and positions beyond 20 bits, C12 arbitrary norm widths and a LayerNorm mode, C13 new SFU functions (tanh, erf, log, softplus), and C14 a fused online softmax.

**Timing note.** C5 and C7 change Qwen's mode plan, which forks H2, H5 and H9 are implementing. They should be decided before those forks land; each fork that lands first is hardware that C7 would delete. The mode-field forks for RoPE, norm output format and GLU format are paused pending that decision; KV striping, INT8 weights, the 18-bit token and the configuration path continue.

### 10.4 Editorial notes from this revision

Writing this edition surfaced points that v0.9 leaves implicit. They are listed here, not resolved, so that the v1.0 revision can settle them:

- the mapping of `wait` bits to unit codes and of `opnd` bits to A, B, C, O;
- the numeric operation codes (this document lists operations in `spec.json` order);
- the bit offsets of the SU template fields (`spec.json` gives order and widths only);
- whether a unit may begin a record before an earlier record of the same unit has completed its writes (§4.2).

The v1.0 draft (§10.5) proposes a resolution for all four.


### 10.5 HGI-1 v1.0 draft: the proposed diff against v0.9

> **Proposed, pending owner approval. Not frozen.** This section is the complete v1.0 draft written as a diff. Chapters 2–9 (v0.9) stay normative until the owner approves it.
>
> - Machine-readable draft: `results/arch/hbm_generic_iface_20261009/v1_0_draft/` (`spec.json`, `manifest_*.json`, `md_*.hex`, `descriptors.json`).
> - Encoder: `tools/hbm_generic_iface.py --draft --out|--check DIR`. Without `--draft` the encoder produces and checks v0.9 exactly as before.

**What the draft takes in:**
- the review's zero-hardware set: C1, C2, C3a, C5, C7, C8, C9, C10 and V0;
- the simulator's gaps G1–G7 and GDN-1 to GDN-6 (`tools/hgi_sim/records.py` `SPEC_GAPS`, hbm-sim.log);
- the owner's decision that **linear attention is in scope through software**.

**What it leaves out:** C4 (window/chunk) and C6 (group sizes) are encoded but are hardware items. C3b and C11–C14 stay deferred.

#### 10.5.1 Summary of changes

| # | Source | v0.9 | v1.0 draft | Hardware |
|---|---|---|---|---|
| 1 | C7, C10 | 17 static mode fields in 9 words | **3 static fields**: `cp_vocab` (40), `cp_ctx_max` (41), `coll_group_size` (46.0). The other 14 fields are retired. Their bits stay reserved forever, and setting one gives E_RESERVED. | less: fork H2 deleted; H5 and H9 shrink to per-op decode |
| 2 | C7, G5 | output formats as modes | output format = the O descriptor's `fmt` per op. It is FP8, BF16 or FP32 for `ROW_NORM` (QK-norm emits FP32 and prenorm BF16 in the same layer), and FP8 or BF16 for `GLU`. | the same logic, decoded per op |
| 3 | C5 | `rope_half`, `rope_rot_log2`, SU partner XOR dims/2 | RoPE pairing is **data**. Qwen's W_q/W_k output rows (and QK-norm gains) are permuted offline so that split-half pairs become adjacent. `c_pair` is always i XOR 1, which is DS's existing hardware. Partial or odd spans are descriptor ranges. | less (no H2) |
| 4 | C2, G2 | `opnd` 4 bits (A, B, C, O) | `opnd` 7 bits: **A, B, C, D, O, R, I** (D = the 4th source, e.g. the RoPE sine; R = the reduction destination; I = the gather index). Descriptors follow in that order. | 0 |
| 5 | C3a | `wait` 12 bits = 12 units, 0 spare | `wait` 16 bits (bit u = unit code u). Unit codes 12–15 reserved. `param` is 25 bits. | 0 |
| 6 | G1 | SUT lsbs unspecified | SUT fields are packed from bit 0 in list order: 142 bits, with lsbs in `spec.json`. | 0 |
| 7 | G3, GDN-3 | `istride` 0 means 1, so no broadcast | MDESC bit 5 **`ibcast`** = inner stride 0 (per-row scalar broadcast: softmax max and normaliser, row scales, per-head gates). | 0 |
| 8 | C1, G4 | `FUSED.SOFTMAX` used but not defined | `FUSED.SOFTMAX`: A = scores, B = sink row as data (−2¹⁰⁰ = no sink, per D3), O, `param[0]` multipass, `imm_a` = scale. `IDX.TOPK_LOCAL` is documented as a generic top-k (n and k from descriptors, lowest-index ties, sorted ids out). | 0 |
| 9 | G6 | "640-row chunks with carry-in" | The multipass carry is the **streaming csum8 binary-counter state**: the denominator equals the golden's csum8 tree exactly. The SU 3-pass fallback stays bound until CF-SFX proves the fused unit equal. | 0 (a fork requirement) |
| 10 | G7 | `CTL.END` requires A | `CTL.END` with A absent: token = the latest SIMT `RESULT` payload (today's CP rule; status 2 if there is none). DS kernel-posted tokens need no extra record. | 0 |
| 11 | C7 | `kv_dense` mode | Opcode distinction. `DMA.STORE` is the generic linear append (dense KV, GDN state); `DMA.KVWB_DS` is the DS native window ring. The cache-length mask is the attention B descriptor's `n_sel` = POS1, or the new POS_SLOT1 per verify slot. | 0 |
| 12 | C7 | `coll_head_rows`, `emb_*` modes | `ARGMAX.LOCAL` `imm_a` = id offset multiplier (global id = local + DYN[RANK]·imm_a). The embedding is a `DMA.LOAD` whose descriptor gives the row (TOKEN · row bytes, `fmt` INT8 or BF16), plus an SU dequant. | 0 |
| 13 | C7 | `norm_d_units`, `sfx_multipass` global | per-op: `ROW_NORM` `param[5:0]` d_units, `[13:6]` seg; `SOFTMAX` `param[0]`. | 0 |
| 14 | GDN-6 | one loop level | a second loop level: `CTL.LOOP param[16]` = level, DYN code L1, MDESC `l1stride`. Effective base = base + L·lstride + L1·l1stride + DYN·dyn_mul. | sequencer only |
| 15 | C4 (reserve) | DYN 8–31 = DS | DYN is 6 bits. Generic codes 0–15 (adds L1, WIN_N0/1, WIN_START0/1, CHUNK_START, CHUNK_N, POS_SLOT1); DS FULL_DYN selectors move to 16–63 in their order. Window parameters reserved in words 50–52. | encoding now; window logic when a windowed model is scheduled |
| 16 | C8 | section B (words 4–31) in the descriptor | Moved to a versioned **model manifest** (JSON, one row per layer: mixer kind, heads, window, RoPE span and pairing-in-weights, compress ratio, Engram, FFN kind, norm). Words 2–31 are reserved. Words 32–39 = sha256 of the manifest. | 0 |
| 17 | C9 | `derive()` mis-derives | Moot for the removed fields. `cp_vocab` legal ≤ 2¹⁸ − 1. Group sizes {1, 2, 4, 8, 16, 32, 64, 96} (the C6 legal set; the hardware table is H6's). | 0 / tiny |
| 18 | V0 | `SIMT.RUN` informal | ABI pinned (§10.5.4). | verification |
| 19 | editorial | implicit | op code = index in `ops[unit]`; same-unit order: a unit starts a record only after the previous record of the same unit has made its writes visible to that unit. | 0 |

Rule 1 (reset = DS) still holds. The three remaining fields reset to DS, and DS records carry DS's own descriptor values (FP8 output formats, sink rows, clamp 10.0, route weights, D5120).

#### 10.5.2 Header (UOP, 128 bits), draft

| Bits | Field | Meaning |
|---|---|---|
| 127:124 | `unit` | 0 CTL, 1 SM, 2 SU, 3 SFU, 4 FUSED, 5 ATT, 6 COLL, 7 ARGMAX, 8 DMA, 9 IDX, 10 HC, 11 SIMT, 12–15 reserved |
| 123:118 | `op` | index in `ops[unit]` |
| 117:102 | `wait` | drain mask, bit u = unit u |
| 101:100 | `pred` | as v0.9 |
| 99:93 | `opnd` | A, B, C, D, O, R, I present (bit 0 = A) |
| 92 | `tmpl` | an SU template follows |
| 91:89 | `slot` | DYN bank |
| 88:64 | `param` | per op (`spec.json` `uop.param`) |
| 63:32, 31:0 | `imm_a`, `imm_b` | immediates |

**MDESC (256 bits), draft:**

| Bits | Field |
|---|---|
| 1:0 | `space` |
| 4:2 | `fmt` |
| 5 | **`ibcast`** |
| 47:8 | `base` |
| 67:48 | `n` |
| 87:68 | `m` |
| 119:88 | `stride` |
| 135:120 | `istride` |
| 167:136 | `lstride` |
| 173:168 | `dyn_sel` (6 bits) |
| 200:174 | `dyn_mul` |
| 206:201 | `n_sel` (6 bits) |
| 238:207 | **`l1stride`** |

Bits 7:6 and 255:239 are reserved.

#### 10.5.3 Model descriptor, draft

| Words | Content |
|---|---|
| 0–1 | header, version **1.0** |
| 2–31 | reserved (section B → manifest) |
| 32–39 | manifest sha256 |
| 40 | `cp_vocab` (18) |
| 41 | `cp_ctx_max` (21) |
| 42–45, 47–48 | retired v0.9 bits, reserved forever |
| 46 [7:0] | `coll_group_size` (kept at its v0.9 position) |
| 49, 53–55 | MTP (D4) |
| 50–52 | C4 window/chunk parameters |
| 56–61 | program entries and image, as v0.9 |
| 63 | CRC |

The CP's checks and error codes are unchanged. A retired bit that is set now gives E_RESERVED. The encoder's negative cases cover this, a group size of 12 (E_RANGE) and a vocabulary of 2¹⁸.

#### 10.5.4 `SIMT.RUN` ABI (V0)

- **Arguments:**
  - `param[13:0]` = entry PC (instruction memory 2¹⁴ × 64-bit words); `imm_a` = SM mask.
  - Uniform registers: UR0 token, UR1 position, UR2 SM id, UR3 die id (as today), UR4 = `imm_b`.
  - UR5 onward = the effective bases of the present descriptors, in `opnd` order (at most 7, up to UR11). UR15 stays the stride register.
- **Completion:** the kernel's done and fault signals; its `RESULT` payload feeds `CTL.END` with A absent (G7).
- **Installation:** kernels are installed into the instruction memory through `hfd_loader` at model load (load-sequence step 1). The image manifest lists entry PCs.
- **Exactness:** the arithmetic library has an OTG-1 entry (`tools/gpu_sys/isa.py` semantics), so the golden can bind a kernel.
- **Open verification (owner of H10-SM):** confirm that the r25 die's SM elements execute OTG-1. If they do not, the tier-K escape collapses and C3b (indexed descriptors) moves forward.

#### 10.5.5 Linear attention through software (owner decision)

The owner put linear-attention layers (Gated DeltaNet, Qwen3-Next style) in scope as **programs on the existing engines**, with no new unit.

The simulator lowered one GDN decode layer (Qwen3-Next dimensions, TP4) to 75 records a die. It is bit-exact against the golden for all nine families on 4 dies, and the golden matches transformers to an rms relative error of 5.8e-7. Its rate figures are estimates (hbm-sim.log).

The draft fixes the conventions it needs:

| Gap | Convention |
|---|---|
| GDN-1 (FP32 state path) | The recurrent state is FP32 and never passes through ATT, whose rows are FP8/BF16. S·k and S·q are `SU.VOP` reductions; the state is loaded by `DMA.LOAD`, updated by SU templates, and written back by `DMA.STORE`. |
| GDN-2 (softplus) | An SU template sequence under its own golden. No SFU code (C13 stays deferred). |
| GDN-3 (per-head scalars) | `ibcast` (row 7 of §10.5.1). |
| GDN-4 (transposed state) | The state is stored **transposed**, `[dv][dk]` row-major per head, so the SU's inner-index reduction computes S·k. The manifest records the layout. |
| GDN-5 (region) | New memory-map region **STATE**: per layer, per local head, the FP32 state (dk·dv·4 B) and the FP32 conv ring (`[conv_k − 1][channels]`). Base = STATE + layer · layer_bytes (`lstride`). STATE is not position-indexed, so the dead-row rollback invariant does not hold: **GDN + MTP needs a per-slot state snapshot** (open; not in v1.0). |
| GDN-6 (per-head loops) | The second loop level (row 14 of §10.5.1). One record per head-family replays over the local heads instead of 32 records. |

Manifest mixer kind `gated_deltanet` carries: heads (k, v), head dims, conv kernel, gate and state formats, and the layer order.

#### 10.5.6 Verification and work-plan impact

- **New conformance rows:**
  - **CF-BCAST:** `ibcast` per-row scalar, plus a mutant that reads inner stride 1.
  - **CF-OFMT:** `ROW_NORM` FP32 / BF16 / FP8 in one program.
  - **CF-SFX2:** csum8 carry equality, T = 640, 641, 1,280 and 8,192.
  - **CF-END2:** a SIMT-posted token.
  - **CF-LOOP2:** two-level loop, `l1stride` and L1.
  - **CF-GDN:** state round trip in the transposed layout, conv-ring wrap, per-head loop, and a GQA-map mutant.
  - **CF-0:** retired-bit negatives.
- **Forks:**
  - H2 (RoPE modes) is **cancelled**. Qwen RoPE becomes an offline weight permutation plus the DS `c_pair`.
  - H3 (norm), H4 (softmax) and H5 (GLU) read per-op fields instead of mode words.
  - H6 needs only `coll_group_size` (C6 table).
  - H9 keeps the linear append (`DMA.STORE`) and drops the `emb_*` and `kv_dense` decode.
  - C1–C3 (CP config path, sequencer, receiver) shrink to 3 words.
- **Simulator migration:** `records.py`'s provisional readings move to the draft:
  - `param` bits 0/1 → `opnd` D/R bits;
  - `istride` 0xFFFF → `ibcast`;
  - `CTL.END` without A.
- **Golden:** `qwen_r25` takes the permuted-RoPE summation order (C5). This is allowed because that golden is new; the quality run covers it.
- **Owner decisions needed:**
  1. approve or amend the draft as a whole;
  2. C5 in particular, which cancels H2;
  3. the GDN + MTP snapshot question, if linear-attention models will run with MTP.

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **AR** | Autoregressive decode: one new token per step. |
| **ARGMAX** | Unit 7: the local argmax over this die's logit shard. |
| **ATT** | Unit 5: the attention tiles, computing QK scores and PV products over KV rows read from HBM. |
| **BF16** | 16-bit brain floating point (8-bit exponent, 7-bit mantissa). |
| **Block-dot** | A dot product over blocks of low-precision values that share one scale (FP8 or FP4 with UE8M0 block scales in DS). |
| **chunk8** | The golden's summation order for attention dot products: chunks of 8, then pairwise. |
| **CMDPROC, CP** | The command processor (`hfd_cmdproc`): the in-order sequencer that fetches and dispatches records and owns the doorbell and configuration path. |
| **COLL** | Unit 6: the cross-die collective engine (all-reduce, all-gather, top-k merge, argmax merge). |
| **Completion** | The record the CP returns to the host at `CTL.END`: the token, position, job, status and cycle count. |
| **CRC-32** | The IEEE CRC-32 checksum over descriptor words 0–62, stored in word 63. |
| **CTL** | Unit 0: control operations executed by the CP itself. |
| **DMA** | Unit 8: row moves between HBM and VM, the KV append and the HBM fence. |
| **Doorbell** | The host's start command for one token: previous token, position, job id, generation, entry point and column count. |
| **DS** | DeepSeek-V4.1-Flash, the reference model whose behaviour is the reset state. |
| **DSpark** | DeepSeek-V4.1's built-in multi-token prediction (draft) scheme. |
| **DYN** | Small per-token integers (POS, POS1, TOKEN, L, RANK, SLOT, …) computed by the CP at the doorbell and used in address computation. |
| **Engram** | A DeepSeek-V4.1 operator family (hashed n-gram memory lookup). DS only. |
| **Entry point** | A record offset in the program image where a pass starts (AR, verify, draft). |
| **Family** | A class of graph operations that share one implementation, for example "prenorm" or "row_scale_qkv". |
| **Fast path** | A fused hardware datapath for a family (norm engine, SwiGLU chain, softmax, RoPE chain). |
| **FENCE** | `CTL.FENCE` or `DMA.FENCE`: waits until posted HBM writes are visible. |
| **FP8E4M3, FP4E2M1, UE8M0** | 8-bit float (4-bit exponent, 3-bit mantissa); 4-bit float (2-bit exponent, 1-bit mantissa); 8-bit unsigned power-of-two scale. |
| **FUSED** | Unit 4: the norm engine and fused SU chains, including softmax. |
| **GQA** | Grouped-query attention: several query heads share one KV head (4 per KV head for Qwen3-8B). |
| **Golden** | The bit-exact software reference model (`hdc_golden_v41` for DS, `qwen_r25` for Qwen). |
| **HBM** | High-bandwidth memory attached to the die: 144 GB per die in 4 stacks. |
| **HC** | Hyper-connections: DeepSeek-V4.1's multi-copy residual mixing (with Sinkhorn normalisation); unit 10. |
| **HGI-1** | HBM Generic Interface, version 1: this specification. |
| **IDX** | Unit 9: the DeepSeek indexer and top-k selection engines. |
| **Image** | The program records stored in HBM, located by `image_base` and `image_pages`. |
| **INT8 row scale** | Qwen's weight format: signed 8-bit codes with one BF16 scale per output row. |
| **KV cache** | The stored key and value rows of earlier positions, in HBM. |
| **L** | The loop counter of `CTL.LOOP`, also DYN code 4. |
| **LPH, NVMAX** | Softmax-unit capacity parameters; NVMAX·LPH = 640 rows per pass, NVMAX = 40. |
| **MD** | The model descriptor: 64 words that identify the model and set the hardware modes. |
| **MDESC** | Memory descriptor: the 256-bit operand description in a record (space, format, base, counts, strides, DYN selection). |
| **Mode field** | One of the 17 static hardware configuration fields in descriptor section C. |
| **MTP** | Multi-token prediction (speculative decoding with draft and verify passes). |
| **OTG-1** | The SIMT instruction set of DeepSeek's general-purpose kernels (`tools/gpu_sys/isa.py`). |
| **PC** | HBM pseudo-channel; a die's KV sweeps must stripe over all 32. |
| **POS, POS1** | The token's position, and position + 1 (the number of valid KV rows). |
| **Quasi-static** | Changed only while the die is idle, so it can be treated as a constant for timing. |
| **r25** | The current revision of the HBM accelerator die. |
| **Rank** | A die's index within its collective group: `die_id mod group_size`. |
| **Record** | One unit operation in a program: header, optional SU template and memory descriptors. |
| **Reset value** | A mode register's value before any descriptor load; equal to DS behaviour. |
| **RoPE** | Rotary position embedding: pairs of query/key elements rotated by position-dependent angles. |
| **R-ARITH** | The golden's reduction-order rule: products are taken in K order and combined by the chunked sum (csum). |
| **SFU** | Unit 3: the fused SwiGLU chain. (Inside an SU template, `sfu` is also the stage that applies exp, rsqrt, sigmoid and other special functions.) |
| **SIMT, SIMT.RUN** | Unit 11 and its operation: launches an existing OTG-1 kernel on a mask of SMs and waits for it. The general-purpose escape of the interface. |
| **Slot** | A verify column; each slot has its own DYN bank. |
| **SM** | Unit 1: the 32 matrix-vector engines per die that stream weights from HBM. |
| **SPMD** | Single program, multiple data: every die of a group runs the same program on its own shard. |
| **STREAM** | A hardware FIFO with credit flow control joining a fixed producer and consumer. |
| **SU** | Unit 2: the programmable vector pipeline configured by an SU template. |
| **SUT** | SU template: the 256-bit configuration of the SU pipeline in a record. |
| **svc** | The HBM service layer that maps sectors to stacks and pseudo-channels. |
| **τ (tau)** | The measured mean number of tokens accepted per MTP verify step. |
| **tc16 ring** | A stage of the SM's accumulation order in the smh arithmetic (with the column tree and stack pairing). |
| **TP** | Tensor parallelism: splitting each layer's matrices over the dies of a group. |
| **UOP** | The 128-bit record header. |
| **Verify pass** | The MTP pass that checks several drafted positions in one sweep. |
| **VM** | Vector memory: the die's 262,144-word FP32 scratch for activations, allocated by the compiler. |
| **`wait` mask** | Header field naming the units that must drain before a record issues. |
| **YaRN** | A RoPE context-extension scheme; only the host's table generator implements it. |

---

## Appendix A. Parallel work breakdown (v0.9)

Everything below starts from v0.9. Arrows are hard dependencies only. Owner assignments are as written at the v0.9 freeze; the owner later moved C1–C3 and P1 to Claude streams (§10.2).

| ID | Work | Owner (at v0.9) | Depends on | First deliverable |
|---|---|---|---|---|
| I0 | This specification and the encoder (`tools/hbm_generic_iface.py`) | Claude hbm-iface | — | Done (v0.9) |
| C1 | CP fork: CFG window, configuration-bus master, CF-0 checks, token width 18, `cp_vocab` and `cp_ctx_max` registers | Codex (cmdproc18 side) | I0 | CF-0 + CF-CP bench |
| C2 | CP sequencer: record fetch from HBM, prefetch ring, `wait`, predicate, LOOP, DYN banks, unit-queue dispatch, SIMT.RUN | Codex (cmdproc18 side) | I0 | CF-PROG on a 10-record smoke test |
| C3 | Configuration-bus receiver (one small module, instanced per block) | Codex, with C1 | I0 | CF-1 for the receiver |
| H1 | SM `smh_front_c` format 3 (in flight, child qwen_r25_fmt3) | Claude | — | CF-SM |
| H2 | RoPE `rope_*` in the q/kv chains and the SU `c_pair` | Claude hbm-su | C3 | CF-ROPE |
| H3 | Norm engine `norm_*` plus the per-operation segment | Claude hbm-su | C3 | CF-NORM |
| H4 | Softmax `sfx_*` | Claude hbm-su | C3 | CF-SFX |
| H5 | SwiGLU `glu_*` | Claude hbm-su | C3 | CF-GLU |
| H6 | Collective group and head rows, 18-bit select | Claude hbm-coll (Codex's qwen-r25-collective branch is input) | C3 | CF-COLL |
| H7 | argmax_m index width 18 | Claude (small) | — | CF-ARG |
| H8 | svc PC striping plus posted-write merge | Claude hbm-svc (T3) | — | CF-SVC |
| H9 | kvwb, ingest and causal mask `kv_dense`; embedding `emb_*` | Claude hbm-kv | C3 | CF-KV, CF-EMB |
| H10 | Unit dispatchers (record → native ports) for SM, SU, FUSED, ATT, ARGMAX, COLL, DMA | Claude, each block owner (H1–H9) with its block | C2 encodings | Per-unit CF-PROG slice |
| S1 | `hgi_sim` functional: arithmetic library, sequencer, units | Claude hgi-sim | I0 | L1 on a Qwen layer |
| S2 | `hgi_sim` timing and calibration table | Claude hgi-sim | S1, stage benches | L3 composition |
| G1 | `qwen_r25` golden on the arithmetic library | Claude qwen-golden | S1 library | L1 |
| G2 | Qwen r25-order quality run (owner sign-off) | Claude quality | G1 | PASS/FAIL record |
| P1 | Qwen compiler: the 28 families → records, KV/embedding/head layout, TP4 images, the six SU-ROM migrations | Codex | I0 (encoder), S1 to run | L1 PASS against G1 |
| P2 | DS lowering: committed kernels and native operations → records | Claude ds-control | I0, C2 | CF-PROG DS |
| V1 | Conformance harness (CF-*), vectors from S1 | Claude hgi-sim | S1 | CF tables green |
| M1 | uarch model / `token_path_export` `qwen_hbm` (hbm-generic W1) | Claude | — | Priced composition |

The critical path is I0 → S1 → G1 → P1 (L1) → stage benches (L2) → S2 (L3). The hardware forks H1–H9 depend only on I0 and the configuration receiver (C3), so they run fully in parallel with the software.

## Appendix B. Sources

- The approved block inventory and parameter list of the hbm-generic plan (`results/arch/hbm_generic_20261009/PLAN.md`, branch claude/hbm-generic-20261009, 01f643326; REVIEW_20261009 addendum).
- The Qwen-on-r25 study (`results/arch/qwen_on_r25_20261008/PLAN.md`) and its TP4 lowering (`tools/qwen_r25_decode_program.py`).
- The coverage ledgers T3 and T4.
- Codex's family inventory: 871 graph operations, 28 families, 22 without a producer.
- The existing r25 block ports: the `hfd_cmdproc` LAUNCH/END list, the `smh` operation port with `op_fmt`, the SU operation set of `tools/hdc_isa_v41.py`, `ot_dshbm_argmax`, `ot_dsrom_su_softmax`, `ot_hbm_rope_table`.
- The generality review `review_queue/iface-review.md` and the owner decisions in REVIEW_20261009 (D1–D4).
