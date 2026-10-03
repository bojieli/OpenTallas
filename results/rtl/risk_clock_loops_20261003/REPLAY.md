# Control-loop clock ceiling at SS (disaster-class risk check, 2026-10-03): PARTIAL

## Question
Can each design's loop-carried CONTROL close at its domain clock? Datapaths can be pipelined. A loop that cannot close costs one cycle per iteration.
- Domains: streaming 1.2 GHz (0.833 ns); serial chain 0.9 GHz (1.111 ns).
- Corners: setup at SS with 60 ps uncertainty; hold at FF with 25 ps.

Sources are pinned at `e156ed54e8ff31def4b8c58d69da3743bb6b498c`, from a `git archive` of rtl/ tools/ physical/ configs/. The copies are at `ot-agidock128:~/rcl-20261003/src` and `ot-pve1:~/rcl-20261003/src`.

## Method
`tools/risk_clock_loops_screen.py` runs per block:
1. Yosys 0.68 + ABC mapped on TT, using the driver's synth.ys.
2. OpenROAD in `openroad/orfs:latest` on the SS liberty, in two phases:
   - **raw:** pre-layout, unbuffered.
   - **repaired:** placed, then repair_design + repair_timing.
3. Register-to-register WNS and fmax for each phase, plus the worst path into named loop-state registers (`--focus`).

The authority is a full ORFS route at WC with hold at WC,BC, checked with `tools/w18/corner_sta.py` (SS setup, FF hold).

Calibration (Qwen TP sequencer, 0.833 ns):

| Measure | reg-to-reg setup |
|---|---|
| Raw screen | -7,813 ps: fanout, `st` driving 568 loads |
| Repaired screen | -153 ps |
| Routed SS | **+6.99 ps** |

The repaired screen is therefore about 150 ps pessimistic. A screen miss inside about 150 ps means "route it", not "fails".

## Results so far

| Design / block | Domain | Evidence | Loop result |
|---|---|---|---|
| Qwen ROM `ot_qwen_tp_seq_w12` (segment FSM, tx queue `rd_go`/`q_n`, argmax `best_v`→`best_i`) | 0.9 | **ROUTED** `routes/qwen_tp_seq_1111`: SS +72.1 ps, FF hold +3.2 ps, closes sign-off | PASS at 0.9 GHz |
| same | 1.2 | **ROUTED** `routes/qwen_tp_seq_0833` | Reg-to-reg SS +6.99 ps and FF hold +10.6 ps: the loops close at 1.2 GHz. The remaining -73.7 ps is the output-port budget (`c_last`/`vm_raddr` against a 20% output delay), not a loop. Note that `worst_register_d_slack` -23 ps is an AND5 pin named D on the same output path. |
| same, ENABLE_AR256=1 | 1.2 | screen | repaired -143 ps (within calibration): needs a route |
| Qwen `ot_rom_oneshot_die` (collective credit/pop loop), DEPTH=32 | 1.2 | screen `screens/qwen/oneshot_die_d32_833.json` | **FAIL, real loop**: repaired -1,208 ps, 490 MHz. The path is `rp` → 32:1 flop-FIFO head mux → `head_mode` → `pop` → fans out to every `rp`/`cnt`/`cr` (`rtl/rom/ot_rom_oneshot_allreduce.sv:122-162`). Routed SS run is in flight on ot-pve1. |
| Qwen ME spine (FAST_ISSUE 0/1), core sequencer (spine and SU black-boxed), vstream SW=64 | 1.2 / 0.9 | screens running on ot-pve1 | pending |
| DS `ot_w15_rom_oneshot_die_px` pop/credit (rp → FIFO head mux → pop → cnt), DEPTH 32 | 1.2 | screen `screens/ds/ds11_*` | **FAIL, real loop**: 474 MHz (-1,277 ps). This is the same defect as Qwen's one-shot, and it is worse at the runtime's 512-deep flop FIFO |
| DS `ot_hdc_v41x_idx_kctl_ring` issue/drain (d_hi → run) | 1.2 | screen | **FAIL, real loop**: 671 MHz (-658 ps) |
| DS q-element x-need walker (n_c → walk2 → n_q), `ot_v41_rom_elem_q_w10` | 1.2 | screen | **FAIL, real loop**: 635 MHz (-743 ps). The earlier TT 0.92 ns route was also not closed. The ICG enable `r_go → ENA` is -82 ps, within calibration |
| DS `ot_chip_v41x_hbm_karb` round robin | 1.2 | screen | -916 ps / 572 MHz, but the path starts at an input port, so it needs an in-context check |
| DS rom_adapt (per-op setup: 30×30 stride multiply, 64-entry key lookup) | 1.2 | screen | -1,055 ps. A one-shot setup per op, not per cycle; fixed with +1-2 setup states per op |
| DS sinkhorn_seq control, accept (NSLOT 8), sel_ctl control, refill FSM, pkg_ctrl_x (u64) | 0.9 / 1.2 | screen | pass or within calibration (sinkhorn and sel worst paths are pipelinable datapath) |
| DS core sequencer, spine, su_adapt, coll_dma, vec, topk_merge | | still running | pending |
| HBM `ot_gpu_issue` (SM issue: `item = wb+si < items_q` → row_ok → adv → cursor) | 1.2 | screen `screens/hbm/issue_*` | **FAIL, real loop**: Qwen 813 MHz (-397 ps), DS 752 MHz; it stays about 810 MHz at 1.024 and 1.111 ns too |
| HBM `ot_gpu_bulk_copy` (consume: cons_p → 1024:1 `full[cons_p]` → take) | 1.2 | screen | **FAIL, real loop**: Qwen 682 MHz, DS 590 MHz |
| HBM `ot_gpu_rf_visibility_fence_w6` (SECDED decode → update → re-encode in one cycle) | 1.2 | screen | **FAIL, real loop**: 429 MHz |
| HBM KV lifecycle controller (72-entry tag match → reader state) | 1.2 | screen | **FAIL, real loop**: 458 MHz |
| DS MTP accept, guarded (SECDED-coded slot state) | 0.9 | screen | **FAIL, real loop**: 444 MHz |
| HBM `ot_gpu_router_topk` (`lane <= insert(lane,x)`), bench-only | 1.2 | screen | FAIL, loop: 621 MHz |
| HBM `ot_gpu_stack` control, fence (H1), barrier | 1.2 | screen | pass (control focus +34 / +27 / +602 ps) |
| HBM `ot_gpu_scratch_service` | 1.2 | screen | -130 ps, from SRAM clk→Q 707 ps at SS: a route is needed, not a loop |
| Streaming HBM controller (branch 52ce3e9c1, routed) | HBM CK/2 | routed | PASS at 1.024 ns (+19 ps); -4.7 ps at 0.833 ns. Acceptable in the service clock |

## Fix for the one confirmed failing loop (one-shot collective pop)
- **The fix:**
  - Register the FIFO head: a first-word-fall-through output register, with `head_mode` carried in a 1-bit side register written at push or advance.
  - `pop` then depends only on registered `nonempty` / `head_mode` / `g_busy` / `inflight==0` flags. The fan-out of `pop` gets a duplicated register per source.
  - Standard look-ahead: next-state flags precomputed from push/pop.
- **Cycle cost:** +1 cycle of fill latency per collective, and no throughput loss (1 word per cycle is kept).
- **Per-token impact:** about 72 all-reduces per token gives +72 cycles on about 144,954, i.e. 0.05% of the per-user rate.
- **With the chosen DEPTH 256 SRAM FIFO:** the macro read latency already forces a registered head, so the same structure applies.

## Fixes for the HBM comparator loops (all standard GPU practice; screen only, not yet routed)
- **`ot_gpu_issue`:**
  - The fix is look-ahead: register `row_ok`/`last` for the next item, precomputed from `si+1` and `wb+IL`, so `adv` is a registered-flag AND.
  - Cost: 0 cycles per iteration, +1 cycle of latency per op.
  - Alternative: two-warp interleaving, where each issue slot alternates between two independent rows. That gives 0 throughput loss when at least 2 rows are in flight (IL=8 already has 8).
- **`ot_gpu_bulk_copy`:**
  - The fix is a registered `full[cons_p+1]` look-ahead (a next-slot valid bit), or a per-bank occupancy split into 8×128 banks.
  - Cost: +1 cycle of latency per stream, no rate loss.
- **SECDED state loops** (fence_w6, MTP accept, W2):
  - Keep the live state unencoded in flops and encode only on write-back or for checking.
  - Mutable control-state protection must stay (AGENTS.md), so the alternative is a check that runs one cycle behind and raises a fault, rather than a decode in the loop.
  - Cost: 0 cycles per iteration plus one cycle of fault-detection latency.
- **KV lifecycle:**
  - The fix is to register the 72-way tag match, i.e. a two-cycle lookup pipelined over independent keys.
  - Cost: +1 cycle per lease operation. That is per layer-KV access, not per element, so the token impact is negligible (to be priced).

## Pricing basis (Qwen ROM)
- 31 fused instructions per layer per die (`program.hex`) and about 1,150 per token.
- A +1 cycle per issue on the core or ME issue handshake (`ready = !active && !pend`) would cost at most about 1,150 cycles per token, i.e. 0.8%.
- The per-element address recurrences (`cur`, `j`/`k`/`t` in `ot_qwen_w12_matvec.sv:359-547`) are per-cycle loops. Their standard fix is look-ahead (`cur+js` precomputed, which FAST_ISSUE already does with keep-prefix adders): +1 cycle of latency per op, about 1,150 cycles per token, 0.8%. A naive two-cycle issue would halve the ME rate and must not be used.

## Verdict (provisional)
- **Qwen ROM:** the sequencer's loops close at 1.2 GHz routed, so the earlier pre-layout "miss" was a fanout artifact. The collective pop loop fails by about 1.2 ns in the screen. It has a cheap fix (0.05%). The ME/core/SU results are pending.
- **HBM comparators: AT RISK.**
  - Four per-token control loops miss 1.2 GHz by far more than the 150 ps screen pessimism: SM issue at about 810 MHz, bulk-copy consume at 590-680 MHz, the SECDED fence at 429 MHz and KV lifecycle at 458 MHz.
  - Each has a standard look-ahead or register-split fix with no per-iteration cycle cost. As built, though, the SM would run at about 0.6 GHz unless they are fixed.
  - A routed confirmation of `ot_gpu_issue` and `ot_gpu_bulk_copy` is the next step.
- **DS ROM: AT RISK (fixable).** Three per-cycle loops miss 1.2 GHz by 650-1,280 ps: the collective pop, the index kctl drain and the q-element x-need walker.
  - **Collective pop:** registered FIFO head (look-ahead), +1 cycle per collective.
  - **kctl ring:** register the drain-head compare and issue from a precomputed next-run flag (+1 cycle of issue latency per index-scan burst, not per key).
  - **x-need walker:** split the walker into a 2-stage next-need precompute, which costs +1 cycle of latency per ROM sweep. Per-element rate is kept only if the walker gets look-ahead. A naive two-cycle walker halves the q-element field rate, a disaster-class cost, and must not be used.
  - Routed confirmation of the pop and walker loops is next. The core sequencer and spine are pending.
- **Screen notes:**
  - The HBM screens used a tool copy (`jobs/risk_clock_loops_screen_hbm.py`) that adds SRAM macro LEF/lib, enlarges the floorplan for high-pin-count blocks and cuts the FP black boxes, plus RTL copies with the w6 SECDED package functions inlined (a Yosys import crash).
  - Its "all fmax" print is wrong (slack in seconds); only the register-to-register figures are quoted.

## Replay
```
# screens (ot-agidock128 small, ot-pve1 large via ~/bin/admit.sh): jobs/qwen_jobs.sh, jobs/qwen_jobs_pve1*.sh
python3 tools/risk_clock_loops_screen.py --top T [--source F | --resolve-from LIST] [--param K=V] \
   [--blackbox M] [--include D] [--focus NAME=REGEX] --period-ns 0.833 --work W --output R.json
# routes: jobs/route_tpseq.sh (agidock), jobs/route_oneshot.sh (pve1); then tools/w18/corner_sta.py
```
The Qwen core is generated with `tools/qwen_rom_rt_core_emit_w12.py` (emit/emit_vstream) into `src/gen_rcl/`, and its source list is `jobs/qwen_srcs.txt` = gen_rcl + rtl/{hdc,rom,proto,common}/*.sv.
