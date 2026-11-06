#!/bin/bash
# run_lfw.sh WT OUT: lf (B11) vs ot_hgi_su_lgroup2 at opsb_output params; lf0 PASS, lf1 (lowest lane wins) lf2 (no row carry) lf3 (no lane row-collision) FAIL
W=$1; O=$2; H=$(cd "$(dirname "$0")"; pwd); V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; mkdir -p $O
P=$W/results/die_hbm_1105/form_split/p27_lf
for m in 0 1 2 3; do ( d=$O/m$m; rm -rf $d; $V --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir $d -o sim $H/tb_lfw.sv $H/tops.sv $P/lbank_fake.sv $P/lg2_orig.sv $H/lf$m.sv > $d.b.log 2>&1 || { echo "m$m BUILD FAIL"; tail -3 $d.b.log; exit; }; timeout 1800 $d/sim > $d.r.log 2>&1; echo "m$m rc=$? $(grep LOCKSTEP $d.r.log)" ) & done; wait
