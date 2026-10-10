#!/bin/bash
# hgi-1010/d5: exact gate of ot_hgi_quant_vm_transport_p (pipelined transport, SRAM result FIFO).
# usage: tools/hgi_quant_vm_transport_p_bench.sh OUT [MUTANTS...]   (default 0 1 2 3 5 6; 0 must PASS, every other FAIL)
#   transport bench: 458 cases (arbitrary CP stall, ACK delay, strided / multirow, tail16/48, illegal UE) + vectors
#   connected bench (ot_hgi_quant_unit PIPE=1 -> real ECC VM unit, 5,888 words): TMUT 0 PASS, 4 / 5 FAIL
#   (MUTANT 6 is caught by the transport bench's random CP stalls; the connected VM never exposes the landing gap)
set -uo pipefail
out=$1; shift; [ "${1:-}" = "--one" ] && mut="" || mut=${*:-0 1 2 3 5 6}
mkdir -p "$out"
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
mem=(rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
src=("${hdc[@]}" "${mem[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/hbm_accel/generic/ot_hgi_quant_vm_transport_p.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv rtl/test/hbm_accel/generic/tb_hgi_quant_vm_transport.sv)
tr() {
 m=$1
 for try in 1 2 3; do   # verilator 5.x internal faults intermittently on this tree under load: rebuild clean
  rm -rf "$out/t$m.obj"
  verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -DPIPE -DMUTANT=$m --top-module tb_hgi_quant_vm_transport -Mdir "$out/t$m.obj" -o sim "${src[@]}" > "$out/t$m.build" 2>&1 && break
 done
 "$out/t$m.obj/sim" +VECTORS=results/hgi_generic/cf_qdq_891b4b555 > "$out/t$m.log" 2>&1; echo $? > "$out/t$m.rc"
}
csrc=(rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_sfu.sv physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hbm_accel/generic/ot_hgi_quant_vm_transport.sv rtl/hbm_accel/generic/ot_hgi_quant_vm_transport_p.sv rtl/link/ot_fifo_sram_fwft.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv rtl/hbm_accel/generic/ot_hgi_quant_unit.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/test/hbm_accel/generic/tb_hgi_quant_vm_connected.sv)
co() {
 m=$1
 iverilog -g2012 -I rtl/hbm_accel/generic -Ptb_hgi_quant_vm_connected.PIPE=1 -Ptb_hgi_quant_vm_connected.TMUT=$m -o "$out/c$m.vvp" -s tb_hgi_quant_vm_connected "${csrc[@]}" > "$out/c$m.build" 2>&1 && vvp "$out/c$m.vvp" > "$out/c$m.log" 2>&1; echo $? > "$out/c$m.rc"
}
if [ "${1:-}" = "--one" ]; then   # closure-loop mutant bench: one transport mutant, exit = its sim rc (expect FAIL)
 m=$2; tr $m; cat $out/t$m.log | tail -3
 grep -Eq 'WRITE mismatch|DROP/CREDIT|EARLY_DONE|unexpected fault|FAULT' $out/t$m.log || exit 0
 exit 1
fi
for m in $mut; do tr $m & done
for m in 0 4 5; do co $m & done
wait
ok=1
for m in $mut; do r=$(cat $out/t$m.rc); if [ $m = 0 ]; then grep -q 'PASS QUANT_TRANSPORT' $out/t$m.log || ok=0; else { [ "$r" != 0 ] && ! grep -q 'PASS QUANT_TRANSPORT' $out/t$m.log && grep -Eq 'WRITE mismatch|DROP/CREDIT|EARLY_DONE|unexpected fault|FAULT' $out/t$m.log; } || ok=0; fi; echo "transport MUTANT $m rc=$r $(grep -m1 -E 'PASS|FATAL|mismatch|timeout|fault' $out/t$m.log)"; done
for m in 0 4 5; do r=$(cat $out/c$m.rc); if [ $m = 0 ]; then grep -q 'PASS HGI-QUANT-VM' $out/c$m.log || ok=0; else { ! grep -q 'PASS HGI-QUANT-VM' $out/c$m.log && grep -q 'FATAL' $out/c$m.log; } || ok=0; fi; echo "connected TMUT $m rc=$r $(grep -m1 -E 'PASS|FATAL|mismatch|timeout|fault' $out/c$m.log)"; done
[ $ok = 1 ] && echo GATE PASS || { echo GATE FAIL; exit 1; }
