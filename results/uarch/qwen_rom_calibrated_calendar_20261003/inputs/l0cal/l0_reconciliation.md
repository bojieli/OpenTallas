# Qwen3-8B ROM layer-0: measured vs unified model (review, 2026-10-03)

Read-only review. Model evaluated on a detached worktree of origin/main dcba5c0ab. Data: `l0_reconciliation.json`.

## 1. Configuration: "TP2" is a label; the run is TP4
- `QWEN_ROM_TOKEN_TP2` is a hardcoded print string in `qwen_rom_rt_observed.cpp`. The die count is the compile-time `TPD` (default 2). This host was built with `-DTPD=4`, and the stage file has four die payloads. The terminal records `scope.ranks=4`, and `rt_tp4d/build_params.json` has die `-GD=4` and coll `-GN=4`.
- Per die: G 6,144 groups, 1,536 tiles (G/4), 8 query heads and 2 KV heads, SU width 64, SMIN 7/SMAX 11/TCUT 7/LV 7.
- The "nodes/die = 1,488" figure counts split-tree nodes the host hosts. It is not a tile count.
- Wire stages: BD 41, NWS 5, TWS 38, ORD 7, XVM 1 and MEM_EXTRA 1, so the ME extra is 112 cycles.
- Arithmetic: the original adders, with no +54/+55 delta.
- Collective: oneshot all-reduce with N 4, LAT 339 and DEPTH 1024.
- Position 0, KV capacity 8,192, 1 attended position.
- The retained TP4 terminal has identical build parameters (binary f16129f2). L0 matches exactly: 4,669 cycles, 2,033 ME, and the same L0 x sha 7631b189 on all four dies. Its L1–L35 are 4,668 cycles (2,027 ME) each, the head is 2,998, and the total is 171,090.

## 2. What the L0 stage contains
- **Included:**
  - the layer from its input norm to the down-projection residual and next-norm tail;
  - QKV, q/k norm, RoPE and the KV write of position 0 (KV zeroed at stage start);
  - attention over exactly 1 position;
  - O and down on the tile array;
  - 2 all-reduces.
- **Excluded:** embedding (preloaded by the host), LM head, image switching, HBM KV service and physical timing.
- **Die-0 instruction trace** (a17a3c79, same binary, same 4,669 cycles):
  - Each all-reduce runs as **2 serialized 128-word segments**. Each segment has 128 transfer cycles and resumes about 362 cycles later, for about 490 cycles per segment.
  - That gives 1,982 exposed cycles per layer, with the ME clock off the whole time.
  - The body outside the collectives is 2,687 cycles.
- `me_busy` 2,033 is the count of cycles with the ME clock enabled: 6 at reset plus 2,027 over six ME windows. It is a window that includes per-op fill (16+112). It is not MAC issue.
- `su_writes` 30,236 counts lane-element writes, not cycles. At 64 lanes that is a lower bound of 473 cycles.

## 3. Model, apples to apples
**Why the model gives 3,338 rather than 2,270.** The credit17 r3 point is `qwen_tp_point(4,6144,'ucie_measured',1.2e9,me_lat_extra=55,ctx=8192,su_width=64)`. It is not an SS variant. Against main's default:
- SU width 1024→64 adds 1,224 cycles;
- ME extra 81→55 removes 156 cycles.

**Finding.** `me_lat_extra` *replaces* the wire extra rather than adding to it. The house convention is that it is the total: `QWEN_SS` = 112 + 54. The +55 is the MUL6 arithmetic delta on top of 112. Credit17, kv_bank_groups and kv_rate_risk pass 55 alone, so they drop the 112 wire-stage cycles that the measured build has.

**RTL-matched comparison** (`qwen_tp_point(4,6144,'board',1.2e9,me_lat_extra=112,ctx=1,su_width=64)`, the same as `qwen_l0_rtl_vs_model`):

| per layer, pos 0 | measured | model | gap |
|---|---|---|---|
| body (excl. collectives) | 2,687 | 2,460 | −227 (×1.092) |
| 2 all-reduces | 1,982 | 884 board / 142 ucie | −1,098 / −1,840 |
| total | 4,669 | 3,344 / 2,602 | −28.4% / −44% |
| credit17, position-independent (chain 2,118 + calendar AR 181.76) | 4,668 | 2,300 | −2,368 (−51%) |

**Approximate span alignment, model vs trace:**

| span | model | trace |
|---|---|---|
| QKV | 504 | 431 |
| attention + O | 837 | 925 |
| gate/up + SiLU | 708 | 647 |
| down + tail | 411 | 702 |

The model charges attention at ctx 1 at 522 cycles, against an 87-cycle attention span in the trace. Its body deficit sits mainly in down plus tail.

**Moving to ctx 8,192** adds +1,220 cycles of model attention. No measurement covers it.

## 4. Verdict
- **The model under-predicts.** At the measured scope (TP4, position 0, host-serviced, LAT-339 two-segment collective), the per-layer total is 28.4% short. The compute body is short by 9.2% (227 cycles). Most of the gap is the collectives (1,098 cycles against the board link).
- **Credit17's calendar layer** (3,338 + 181.76) cannot be checked at ctx 8,192. Its part that does not depend on position is about half the measured value. That shortfall comes from the dropped 112-cycle wire stages and the 71-cycle all-reduce.
- **What the calendar should use:**
  - `me_lat_extra` = 112 + arithmetic delta (167 → chain 2,790 at ctx 1, 4,010 at ctx 8,192);
  - the measured body ratio of 1.092 at position 0;
  - collectives at the measured 991 per all-reduce until a one-segment or UCIe measurement exists.
- **Not shown by this evidence:**
  - long-context attention cost;
  - one-segment all-reduce latency (about 620 cycles, unmeasured);
  - the +55 arithmetic in RTL;
  - SS/FF timing;
  - HBM KV service.
