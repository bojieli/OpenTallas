# HEAD die token pass on the LANDED bind (TOK-HEAD-LAND-1, 2026-10-28)

Whole-die HEAD token simulation on the count-aligned LANDED top of the DIE-HEAD-17 gate bind
(claude/die-head-17-1028@fbacd60fa5, clk17_max_2: plan.json md5 054f73bc, bind.json md5 fa544b31), strap form
(OWNER 12.15a), with the die START tree bound, plus the rank 1-3 ROM image compile.  All numbers CHECKED (simulated,
logs here) unless marked UNCHECKED.

## 1. ROM images ranks 0-3 (CHECKED)

Rank 0 = TOK-ALL-14 images (tok14-head-fw).  Ranks 1-3 generated and run with `tools/s81_head/head_native_fullweight.py`
(src/ranks.sh, every active tile in the native partition bench on intel1):

| rank | active tiles | RTL argmax (global row, bits) | golden | GO->result |
|---|---|---|---|---|
| 0 | 253 | 21946 4173a558 (TOK-14) | = | 8,429 |
| 1 | 253/253 PASS | 33100 41345fd2 (tW0o5) | = | 8,429 |
| 2 | 252/252 PASS | 93642 41363460 (tW5o5) | = | 8,429 |
| 3 | 252/252 PASS | 103774 414142e8 (tW1o8) | = | 8,429 |

Controls wrongrom / mutrow / mutft CAUGHT on every rank (ranks/r*_result.json).  4-rank argmax = rank 0 = golden.

Root cause fixed (die-local, tools/s81_head/head_native_fullweight.py): rank > 0 used `rank * ROWS_RANK_PLAN` as the
row base (rank 3: 97152, contract 97024) and the PLAN's rank-0 strap set for every rank (ranks 2/3 would enable the
dark slot tE5o10 and duplicate 128 rows).  Now the rank base and per-tile ROW0/TEN come from `head_row_map.build`
(controller_row_base 0/32384/64768/97024), fail-closed against the plan straps for rank 0.  No padding/override.

## 2. Landed die-spine vehicle

src/landrtl.sh: `count_align_bind --strap-form` (427 crossings DEPTH 4, K -11..14, verify 2000 chips 0 violations,
3214 tied strap bits, 16 types; bind == the gate bind.json, no key diffs) -> `fallback_land.py compose`
(OK 16 -> 16 types) -> `gen.py latency` -> `head_landed_ft_adapter.py` -> `gen.py rtl --clock-landing` (rc 0, strap
audit PASS).  Bench (src/setup_land.sh, src/mk_tb_land.py) = the TOK-ALL-15 recipe (ctl leaf -> ctl_core_drv, bundle ->
measured view LB 8,419, off-path leaves stubbed) on the landed top, plus:
- each of the 326 region clocks at its routed tap arrival (proof_t/tap_arrivals_<C>.json late_ps; plan d within 29 ps);
- the START tree `ot_die_start_stages` (results/die_head_17_1028/die_ca/start_stages.sv, 358 stages, root
  SETTLE 64) instantiated beside the top: pst_<part> -> top, top rs_<part> -> tree, stage clocks at their tree cell's
  arrival.  `gen.py rtl` does not instantiate it (the top exposes 326 pst_ inputs / 20 rs_ outputs); with pst_ tied 0
  no region gets a count origin and ctl never starts (first run, FAIL).

| run | result | GO->result | verdict |
|---|---|---|---|
| TT arrivals, 2 positions (GAP 10,357) | row 21946 bits 4173a558 = golden | **8,780** both | PASS |
| FF arrivals | same | 8,780 both | PASS |
| TT, tE3b4 = REAL bundle on released images | same | 8,780 | PASS (measured view == real in the die) |

Landing ready (die-wide collect) at bench cycle 342, first GO 745.  Unlanded TOK-15 vehicle: 8,691 -> landed **+89
cycles**.  Same 8,780 at TT and FF arrivals: the count-aligned latency is phase-invariant, as designed.

Per token (UNCHECKED composition, TOK-15 rows with the simulated span replaced): xb_ingress 162 + 8,780 + rank_merge
361 + mtp 6 + out hop 4 = **9,313 cycles = 7.76 us** at 833 ps; calendar window 10,357 -> slack 1,044 (HEAD is not
the rate limiter; one token per window = 115.9 k tok/s per HEAD die).  rank_merge remains the TOK-15 lower-bound
caveat (>= +12).

## 3. Mutants (must FAIL)

| mutant | change | outcome |
|---|---|---|
| ROMFLIP | tE3b4 real bundle; row 21946 dim 3286 (max abs x) BF16 3e2f -> 7e2f, exactly ONE ROM word changed (ha1_1 line 432; src/rom_flip.py) | row 3352 bits 413075de (= next-best tile tE0o4) MISMATCH 2/2 -> **FAIL CAUGHT** |
| K-1 | sst5 strap_ca_k_tx_i 1 -> 0 (host -> sst5, margin_lo 252.8 ps) | guard fault cycle 216, no landing ready, no result -> **FAIL CAUGHT** |
| K+1 on path | sp0 strap_ca_k_x_i 8 -> 9 (ctl -> sp0 x/GO, margin_hi 1,297.9 ps > T) | bit-exact result, GO->result **8,781** (+1): caught only by the exact-latency value 8,780; the ring guards do not see an in-window K error |
| K+1 off path | sst5 strap_ca_k_tx_i 1 -> 2 (mesh tx, not on GO->result) | 8,780 PASS: equivalent mutant for this token path |

## 4. Alignment checks in the HEAD bind script

src/landrtl.sh runs the existing checks in order and stops on a failing step: count_align_bind + verify (logs/cab.log),
compose landing_contract (logs/compose_report.json), gen strap audit (gen_count_strap_audit.json), then the die sim
(src/setup_land.sh, build.sh, run.sh).  regen_constants.py has no s81_head mode; it is a shared tool
(tools/die_plan), so no mode was added here (ASK in the review queue).

## Findings

1. Bench bug, affects any Verilator bench that delays a clock with `x <= #d ck`: Verilator 5.050 --timing gave the
   value of ck at the END of the delay, so every clock whose delay sits in an odd half-period window ran INVERTED
   (lk_HOST0 2,920 ps vs sst5 2,889 ps -> writer 448 ps after reader instead of 31 ps; ring sst5.u_i tripped
   glo=0; logs/debug_*).  mk_tb_land.py now drives each delayed clock as its own 833 ps clock at phase (d mod T),
   timescale 1ns/100fs (1 ps precision rounded #0.4165 to an 834 ps period).
2. compose landing_contract reports 362 errors "lk_*.cland_tstart_in/out: infrastructure pin used 0 times" while
   compose status is OK; the start tree is external to the generated top (above).
3. The die plan carries only the rank-0 strap set; ranks 2/3 need the tE5o10 TEN=0 variant (head_row_map has it).

Raw data: intel1:/srv/opentallas-scratch2/claude/tok-head-land-1 (land/, obj_*, run_*.log, img_romflip, img_real,
ranks/); landed RTL built on intel2 (same path).  Build ~10 min / 2.1 GB (real) and ~4 min / 0.9 GB (measured view),
run < 15 min, 13 MB.  Hashes: gen_sha256.txt.
