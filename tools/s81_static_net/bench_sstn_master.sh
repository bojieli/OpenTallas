#!/usr/bin/env bash
# S-NET production bench of a generated dsfd_sstn_* / dsfd_rstg master (--sstn-reg form).
#   bench_sstn_master.sh pass|mut_noreset MASTER GLUE_SV OUT      (mutant: the valid flop loses its column reset)
set -eu
cd "$(dirname "$0")/../.."
mode=${1:?}; mst=${2:?}; glue=${3:?}; out=${4:?}; mkdir -p "$out"
awk "/^module $mst /,/^endmodule/" "$glue" > "$out/master.sv"
grep -qE "& rs\[0\]" "$out/master.sv" && { echo "SSTN_REG FAIL logic behind the output flop (rs AND) in $mst"; exit 1; }
if [ $mode = mut_noreset ]; then
  sed -i "s/if (!rs\[0\]) xv <= 1'b0; else xv <= xai\[282\];/xv <= xai[282];/; s/if (!rs\[0\]) v <= 1'b0; else v <= i\[0\];/v <= i[0];/" "$out/master.sv"
fi
defs="-DDUT=$mst"
case $mst in dsfd_rstg*) defs="$defs -DRSTG";; esac
grep -q "output wire \[14:0\] cc" "$out/master.sv" && defs="$defs -DHAS_CC"
grep -q "input wire \[1:0\] e1" "$out/master.sv" && defs="$defs -DHAS_E1"
grep -q "input wire \[1:0\] si" "$out/master.sv" && defs="$defs -DHAS_SI"
grep -q "input wire \[0:0\] nf" "$out/master.sv" && defs="$defs -DHAS_NF"
[[ $mst == *_cp1* ]] && defs="$defs -DCP"
iverilog -g2012 $defs -s tb_dsfd_sstn_reg -o "$out/sim" "$out/master.sv" rtl/dsrom_sys/s81_static_net/test/tb_dsfd_sstn_reg.sv
if vvp -n "$out/sim" > "$out/log" 2>&1 && grep -q "SSTN_REG PASS" "$out/log"; then r=PASS; else r=FAIL; fi
grep -m3 "SSTN_REG" "$out/log" || tail -2 "$out/log"
if [ $mode = pass ]; then [ $r = PASS ] && echo "SSTN_REG_GATE PASS $mst" || { echo "SSTN_REG_GATE FAIL $mst"; exit 1; }
else [ $r = FAIL ] && echo "SSTN_REG_GATE MUTANT REJECTED $mst" || { echo "SSTN_REG_GATE MUTANT ESCAPED $mst"; exit 1; }; fi
