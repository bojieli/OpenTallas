# Qwen async collective: precomputed segment end and registered 2:1 select (SB_PIPE=4), owner-approved final attempt (2026-10-04)

**Verdict: FINAL REJECT.** SB_PIPE=4 is exact and keeps the gain (+7.27% per user), and it removes every loop the SB_PIPE=2 route reported. It still does not close in context. After GRT repair the SS setup WNS is **-2.2 ps** on 2 endpoints in the head argmax, and repair stalls. Detailed route does not converge: DRC violations bottom out at 2,610 at iteration 16, jump back to 9,993 at iteration 17, and the 6 h flow timeout ends the run during iteration 18. There is therefore no 6_final, no SS/FF sign-off, and the adoption bar (SS >= 0 at 60 ps and FF >= 0 at 25 ps after detailed route) is not met. Under the owner rule there are no further attempts. The Qwen ROM keeps the one-stream all-reduce: 144,522 cycles per token with ideal memory.

## The change
Source: `837d9900a` on `claude/qwen-async-seg-precompute-20261004`. `SB_PIPE=4` is a new value; the default stays 0, and modes 0 to 3 behave as before. All changes are in `rtl/rom/ot_qwen_tp_seq_async_w12.sv`, and each costs zero cycles.

- **Fix (1), the segment end comes off the loop.** `more` is a register holding `rd_k < nw`, loaded with the outcome for both cases: `rd_go ? (rd_k+1 < nw) : (rd_k < nw)`. It is reloaded with `nw != 0` at the two counter clears. The receive end, `rx_k == rx_total - 1`, which also started at the `nw` compare (`next_val`, `next_token`, `seg` in SB_PIPE=2), gets the same treatment as `rx_end`.
- **Fix (2), both outcomes are precomputed.** `rdy_h = lw[ra]` and `rdy_a = lw[ra+1]` are registered without `rd_go`. The ready bit is `go_r ? rdy_a : rdy_h`, where `go_r` is the previous `rd_go`. Bit for bit this equals the SB_PIPE=2 `rdy`, so the send cycles are identical.
- **The scoreboard set no longer subtracts.** `lw` is indexed by the word's absolute address mod 256. A region is at most 256 consecutive words, so the index is unique within it. The set therefore decodes `addr[7:0]` directly, without `addr - vw`, which removes the `s1_hi` path at -6 ps. The read index is `ra = vw + rd_k`, kept as a register.
- Simulation asserts check `more`, `rx_end` and `ra` against the direct expressions every cycle, plus a no-early-send check against `lw[ra]`. None fired in any run.

Fix (3), a one-cycle bubble at segment boundaries, was not needed for setup. It would not address the remaining limiter (the argmax compare) or the routability problem.

## Exactness and gain (all measured)
| | one-stream | SB_PIPE=1 | **SB_PIPE=4** |
|---|---|---|---|
| Verilator gate, 56 cases | | pass | **pass**: every case's cycles, writes and faults are identical to SB_PIPE=2; the overflow and bad-last cases fault |
| Full token, ideal memory, layer-parallel (exact, poison check passes) | 144,522 | 134,658 | **134,730** |
| REAL_MEM E+L0-L2 P0 (X, K/V exact) | 14,273 | 12,244 | **12,246** |
| REAL_MEM E+L0-L2 P255 (X, K/V exact) | 13,874 | 12,701 | **12,708** |

**Per-user gain:** 144,522 / 134,730 = **+7.27%**, or 8,907 tok/s at 1.2 GHz.

## Physical, in context
The recipe is the same as a0h/a1p and f2/f3: `ot_qwen_tp_seq_async_ctx_w12`, 1.2 GHz, 60/25 ps uncertainty, WC/BC corners, `ADDER_MAP_FILE=` empty, die 130x130 µm.

| | after CTS repair | after GRT repair | detailed route |
|---|---|---|---|
| SB_PIPE=2 (previous) | -6.4 ps | -17.8 ps, 63 endpoints | not run |
| **SB_PIPE=4** | **no violations** | **-2.2 ps, 2 endpoints** (`next_token[12]`); RSZ-0062 | **did not converge**: 66,156 -> 2,610 (iteration 16) -> 9,993 (iteration 17); 6 h timeout in iteration 18 |

- **Setup.** The remaining GRT limiter is the pre-existing head argmax compare, `best_v` -> `okey` compare -> `next_token`/`next_val`. It closes in a0h, where utilization is 20%. Here the async tap and scoreboard raise utilization to 45% (7,028 µm²). With placement parasitics the same path is +29 ps (`jobs/probe_f4.tcl`), so it fails only with GRT wiring.
- **Routability.** Detailed route is the binding problem. It is shared by every async variant at this die size: SB_PIPE=1 also stalled at 1,215 DRC at iteration 13.
- EPYC was heavily loaded during the run (load 350 or more), which made each DRT iteration slow, about 1 h. The violation trend itself does not converge, independent of that.

## Files
- `async_coll_verilator_gate_sbpipe4.json`
- `layer_parallel/verdict_m4.with-poison.json` and `layer_parallel/verdict_m4_poison.json`
- `realmem/rm_m4_p{0,255}.json`
- `physical/route_f4_repair_and_drt_tail.txt`, `physical/route_f4.partial.json`
- `jobs/run4.sh`, `jobs/probe_f4.tcl`, `jobs/chain.log`

The remote run directory is `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-async-segpre`.
