# S81-WQBP 10-20: attn.wq_b P126 row-batch calendar = die compiler emission + consumer retire / deadline bench

Branch claude/s81-wqbp-1020 (main-based). Carries the S81-RATEFIX compiler pieces (xs_calendar.compile_pipeline,
claude/s81-ratefix-1019@ff8fa3745) and the TOKSIM-S81D/WQBP compiler integration that was left uncommitted.

## 1. Compiler emission (no scenario)
- `tools/s81_dv/layer_prog/xs_wqb_die.py` `wqb_calendar`: one function for both emitters. Default PIPELINE P126 /
  cfg_lead 52: all phases in one calendar segment, tags 0/2 alternate. Static checks run on every emission: rows ordered
  and unique; streams disjoint; a tag is reused only after its retire; ROM bounds; is_d delay line <= ND; period >= the
  measured floor. P < 126 is a COMPILE FAULT (CalendarFault), never a stall. Serial P224 can still be selected.
- The die compiler `dv_layer_compile.py` -> `lower_xs` -> `xs_place.lower_placed` now emits
  `prog/xs/<id>.calendar.json`, the pq_calendar action/time ROM images and is_d for attn.wq_b.
  Fleet runs (ep9, real layer fixtures):
  - L0 u_s_0S: 11 phases, static PASS, predicted span 1483.
  - L2: wq_b + idx.q, 17 phases, span 2239.
  - Evidence: `evidence/out_dvc/`. The L2 run used the code before the edit to the lowering-note text; only the note
    differs.
- `xs_wqb_die.py die`, L0/L2/L14/L20, every layer class:
  - pipeline: 11 phases, span 1483; sparse layers with idx.q 17 phases, 2239.
  - serial P224: 2463 / 3807.
  - P124: refused, rc 1 (`evidence/out/die_*`).
- The fullsix vehicle programme (`retained_xs_program.py`) takes its calendar from the same function. Its seven ROM
  images match the simulated runs byte for byte, in all 35 comparisons (`EMIT_IMAGE_MISMATCHES 0`, client log
  `consumer1.otrun.log`). The runs are source_compiled, capture_l2, capture_l14, wrong_rbase and late_cfg in
  codex-cap-contract-1020. All five used the same exe 63eccd91, built with Verilator 5.050 (2026-07-01), plus the 15
  source-derived CAP descriptors from codex/token-cap-contract-1020. So that RTL ran exactly this compiler emission.

## 2. Consumer retirement + deadline bench (`tools/s81_dv/layer_prog/check_wqbp_consumer.py`)
These are observational checks on the real RTL monitors. Rule groups:
- **R1 element retire, per tag (Q_LIFETIME):** the 54 capturing q elements each hold one life per GO (15). Every life
  retires, consecutive phases alternate slot/tag, a slot is re-armed only after it retires, and the fault count is 0.
- **R2 CAP descriptor retire, per row domain:** one window per CFG (15). Each window retires before the next CFG. The
  rbase domains rotate 5800/9800/d800/1800. All sticky causes and F5..F11 are 0.
- **R3 consumer read at the compiled deadline:** D = first capture 1573 + compiler span 1987 + priced tail 195 = 3755.
  At D, the VP SRAM state is rebuilt from every real VP commit and read. All 512 dims must equal the released-fixture
  golden, with no collision, and no overwrite of a consumed address up to the end of the trace.
- **R4 static = runtime:** 15 GOs at exactly 126 spacing and 15 CFGs.

Matrix (fleet ep9 unit oth-ubuntu-1778215-1792488412, `evidence/out/consumer/`; 9/9 as expected):

| case | verdict | note |
| --- | --- | --- |
| L0 / L2 / L14 nominal | PASS | last VP commit 3637, last element retire 3551, last CAP retire 3619; slack 118 |
| deadline -118 | PASS | slack 0: the check is tight |
| deadline -119 | FAIL R3 | 1 edge early |
| tail 0 | FAIL R3 | the CAP/VP tail needs 77 of the 195 priced |
| wrong rbase | FAIL R2+R3 | |
| late CFG | FAIL R2 | F11 |
| P124 calendar | FAIL R1 (element faults) + R2/R3/R4 | |

## 3. Composed rate
The composer is codex/token-gl24-main-1020@d5fcf23d5, `tools/toksim_s81_compose.py`. `--check` PASSES for both the
baseline and `--scenario wqbp-p126`:
- Baseline (WQBG serial 3359 + 195): AR **834.0** / MTP **2,649.1** tok/s.
- P126 (1987 + 195 on all 40 wq_b nodes): AR **867.1** (+4.0%) / MTP **2,738.9** (+3.4%).

The die shape is 11 phases with a predicted span of 1483, against 1987 for the 15-phase vehicle. That would be a further
504 edges per node, but it is not measured and is not used.

## Still open (not claimed)
- CAP cfg_d descriptors for the real 8-frame / 11-phase die shape inside the die compiler. Only the private fullsix
  6-frame / 15-phase lowering exists (codex compile_fullsix_cap_program.py).
- A consumer RTL unit reading the VP (q_rope QR / attention) is not in the vehicle. R3 reads the VP SRAM state that the
  real write port produced at D. The vehicle's output base 0 is not the die consumer layout QR_IN.
- The fullsix tb's three legacy source bookkeeping asserts (simulator exit 1) are unchanged. They are explained in the
  codex README.
- ot_s81sl_cap/slice/xr in the vehicle differ from release 19bf4121e (TOK2 capld successor).
