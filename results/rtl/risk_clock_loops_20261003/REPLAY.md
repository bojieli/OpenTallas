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
| DS ROM (18 blocks) and HBM comparators (~15 blocks) | | helper screens running; see STATUS.md | pending |

## Fix for the one confirmed failing loop (one-shot collective pop)
- **The fix:**
  - Register the FIFO head: a first-word-fall-through output register, with `head_mode` carried in a 1-bit side register written at push or advance.
  - `pop` then depends only on registered `nonempty` / `head_mode` / `g_busy` / `inflight==0` flags. The fan-out of `pop` gets a duplicated register per source.
  - Standard look-ahead: next-state flags precomputed from push/pop.
- **Cycle cost:** +1 cycle of fill latency per collective, and no throughput loss (1 word per cycle is kept).
- **Per-token impact:** about 72 all-reduces per token gives +72 cycles on about 144,954, i.e. 0.05% of the per-user rate.
- **With the chosen DEPTH 256 SRAM FIFO:** the macro read latency already forces a registered head, so the same structure applies.

## Pricing basis (Qwen ROM)
- 31 fused instructions per layer per die (`program.hex`) and about 1,150 per token.
- A +1 cycle per issue on the core or ME issue handshake (`ready = !active && !pend`) would cost at most about 1,150 cycles per token, i.e. 0.8%.
- The per-element address recurrences (`cur`, `j`/`k`/`t` in `ot_qwen_w12_matvec.sv:359-547`) are per-cycle loops. Their standard fix is look-ahead (`cur+js` precomputed, which FAST_ISSUE already does with keep-prefix adders): +1 cycle of latency per op, about 1,150 cycles per token, 0.8%. A naive two-cycle issue would halve the ME rate and must not be used.

## Verdict (provisional)
- **Qwen ROM:** the sequencer's loops close at 1.2 GHz routed, so the earlier pre-layout "miss" was a fanout artifact. The collective pop loop fails by about 1.2 ns in the screen. It has a cheap fix (0.05%). The ME/core/SU results are pending.
- **DS ROM, HBM:** pending. See STATUS.md.

## Replay
```
# screens (ot-agidock128 small, ot-pve1 large via ~/bin/admit.sh): jobs/qwen_jobs.sh, jobs/qwen_jobs_pve1*.sh
python3 tools/risk_clock_loops_screen.py --top T [--source F | --resolve-from LIST] [--param K=V] \
   [--blackbox M] [--include D] [--focus NAME=REGEX] --period-ns 0.833 --work W --output R.json
# routes: jobs/route_tpseq.sh (agidock), jobs/route_oneshot.sh (pve1); then tools/w18/corner_sta.py
```
The Qwen core is generated with `tools/qwen_rom_rt_core_emit_w12.py` (emit/emit_vstream) into `src/gen_rcl/`, and its source list is `jobs/qwen_srcs.txt` = gen_rcl + rtl/{hdc,rom,proto,common}/*.sv.
