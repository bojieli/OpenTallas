# Model packet: mixed dense/attention SVG (no RTL implementation)

Root decision is required before implementing this proposal. The existing full-64-row KV8/KV4 receipts, compiler defaults and RTL are unchanged. The model is `attention_mixed_model.py`, exposed as `uarch_model.hbm_attention_mixed_context_model()`.

## Preferred descriptor contract

Use the **existing descriptor mode bit197** as the attention class, rather than allocate a redundant bit200. Descriptor[197:195] already carries the full three-bit SM mode. The actual SM frontend defines attention as command mode[2]; modes4/6/7 are attention and modes0/1/2 are dense (mode3 is illegal). Attention descriptors therefore write mode4 for QK, mode6 for KV8 PV or mode7 for KV4 PV, while retaining mrel=0 and fl=0. The literal programme command words remain unchanged. The compiler verifies that every nonzero magic command in a programme has the descriptor's class and rejects a programme mixing dense and attention words. A zero command is idle and does not need a class comparison.

The SVG issuer captures bit197 with the descriptor and adds it as the most significant bit of the existing start/go queue entry. Four-entry S/G queues grow110→111 bits at LB=2; `s_ent` also grows one bit. A/P stay200 bits. The descriptor SRAM, ingress word, descriptor count, programme SRAM and programme payload stay unchanged. The reserved check remains [231:200]==0. The existing full mode field in XC stays unchanged, and XC needs neither a new context bit nor a reserved-check change.

The explicit-bit200 fallback is modeled for root review: A/P grow200→201, reserved checks in **both** SVG and XC become [231:201]==0, and the compiler must validate agreement between bit200 and mode class. It costs two extra A/P FF bits and duplicates semantic state. Everything below uses the same context47 shape under either option.

## Context and command association

SVG context grows46→47; bit46 is attention, and the lower46 bits keep exactly their existing positions. The issuer extracts the class from the **head of the GO queue**, never from the current descriptor, A/P stages, current run, IDs broadcast or a live mode wire. The launch context is captured with the programme and travels with its words. SVG group/feed connections and application `start_ctx`, `wctx` and banked-core XW must all widen explicitly. XC keeps XW5.

Banked calendar token width is62+XW:108→109 bits. Its fields are PC[10:0], ordinal[42:11], ctx[89:43], iteration[105:90], last_iteration[106], last_word[107], valid[108]. Upper fields must use parameterized offsets. All three four-slot token rings widen. Four-bit slicing pads the109-bit token to112, versus108 previously: each ring allocates16 additional payload FFs and two phase FFs. Three rings cost54 allocated FFs; context/input/output capture copies cost eight more. The total is **62 allocated source FFs /20 semantic live bits**, before mapped optimization. No new macro is required. Exact XW47 behavior and mapped census remain gates.

The class joins the command envelope at the functional R stage and follows the same word to C. PREL=0 selects the R-associated class; PREL=1 selects the C-associated class. The existing native-cache command capture envelope widens83→84 internally across d1/d2. The extra bit must share the actual command envelope, with its valid/reset ownership; no separate long flag shift chain is introduced. External SM command remains83 bits and packet remains1099 bits. Reset/invalid command tokens clear class validity; format injection uses the injected word's class. Initial attention lowering keeps fl=0, loops=1, lstep=0 and row_off=0.

The dense checker receives its normal83-bit command except bit25 is masked when the **aligned word's class is attention**. Packet-valid and packet-tag checks always remain active. The external SM command is never masked. Three descriptors dense→attention→dense, including idle, retire and native tails, are the minimum coexistence vehicle. A live-descriptor selection, stale class, swapped class and misaligned class must each have a committed fail witness.

Preferred allocated source estimate: issuer queue/s_ent9 + banked context62 + command-associated R/C/d1/d2 bits4 = **75 FF bits per SVG**. Bit200 fallback costs77. These are source counts, not mapped area/timing claims. Existing physical native frontend control/reset audits remain OPEN. Added context/token wires stay in existing registered lanes; fanout, reset copies, reach and clock must be measured with the new width. The flag only selects one dense-valid check and must not become a wide control broadcast.

## Compiler timing contract

Proposed attention API additions are `native_padding=0`, `command_extra=0`, `calendar_extra=0`, and `programme_done_extra=0`, with one profile constructor deriving them from actual instantiated hardware. Default zero preserves the existing proof's event images, GO slots, X writes and output windows byte for byte. Profile arguments alone must not claim that physical native hardware was selected.

| Profile | Read admission reference | Physical READ | External command/packet | Done extra | Residual command tail | Native prefetch padding |
|---|---:|---:|---:|---:|---:|---:|
| Storage-only proof |7|G+6|G+7|0|0|0|
| Native landing/return/cache-safe |7|G+6|G+9|0|2|19|
| Above + banked calendar |7|G+8|G+11|2|2|19|

The7-edge **read-admission calibration is a compiler reference**, not the physical READ pin latency. Native prefetch padding19 is8 landing +7 regional return +4 cache OPEN/closure allowance. Cache-safe adds two command-only edges. Banked calendar adds two READ **and** command edges; its done moves exactly two edges, so residual command-only tail remains two. There are no four extra residual tail edges. XC must mirror both the calendar delay and the command-only alignment delay; otherwise the composed192-bit SM command is invalid.

Let `F` be the legacy first-word reference, `i` a programme word ordinal and `rc0` the issuer run origin. Keep GO = F-rc0-7. Physical READ is F-1+calendar_extra+i. Actual SM command is F+command_extra+i, where command_extra is2 for cache-safe or4 with cache-safe+banked. Actual last command includes that same total command_extra. Add native_padding to admission/fetch margins separately; never subtract command_extra from GO to regain the original command edge. Such compensation would spend the cache readiness margin.

The existing attention proof uses F=rc0+FIRST_GO+8 for its earliest reference, hence the first GO is FIRST_GO+1. Preserve this historical one-edge bias under default arguments rather than silently replacing it with the matvec compiler's first-GO expression. Every subsequent op schedules against the previous **actual** command/result tail and actual X-store ownership. Retain source-relative external X writes unless a separately modeled loader constraint requires a shift; the whole command delay makes them earlier relative to consume, not later. Output exactness windows follow actual command/result timing. Queue/busy spacing includes the banked completion delay and the residual command-only tail; the final drain includes only the residual beyond the actual programme done.

`req_lead=8` remains an observational request lead. `pread=consume-3` remains the probability-store read. Neither is a cache read. Do not alter those fields or their intra-calendar offsets: moving the complete command calendar preserves them. Descriptor mode changes metadata only; no extra programme word, descriptor, ingress row, HBM byte or packet is needed for coexistence.

Current hardware flags contributing to the profile are SMB_NATIVE_LANDING, SMB_NATIVE_RETURN and SMB_NATIVE_CACHE_SAFE. The future banked calendar selection must bind the actual new core/application source and its matching XC alignment; it is not yet an existing attention runner flag. Each receipt should record those physical selections, the derived timing profile and the frozen source hashes.

## Source freshness and review gates

Canonical issuer825607a54 is byte-identical at main944bbb859: SHA256 `6acb3e9d66d70ceb211c86a317868e10bb15716787fdf9b3815a08b57d407d07`. This model preserves ID_COHORT=1, the16-bit run cohort, reset/run freshness clear, layer/cohort checks, once-per-run ID acceptance, and fixed routed-slot faulting. It does not replace that source with the old issuer used by the historical attention receipt. Attention descriptors have id_sel=0; mixed routed descriptors still require the actual current cohort after run starts and before their fixed deadline. Semantic context is descriptor metadata and cannot reuse or override ID freshness state.

Root should approve either mode197 or explicit200 before source edits. The implementation should be opt-in so the historical global ATTENTION=1 pure-attention proof remains reproducible; the new mixed path takes class from context and does not force global ATTENTION=1. Adoption then needs XW47 core/app exactness+census, alternating dense/attention RTL exactness and mutants, matching XC command alignment, native frontend/reset/physical audits, mixed die writer/descriptor composition, and production throughput pricing. No gate or RTL change is authorized by this model packet itself.
