# KV-EMB2 (K.STA.EMB): allocation-owned embedding fill start, KV side

## Decision: no D2D PREP codec; tap the HOST kind-12 CONTEXT record on the KV die

The allocation event is born on the **KV die**, so it never has to cross the D2D link:

- the allocator `ot_qwen_tp8_token_epoch_allocator[_mu]` sits in `qkd_host_lifecycle_collected[_mu]`, which sits in the
  KV-die HOST root `qkd_host_root_admission` / `qkd_host_root_pt`. The prompt scheduler (pb_q) and the cohort sit there too.
- the full owner O61 = {gen2, TAG59 = {epoch16, stage 0, token18, position13, segment 0}} already leaves the HOST on the
  compiled port-1 **kind-12 CONTEXT** record (`qkd_host_native_context_tx`: DATA[58:0] TAG59, DATA[60:59] gen, header
  epoch == TAG epoch).
- the compute die decodes that same record into its expected identity (`qfd_host_native_context_rx` host_tag / host_epoch).

The simplest exact static design therefore needs no transport at all. Taking the same record on both dies pairs the two
ends by construction:

- `qkd_embedding_ctx_start` (new) takes the die fork of the HOST record face: {record_tx_v, record_tx_observed_v,
  record_tx[547:512], record_tx[60:0]} = 99 bits.
- a valid kind-12 record whose owner is new gives one registered start pulse, with that owner's token and epoch.
- a repeated owner starts nothing (the port re-sends the request it holds on every token run).
- a missing context leaves the row unstaged, so row_tx faults at the header slot. This fails closed and the slot never
  moves.
- `qkd_kvs_emb_ctx` is the reference body of the kvs_emb tile for the MU build (`OT_KV_EMB_CTX=1`). It drops `d2d__svc`
  and drives join4_cal start, row_tx fill_*, and px_st / px_tok / px_tep (the fan root) from that one register. It also
  exports emb_fault (ctx | join | row_tx).
- RESULT (kind 15) keeps its real meaning (HOST POST / CQ / health) and **never starts a fill**.

This supersedes the following Codex ce631fc1b candidates. None of them are needed:

- the kind-15 C->K PREP subtype with a new PREP-only reservation.
- the paired TX/RX codec and its calendar analysis.
- the 27-bit row-header widening.
- the 31,752-bit 128-return widening.
- the 337+62N metadata floor.

Why they are not needed: the row header keeps {token18, epoch16}. Epoch16 = {seq14, user2} is unique per allocation
inside the allocator's wrap fence, and the returns already carry token/epoch, which row_tx checks per word.

## NULL inputs, filled from source

| Input | Value |
|---|---|
| PHY per-request bound | Not needed for the start transport (it does not cross the D2D). The fill itself keeps the selected fixed join4_cal calendar (RETIME1 reserved latest return per PC, relative to start). It is unchanged. |
| Installed E / prologue | The compute-side E expectation = host_tag of the same kind-12 record. Static order: context slot -> fork ages + 2 (tap + out) -> join calendar `last` -> row resident -> header slot (first_emb_send - 1). |
| Final scale / drain / release | The row owner lives in row_tx from start until the 65th record (n==64 clears armed). A new owner before MIN_GAP=66 edges faults in ctx_start, and before the 65th send it faults in row_tx (armed). The next start is the next token run's new context, at least one token period later. Join returns are bounded by the calendar `last`. |
| Codex RESULT-trigger defects | Removed: wrong prompt token, no first-token fill, old epoch. |

## Price

- **Edges.** The start is 2 edges after the record reaches the kvs_emb face (face capture + output register), plus the die
  fork relay ages of the HOST record bus.
- **Calendar constraint (compiler, d2d_link_calendar.py).** The token-run kind-12 CONTEXT slot that carries step n+1 must
  come after the HOST holds the step n+1 request:
  - prompt tokens: the request is ready early.
  - generated tokens: no earlier than RESULT(n) at the KV HOST, plus the HOST request latency (NULL: HOST lane to measure).

  The compute face already needs this same constraint for its expected identity. The fill budget becomes
  first_emb_send - (ctx slot + fork + 2), which must be >= join `last` + 1. The current PREC_K0 = 3 sits before RESULT
  arrives, so a generated-token run has to move it. This is a compiler item.
- **State and pins.** +207 flops (no SRAM); 0 header bits; 0 return bits. kvs_emb pins: -174 (svc) +99 (ctx) +2
  (px_st, emb_fault).
- **Die.** +99-bit kv_oneway fork of the HOST record bus to kvs_emb. The fan root emb_start moves from the hsvc svc[24]
  branch to px_st. The join4_cal / fan root start ages must be recompiled together (kvjc3_pc_chain.py).

## Safe-design checklist (qkd_embedding_ctx_start)

| # | Item | Result |
|---|---|---|
| 1 | Pins | PASS: every input is captured at the face and every output is registered. Reset is async rst_n, the same as join4_cal. Lint SYNCASYNCNET with row_tx's rst_q pin flop: the kit reset_landing check decides. |
| 2 | Reach | PASS: tile-local. |
| 3 | Fanout | PASS: <= 4 loads per output bit, <= ~4 per owner bit. |
| 4 | Depth | PASS: 61-bit equality + 18-bit range compare, ~8 levels. |
| 5 | Storage | PASS: 207 flops. |
| 6 | Floorplan | Kit re-harden of kvs_emb (die-chain owner). |
| 7 | Clock | ck only. |
| 8 | Schedule | PASS: static, +2 edges priced above. |

## Bench (Verilator 5.050, fleet ot-epyc4)

Run with `run.sh MUT`. Bench sources: the SRAM model, qkd_embedding_row_tx.sv, qkd_embedding_ctx_start.sv and
test/tb_qkd_embedding_ctx_start.sv.

`m0.log`: **PASS**. It covers:
- prompt [7, 11, 11] plus a user-1 generated token: 4 fills, and every header {token, epoch} equals the context owner.
- no fill on a repeated owner, a kind-13 AUTH record or an observed-0 slot.
- 4 negatives faulted: header epoch, stage, token range, two owners inside one row window.

Mutants (fail regex `^FAIL`, witnesses committed):

| Log | Mutant | What fails |
|---|---|---|
| m1 | no repeated-owner suppression | start counts + row_tx fault |
| m2 | token taken from the position field | header/token mismatch |
| m3 | no header-epoch check | negative not faulted |
| m4 | no kind check | AUTH record starts a fill |

`lint.sh`: qkd_kvs_emb_ctx with the real join4_cal / row_tx elaborates. Exit 0, with the SYNCASYNCNET note only.
