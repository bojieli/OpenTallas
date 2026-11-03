#!/bin/bash
# qcen SFR0 vs SFR1 lockstep: base + negative controls (SH 1/3) + mutant (lfd not lengthened)
W=/home/ubuntu/scratch-root/claude/dhbm61-st32-work; cd $W; export PATH=$HOME/.local/opentallas-tools/bin:$PATH
S=../die-hbm-61-rtl-st32/rtl; Q=$S/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qcen_static.sv
sed 's/localparam int SH = 2, NCYC/parameter int SH = 2; localparam int NCYC/' tb_qcen.sv > qc/tb_qcen_p.sv
sed 's/lfd\[LT\*TLA+SFD-1\]/lfd[LT*TLA-1]/' $Q > qc/mut_lfd.sv; cmp -s $Q qc/mut_lfd.sv && { echo mut_lfd unchanged; exit 1; }
one() { n=$1; q=$2; sh=$3; exp=$4; d=qc/b_$n
  systemd-run --user --scope -q -p MemoryMax=16G verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -GSH=$sh --top-module tb -Mdir $d -o tb qc/tb_qcen_p.sv $q $S/hdc/ot_hdc_fp32_add_lat.sv $S/hdc/ot_hdc_fastfp.sv $S/hdc/ot_hdc_prefix.sv $S/lib/ot_rst_relay.sv > $d.build.log 2>&1 || { echo "$n BUILD_FAIL"; return; }
  $d/tb > $d.run.log 2>&1; echo "$n expect=$exp rc=$?: $(grep QCEN_LOCKSTEP $d.run.log)"; }
one base $Q 2 pass & one sh1 $Q 1 fail & one sh3 $Q 3 fail & one mut_lfd qc/mut_lfd.sv 2 fail & wait
