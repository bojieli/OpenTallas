# Qwen3-8B ROM KV service (credit17): pricing for mutable-storage protection and refresh

This is a model-only review. There is no new RTL or P&R, and nothing in the repo changed. Subject: `results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json` (calendar = model-r2). Method: re-run `tools/uarch_model_qwen_kv_credit17.build()` in a scratch worktree at `dcba5c0ab` with edits to the calendar source and to the service class (`run_variants.py`, `run_pred.py`, `price_area.py`). The baseline replay reproduces model-r2 exactly: 358.6013 us, REF=PREALL=11456, max lateness 1633.

## A. Named baseline QROM-KV-SECDED-B1

| Storage | Code | Fit |
|---|---|---|
| request RAM 64x512/PC (472 = 216 hdr + 256 data) | (225,216) + (266,256) | 491/512, spare columns |
| return RAM 64x512/PC (471 = 215 hdr + 256 payload) | (224,215) + (266,256) | 490/512 |
| FF spill 4/PC, lookahead 16/PC | carry RAM codewords (+19 FF) | checked after RAM/spill join |
| context 128x256, 32/stack (record 232) | (241,232) | 241/256 |
| assembly 56x85x787 FF | 4x(153,144) per quarter (128 data + 16 mask) + (220,211) meta | +45 FF/word, no RMW |
| pending/cohort/credit control FF | even parity, detect -> fail-stop/replay | 0 edges |

Why these widths: K=256 matches the repo's measured checker exactly. K≤247 needs only 8+1 check bits. Each record is written whole, so one code per field is enough, and (72,64) would multiply decoders with no gain. **No SRAM macros are added.**

The costs come from the measured ROM-ECC history (same construction):
- **Clean checker, K=256:** 525.7 ps at SS, +247.6 ps setup slack at 833 ps, 80.07 um2. The FF virtual hold slack is -13.3 ps, so it needs hold buffers.
- **Full corrector:** 158.6 um2 but 2.8 ns, so it stays on a held-word slow path.

**Area per die: 0.404 mm2** (FF 0.116, encoders/checkers/correctors 0.215, parity 0.073). The conditional slot remaining is 2.54 mm2. This is cell area only.

**Latency per serial transaction (conservative):**
- Return chain: +3 service edges (encode at raw_capture 3→4, check at return_validation 2→3, context check in lookup 12→13).
- Request chain: +2 (encode at write, check before command).
- Assembly: +2 stream periods.
- Total: about 6.67 ns.

The lower bound is +1 return edge and +1 assembly period.

**Token latency:**
- Conservative: 358.60 → 361.28 us (+2.67 us, +0.75%). That is about 11 exposed serial transactions per layer, consistent with 2084 cohorts / 136 credits ≈ 15 credit turns per layer.
- Lower bound: about 0. The run gave -0.10 us because the lazy calendar is non-monotone.
- Under strict refresh: +0.64 us.

## B. Refresh

**What the repo uses:**
- tREFI 3.9 us and tRFC 350 ns from JESD238 (`rtl/hdc/kv/ot_hdc_hbm_model.sv:49-83`), plus tRFCpb 200 ns (`ot_hdc_v41x_idx_hbm.sv:33`).
- Credit17 uses per-PC REFab: PREALL (+17) then REF, staggered.

**Postponement allowance:** no source in the repo. The repo's models say "there is no postpone/pull-in". The external JEDEC figure of up to 8 postponed REFab is unverified here.

**What 1633 means:** 1633 edges is 0.42 tREFI, so at most one REF is ever outstanding. That would be legal under any allowance of at least one REF. But it is an observed maximum, not a bound:
- The lazy model only refreshes when a new request arrives.
- 188 REFs are still due at token end, and the next token restarts the refresh phase, so that debt is silently forgiven.
- The RTL does refresh from IDLE (`ot_hbm_r14_pc.sv:120`).

**Strict REFab** (each REF issued at its due edge, as the RTL does):
- Max lateness 103 edges; REF=PREALL=11376.
- Banks are unavailable 367/3900 = 9.4% of each PC's time.
- **Token time 356.49 us, 2.11 us faster than lazy**, because lazy refresh puts tRFC on the demand path.
- Carrying the token-end debt adds at most 0.37 us (not run).

**Naive REFpb is rejected:** 423.3 us (+64.7 us). It closes open rows, and its 431k extra commands load the shared command paths. A refresh-aware bank choice was not modelled.

## 1% screen, like for like

| Case | us |
|---|---|
| Predecessor, strict refresh | 357.22 |
| credit17, strict | 356.49 |
| credit17, strict + ECC | 357.14 |

Against the lazy predecessor, credit17 under strict refresh shows a 1.29% gain. That is an artifact: like for like, the gain is 0.20%. With ECC it is 0.02%, but the predecessor run had no ECC, so the two are not fully comparable. **The 1% gate still fails, and the 3k budget (333.33 us) is missed by about 23.8 us.**

**Not priced:**
- Hold buffers.
- PG, routing and clock.
- HBM link and on-die ECC, and controller ECC.
- The calendar for the slow correction path.
- Carrying the token-end refresh debt.
- A smart REFpb.
