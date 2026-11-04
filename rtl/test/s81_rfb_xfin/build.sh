#!/bin/bash
# RF-B xfin lockstep bench: gold = 8f0bf2371d eng_finish (current kit form), new = branch eng_finish (predecode + out-face latch)
cd $(dirname $0); W=../wt
git -C $W show 8f0bf2371d:rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv | awk "/^module ot_s81dv_eng_finish/{p=1} p{print} p&&/^endmodule/{exit}" | sed "s/module ot_s81dv_eng_finish #(/module gold_eng_finish #(/" > gold_ef.sv
awk "/^module ot_s81dv_eng_finish/{p=1} p{print} p&&/^endmodule/{exit}" $W/rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv > new_ef.sv
for f in gold_ef.sv new_ef.sv; do sed -i "s/ca(n)/(2*n)/g; s/cb(n)/(2*n+1)/g" $f; done
S=$(tr " " "\n" < srcs.txt | grep -v ot_s81dv_norm.sv | tr "\n" " ")
iverilog -g2012 $@ -o sim_new${MUT:+_mut} -s tb tb.sv gold_ef.sv new_ef.sv $S 2>&1 | grep -iv warn
