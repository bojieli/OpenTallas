#!/usr/bin/env bash
# HBM-TOK8: build tb_r6q once (Verilator 5.050), run q0..q3 of the R6 compiler fixture.
set -u
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VL --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir obj -j 4 +libext+.sv+.v \
  -y snap/rtl -y snap/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 $(for d in snap/physical/asap7_memory_macros/*/; do echo -y $d; done) -y snap/rtl/lib -y snap/rtl/hbm_accel/generic/adapters/static_su -y snap/rtl/hbm_accel/generic/adapters/static_su/programme \
  snap/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme_pgcol.sv tb_r6q.sv > build.log 2>&1 || { tail -20 build.log; exit 2; }
for C in config config_ib4; do G=64; for q in 0 1 2 3; do ./obj/Vtb +GAP=$G +NCFG=$(grep -c . q$q/cols/config.mem) +CFG=q$q/cols/$C.mem +EXP=q$q/quarter.mem > run_q$q.log 2>&1; cp run_q$q.log run_q${q}_$C.log; echo "$C q$q $(grep R6Q_DONE run_q$q.log)"; done; done
