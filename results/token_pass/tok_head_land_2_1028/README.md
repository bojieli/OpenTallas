# HEAD landed token pass re-run on main after RM271 (TOK-HEAD-LAND-2, 2026-10-28)

Re-run of TOK-HEAD-LAND-1 (results/token_pass/tok_head_land_1028) on origin/main b6fd7043d2, which includes
ROOT-MERGE-271 (DIE-HEAD-10 FSTART: `start_d` on ot_dp_landing_origin_s / ot_dp_landing_root, forwarded start pins
driven by dedicated `ot_dp_landing_relay` face flops).  landslots / fclklat / ringstart are NOT on main yet (re-run
again when they land).  Same bind inputs as LAND-1 (DIE-HEAD-17 clk17_max_2, md5s in logs/landrtl.log), same START tree
(start_stages.sv 358 stages, DIE-HEAD-17; tools/die_plan/start_stage_emit.py unchanged since DIE-HEAD-12), same tap
arrivals.  All numbers CHECKED (simulated, logs/).

## Regenerated landed RTL
src/landrtl.sh (intel2): count_align_bind --strap-form -> compose OK 16 -> 16 types (landing_contract 362 errors =
external START-tree pins, DIE-HEAD-21 item per COORD 22:37) -> latency -> ft adapter -> gen rtl --clock-landing,
strap audit PASS 3,214 bits.  Diff vs LAND-1 generated RTL: s81_head_top.sv and ot_dp_cells.sv identical; the 16
wrappers differ ONLY in the FSTART form (`assign cland_fstart_out_* = cland_start` -> `ot_dp_landing_relay`
(d = cland_start_d, same clk / raw reset) + `.start_d` on the origin).

## Bench
Same as LAND-1 (src/setup_land.sh) plus the COORD 22:37 ASK-4 assertion: src/ctl_core_drv_lat.sv FAILS any result
whose GO->result != +EXP_LAT (default 8,780 = HEAD landed latency of record).

| run | result | GO->result | verdict |
|---|---|---|---|
| TT arrivals, 2 positions | row 21946 bits 4173a558 = golden | 8,780 both | PASS |
| FF arrivals | same | 8,780 both | PASS |
| TT, tE3b4 REAL bundle, released images | same | 8,780 both | PASS |
| ROMFLIP (one ROM word, LAND-1 img_romflip) | row 3352 413075de | 8,780 | FAIL CAUGHT (mismatch) |
| K-1 sp0 strap_ca_k_x_i 8 -> 7 (ctl -> sp0) | bit-exact | 8,779 both | FAIL CAUGHT (latency assertion) |
| K+1 sp0 strap_ca_k_x_i 8 -> 9 | bit-exact | 8,781 both | FAIL CAUGHT (latency assertion) |

Latency unchanged (8,780): expected, the FSTART relay equals start every cycle (0 added cycles, proven by
results/die_head_1028/die_head_10_fstart/fv_start_o.sh); boot: cland_start cyc 124 (FF 123), landing ready 342 (FF 341),
same as LAND-1.  The ctl -> sp0 K-1 is in-window too (bit-exact, -1 cycle), so both sp0 K mutants are caught only by
the exact-latency assertion; the ring guards do not see them.

Raw data: intel1:/srv/opentallas-scratch2/claude/tok-head-land-2 (obj_*, run_*.log, km1/, kp1/, real/);
landed RTL intel2:/srv/opentallas-scratch2/claude/tok-head-land-2/land.  Hashes: gen_sha256.txt.
