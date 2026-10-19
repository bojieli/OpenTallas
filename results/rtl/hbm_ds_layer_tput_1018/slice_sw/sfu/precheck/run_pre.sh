#!/usr/bin/env bash
# VEH-FMT-COLL2/SFU pre-check: tb_sfu_collar on the sw2 bundle masters (Verilator 5.050), positive + 2 mutants
set -u
H=$(cd "$(dirname "$0")" && pwd); B=/srv/opentallas-scratch/claude/layerbench-hbm/sw2
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
LIB=("$B/masters/ot_hbm_static_cfg_collar.sv" "$B/masters/ot_hgi_sfu_programme_store_r10.sv")
read NC NI < $H/len.txt
sha256sum "${LIB[@]}" $H/tb_sfu_collar.sv $H/ctl.hex $H/io.hex $H/*.events.txt > $H/sources.sha256
"$V" --version > $H/build.log
"$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP -Wno-TIMESCALEMOD \
  -GNCTL=$NC -GNIO=$NI --top-module tb_sfu_collar --Mdir $H/obj $H/tb_sfu_collar.sv "${LIB[@]}" >> $H/build.log 2>&1 || { tail -30 $H/build.log; exit 2; }
for n in pos mut_compact mut_bit; do
  (cd $H && ./obj/Vtb_sfu_collar +EV=$n.events.txt > $n.log 2>&1)
  echo "$n: $(grep -m1 -E '^SFUCOL (PASS|FAIL)' $H/$n.log)"; grep -E '^SFUCOL (launch|collar)|MISMATCH' $H/$n.log | head -4
done
