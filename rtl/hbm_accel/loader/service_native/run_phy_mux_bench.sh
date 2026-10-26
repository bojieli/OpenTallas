#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
iverilog -g2012 -s tb_hbm_svc_phy_mux -o "$out/positive.vvp" "$d/ot_hbm_svc_phy_mux.sv" "$d/tb_hbm_svc_phy_mux.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'PHY_MUX PASS' "$out/positive.log"
sed 's/held\[p\]?held_wb\[p\]:/(1\x27b0)?held_wb[p]:/' "$d/ot_hbm_svc_phy_mux.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_phy_mux.sv";then exit 1;fi
iverilog -g2012 -s tb_hbm_svc_phy_mux -o "$out/mutant.vvp" "$out/mutant.sv" "$d/tb_hbm_svc_phy_mux.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log";then echo 'mutant passed unexpectedly';exit 1;fi
grep -q 'mux ownership' "$out/mutant.log"
yosys -Q -q -p "read_verilog -sv $d/ot_hbm_svc_phy_mux.sv; hierarchy -check -top ot_hbm_svc_phy_mux; proc; check -assert" > "$out/yosys.log" 2>&1
cat "$out/positive.log"
echo 'PHY_MUX_MUTANT rejected changed owner under stall'
