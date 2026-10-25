#!/bin/bash
# CLOCK-RESET/argmax 2026-10-25: STRUCT=1 vs STRUCT=0 lockstep (several FLAT/FAST/seeds) + the existing argmax18 bench
# with STRUCT=1 + mutants (each must FAIL).  usage: run_struct_lockstep.sh OUTDIR
set -uo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
A=physical/hbm_generic/argmax18
SRC="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/gpu/ot_gpu_fadd.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv"
fail=0
ls_run() { # tag value.sv FLAT FAST SEED
  iverilog -g2012 -s tb_argmax18_struct_lockstep -P tb_argmax18_struct_lockstep.FLAT=$3 -P tb_argmax18_struct_lockstep.FAST=$4 \
    -P tb_argmax18_struct_lockstep.SEED=$5 -o "$out/$1.vvp" $SRC "$2" $A/rtl/ot_hgi_argmax18_m.sv $A/bench/tb_argmax18_struct_lockstep.sv > "$out/$1.build.log" 2>&1 || { echo "$1 BUILD FAIL"; cat "$out/$1.build.log"; return 2; }
  vvp -n "$out/$1.vvp" > "$out/$1.log" 2>&1; tail -1 "$out/$1.log" | sed "s/^/$1 /"
  grep -q "PASS$" "$out/$1.log"
}
for cfg in "7 1 1" "7 1 2" "7 1 3" "7 0 4" "4 1 5" "2 1 6" "2 0 7"; do set -- $cfg
  ls_run ls_f$1_a$2_s$3 $A/rtl/ot_hgi_argmax18_value_m.sv $1 $2 $3 || fail=1; done
# mutants (must FAIL): M1 ring pointer reset one slot late; M2 key-group bvalid replica drops the row-restart clear;
# M3 bits-group fin replica fires on every valid beat
cp $A/rtl/ot_hgi_argmax18_value_m.sv "$out/m1.sv"; sed -i "s/q <= {{(N-1){1'b0}}, 1'b1}; else/q <= {{(N-2){1'b0}}, 2'b10}; else/" "$out/m1.sv"
cp $A/rtl/ot_hgi_argmax18_value_m.sv "$out/m2.sv"; sed -i "s/u_bvk (.clk(clk), .rst_n(rst_n), .d(bvalid_d\[gr\])/u_bvk (.clk(clk), .rst_n(rst_n), .d(bvalid_d[gr] | bvalid[gr])/" "$out/m2.sv"
cp $A/rtl/ot_hgi_argmax18_value_m.sv "$out/m3.sv"; sed -i "s/u_fb  (.clk(clk), .rst_n(rst_n), .d(fin_d)/u_fb  (.clk(clk), .rst_n(rst_n), .d(e_v)/" "$out/m3.sv"
for m in m1 m2 m3; do cmp -s "$out/$m.sv" $A/rtl/ot_hgi_argmax18_value_m.sv && { echo "$m NOT APPLIED"; fail=1; continue; }
  if ls_run mut_$m "$out/$m.sv" 7 1 11; then echo "$m MUTANT SURVIVED"; fail=1; else echo "$m mutant caught"; fi; done
# existing functional bench (golden rows + DS lockstep) with the wrapper defaulting to STRUCT=1
mkdir -p "$out/b18"; cp $A/rtl/ot_hgi_argmax18_m.sv "$out/b18/wrapper.sv"; sed -i 's/parameter integer STRUCT=0/parameter integer STRUCT=1/' "$out/b18/wrapper.sv"
grep -q "STRUCT=1 " "$out/b18/wrapper.sv" || { echo "b18 wrapper patch failed"; fail=1; }
iverilog -g2012 -s tb_hgi_argmax18 -o "$out/b18/bench.vvp" $SRC $A/rtl/ot_hgi_argmax18_value_m.sv "$out/b18/wrapper.sv" $A/bench/tb_hgi_argmax18.sv > "$out/b18/build.log" 2>&1 \
  && vvp -n "$out/b18/bench.vvp" > "$out/b18/sim.log" 2>&1; rc=$?; echo "argmax18 bench STRUCT=1 rc=$rc: $(tail -1 $out/b18/sim.log)"; [ $rc = 0 ] || fail=1
echo "STRUCT_LOCKSTEP $([ $fail = 0 ] && echo PASS || echo FAIL)"; exit $fail
