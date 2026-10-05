# Qwen async collective: pipelined scoreboard (SB_PIPE=1), one bounded attempt (2026-10-04)

**Verdict: REJECT.** The design is exact and keeps the gain (+7.33% per user), but it does not close SS setup at 1.2 GHz in context. After full GRT repair the WNS is -87.9 ps. Under the owner rule this is the final verdict, with no further redesign.

## The change
Source: `d4b597eab` on `claude/qwen-async-seqfix-20261004`. The new parameter is `ot_qwen_tp_seq_async_w12` `SB_PIPE`, and its default of 0 keeps the original logic.

`SB_PIPE=1` splits the scoreboard set into three steps:
1. A tap register on the 174 µm ME-to-sequencer hop.
2. The per-port `addr - vw` subtract and range check, registered as two 16-way one-hots.
3. An AND-OR of the one-hots into `lw`.

A mark is only ever delayed (by 2 cycles), never set early.

## Exactness and gain
| | one-stream | SB_PIPE=0 | SB_PIPE=1 |
|---|---|---|---|
| Full token, ideal memory, layer-parallel (exact, poison check passes) | 144,522 | 134,514 | **134,658** (+4 cycles/layer) |
| REAL_MEM E+L0-L2 at P0 (X and K/V exact) | 14,273 | 12,240 | **12,244** |
| REAL_MEM E+L0-L2 at P255 (X and K/V exact) | 13,874 | 12,687 | **12,701** |

- **Per-user gain:** 144,522 / 134,658 = **+7.33%**, which is 8,911 tok/s at 1.2 GHz.
- **Verilator gate:** passes (`async_coll_verilator_gate_sbpipe1.json`).

## Physical, in context
**Setup.** After GRT repair, SS setup WNS is **-87.9 ps** with 164 failing endpoints. The setup repair stalls. The same recipe closes for ASYNC_COLL=0 (a0h: +17.1 ps).
- The scoreboard set itself is no longer the limiter: `s1_v` is at -31 ps.
- The new worst path is the scoreboard *read*: `rd_k` → 256:1 `lw[rd_k]` mux → `word_ok`/`rd_go` → `rd_k+1`.
- The added area also pushes existing paths past the limit. `seg` is at -49 ps and the head argmax (`best_v`, `next_val`, `best_i`) at -42 to -43 ps. Both closed in a0h.

**Detailed route.** It was stopped at iteration 13, with 1,215 DRC violations remaining, once GRT had decided the verdict. FF hold was therefore not signed off.

**Files:** `physical/` holds the repair tail, the OpenSTA worst path on `5_1_grt.odb`, and the CTS report. `jobs/probe_grt.tcl` is the probe.

## Not tried
Not tried, by the owner rule (one attempt):
- a registered `lw[rd_k]`/`lw[rd_k+1]` lookahead for the read loop, which would add zero cycles
- area relief for `seg` and the head argmax
