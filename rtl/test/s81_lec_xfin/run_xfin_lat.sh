#!/bin/bash
# usage: run_xfin_lat.sh WT KITRTL OUT [iverilog defines...]
W=$1; KR=$2; O=$3; shift 3; mkdir -p $O; cd $O
git -C $W show 2c2cb26e06:rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv | awk '/^module ot_s81dv_eng_finish/{p=1} p{print} p&&/^endmodule/{exit}' | sed 's/module ot_s81dv_eng_finish #(/module gold_eng_finish #(/' > gold_ef.sv
awk '/^module ot_s81dv_eng_finish/{p=1} p{print} p&&/^endmodule/{exit}' $W/rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv > new_ef.sv
for f in gold_ef.sv new_ef.sv; do sed -i 's/ca(n)/(2*n)/g; s/cb(n)/(2*n+1)/g' $f; done
S=$(ls $KR/*.sv | grep -v ot_s81dv_norm.sv | tr '\n' ' ')
iverilog -g2012 "$@" -o sim -s tb $(dirname $(readlink -f $0))/tb_lat.sv gold_ef.sv new_ef.sv $S 2>&1 | grep -iv warn | head -20
for s in 1 2 3; do vvp -n sim +seed=$s | grep -E "XFIN_LAT|MISMATCH|EXTRA" | head -4; done
