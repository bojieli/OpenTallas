#!/bin/bash
# eq_off.sh: yosys equiv, ot_svgr_top_cachecut RRMIR=0 (new file) vs the vL7 file, vL7 kit parameters, SRAMs black boxes.
B=$(cd "$(dirname "$0")" && pwd); cd /
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
K=$B/rtl; SUB="$K/ot_hbm_svc_sm_issuer_rel.sv $K/ot_smh_calendar_static_x.sv $K/ot_smh_static_feed.sv $K/ot_reset_sync.sv $B/ref/ot_svgr_cache136_native.sv"
CP="-chparam LBANKS 4 -chparam NID 6 -chparam IDW 9 -chparam PAW 11 -chparam PREL 1 -chparam DD 256 -chparam ID_COHORT 1 -chparam XSLOT 1 -chparam OPEN_IL 1 -chparam CACHE_RW_SRAM 1 -chparam P1 1 -chparam CACHE_WDEC 1 -chparam CACHE_GSEL 1 -chparam CACHE_GREP 2"
cat > $B/eq_off.ys <<EOT
read_verilog -sv $B/bb.v
read_verilog -sv $B/ref/ot_svgr_top_cachecut.sv $SUB
hierarchy -top ot_svgr_top_cachecut $CP
proc; flatten; async2sync; opt_clean; rename ot_svgr_top_cachecut gold; design -stash gold
read_verilog -sv $B/bb.v
read_verilog -sv $B/dut/ot_svgr_top_cachecut.sv $SUB
hierarchy -top ot_svgr_top_cachecut $CP
proc; flatten; async2sync; opt_clean; rename ot_svgr_top_cachecut gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 5; equiv_struct; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
EOT
timeout 3600 prlimit --as=24000000000 nice -n 10 $Y -q -l $B/eq_off.log -p "script $B/eq_off.ys" > /dev/null 2>&1; echo "EQOFF rc $? $(date)" >> $B/eq_off.rc
grep -E "Found|proven|unproven|Equivalence successfully" $B/eq_off.log | tail -5 >> $B/eq_off.rc
