# HBM-CORES-REBAL-8 (2026-10-28) -- lanes__canon _c20ek2m timing fixes (a)-(c)

Vehicle: lanes__canon _c20ek2m 3_place.odb (REBAL-4 kit, oth-ubuntu-20590), TT RVT liberty, placement RC (setRC_rcx),
ideal clock. All STA here re-reads the SAME odb; no rebuild.

## (a) reset port constraint -- DONE, CHECKED
* Generator: physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py sdc() (the one SDC template of every HBM core kit;
  no per-kit edit). The extra `set_input_delay -max 0.5*per` on the reset pins is removed: under the reset contract the
  core reset pin is driven by the die reset tree's last relay flop (tools/die_plan/reset_tree.py, DIE-HBM-10
  reset_contract.json), i.e. a synchronous input at the IO budget like every data pin (= gen_phys arst_n floor
  IO_BUDGET*per = 166.6 ps). Reset ports stay in $non_clk_in. hbm_arch_cores tests 11 PASS, tools/die_plan/test_sdc_lint 41 PASS.
* lanes__canon TT rerun (sta_a/sta.log, SDC = 3_place.sdc with the 5 reset lines at 166.6):
  reset recovery worst -464.6 -> -214.8 ps; WNS now -254.4 (u_m2 reg2reg); TNS -1.375M -> -0.869M.
  The remaining -214.8 is a 12-buffer pre-CTS placement reset chain (input -> 11 BUFx6f -> lane3 RESETN, ~600 ps)
  with the capture clock IDEAL (0 ps) against vclk source latency 250: after CTS the ~250 ps core insertion is on
  the capture side, est. +35 ps (UNCHECKED until CTS). Structural follow-up if it stays negative: the 12.x reset rule's
  in-core pin register + relay tree (reset pins are skipped by face_flops today).
* Other dies' kit generators (KV gen_core_kit_kv.py, S81 gen_core_kit*.py, QC legacy, hbm/cores/harden) carry the same
  0.5*per reset line; not touched (die owners).

## (c) lane multiplier depth -- ESTIMATE + finding, not adopted
* sta_a/sta_mul.log: EVERY LAT-4 lane multiplier fails at its first stage s1_rows, not only u_m2:
  u_m2 -254.4, u_m1 -242.5, u_e1m -214.3, u_me2 -166.9, u_q -118.4 ps. Start points = the command pin registers d_q
  (u_lane2.d_q[184] drives u_lane1's u_m2: a command register shared across lanes, buffer fanouts 3/3/14/14/21) and the stage delay lines; then the operand multiplexer +
  Booth rows (23 levels). This is the case ot_hdc_fp32_mul_lat5i exists for (input cut: operand mux shares a stage with
  decode, not with the partial products; bit-identical, 21d9aab2). So the structural fix is the lane's MLAT 4 -> 5
  (all multiplying stages), not u_m2 alone.
* Price (price/price.json, historical d4g_2ring_qbg priced_layers model, the price_su31_calendar.py baseline, applied to
  all 1356 SU-executing records/token, 702 SFU-using; UNCHECKED model sensitivity, serial upper bound):
  baseline 1902.26 tok/s; (b) write commit +1: -0.09 %; (c) MLAT5 (+4 per lane element, SFU +18 upper): -0.83 %;
  (b)+(c): 1884.7 tok/s, -0.92 % (SFU +7 instead of +18: -0.65 %). Below the 5 % COORD threshold, but in absolute terms
  below the owner-accepted 1906 floor of planU3f -> stated for COORD.
* NOT done: lanes4 core regen at MLAT 5 (build_split_tops.py from r18h5 views.json), compiler constants
  (tools/hbm_static/toksim_su/suvop/prod_compile.py MLAT/LIN, tools/hbm_layer_vehicle/layer_images.py FO), token check.

## (b) write-data broadcast -- RTL opt-in DONE + bench, not adopted
* ot_hbm_su_static_replicated_bank / _pinned_bank / _bank6_clock_physical: opt-in WCOPY (default 0): each replica
  column registers write_v/addr/data itself (on the word-select clock, beside its SRAM), so the single wd_pin register
  no longer fans 32 bits x 48 SRAM data pins across the 6 columns. Write commit n+1 -> n+2; reads unchanged (n -> n+2).
* Default unchanged: yosys equiv vs origin/main, SRAM blackbox: bank6_clock_physical 4208/4208, pinned_bank 3897/3897
  PROVEN (eq/).
* Bench (tools/hbm_static/su_bank_run.sh, SU_BANK_GPARAMS): default PASS 3613 checks (commit 1); WCOPY=1 PASS 3619
  (commit 2, extra old-word read checked); mutants all CAUGHT: latency WCOPY=1/EXP_WC=1 FAIL 6, WCOPY=0/EXP_WC=2 FAIL 6,
  WCOPY=1 + coherence 516, reset 6, return 2, clock_halt 12, rd_halt 24, ws_halt 24.
* NOT done: compiler FILL commit E+RR+3 -> +4 (prod_compile FPIN, layer_images write_port_guard), token check, kit regen.

## (d) re-place -- NOT started (nothing adoptable yet: (b)/(c) need the schedule regen + token check first).
