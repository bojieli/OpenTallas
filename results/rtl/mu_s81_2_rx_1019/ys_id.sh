#!/bin/bash
# MU_EN 0 netlist identity: generic synth of ot_s81sl_lep / ot_s81sl_lep_nh from the old and new lep source
set -u; mkdir -p ysid
C="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv"
for top in ot_s81sl_lep ot_s81sl_lep_nh; do for v in old new; do
  f=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv; [ $v = old ] && f=lep_old.sv
  yosys -q -p "read_verilog -sv -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v; read_verilog -sv $C $f; synth -top $top -flatten -run begin:fine; opt_clean -purge; write_verilog -noattr ysid/${top}_$v.v; stat" > ysid/${top}_$v.log 2>&1 || echo "YOSYS_FAIL $top $v"
done
if cmp -s ysid/${top}_old.v ysid/${top}_new.v; then echo "IDENTICAL $top $(md5sum < ysid/${top}_new.v | cut -c1-12) $(wc -l < ysid/${top}_new.v) lines"; else echo "DIFFER $top"; diff ysid/${top}_old.v ysid/${top}_new.v | head -20; fi
done
