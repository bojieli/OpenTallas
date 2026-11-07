#!/bin/bash
# eq_off.sh REF_CACHE DUT_CACHE WORKDIR [WDEC GSEL GREP WPIPE]: yosys 0.68 equiv_make/struct/simple/induct of
# ot_svgr_cache136_native (DUT, given params; default all 0 = off, WPIPE 1) vs the vL6 copy (REF), PACKED136=1 RW_SRAM=1.
# The SRAM macro cells are deleted after equiv_make (their outputs are matched by name, so both sides read one free value;
# their input nets keep their own $equiv cells).
set -u; R=$1; D=$2; B=$3; W=${4:-0}; G=${5:-0}; P=${6:-1}; Q=${7:-1}; H=$(cd "$(dirname "$0")" && pwd); cd /; mkdir -p $B
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
sed -e 's/\bmodule ot_svgr_cache136_native\b/module ot_svgr_cache136_native_ref/' $R > $B/ref_cache.sv
cat > $B/eq_$W$G$P$Q.ys <<EOT
read_verilog -sv $H/sram_bb.v
read_verilog -sv -mem2reg $B/ref_cache.sv
chparam -set PACKED136 1 -set RW_SRAM 1 -set WPIPE $Q ot_svgr_cache136_native_ref
read_verilog -sv -mem2reg $D
chparam -set PACKED136 1 -set RW_SRAM 1 -set WPIPE $Q -set WDECOUPLE $W -set GSEL $G -set GREP $P ot_svgr_cache136_native
proc; opt_clean; memory -nomap; memory_map; opt -fast
flatten; opt -fast
async2sync
equiv_make -inames ot_svgr_cache136_native_ref ot_svgr_cache136_native eqm
hierarchy -top eqm
delete eqm/t:ot_sram*
equiv_struct
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status
EOT
timeout ${EQ_TIMEOUT:-7200} $Y -q -l $B/eq_$W$G$P$Q.log $B/eq_$W$G$P$Q.ys >/dev/null 2>&1; echo "yosys_rc=$?"
grep -E "Found|unproven|successfully|^ERROR" $B/eq_$W$G$P$Q.log | tail -4
