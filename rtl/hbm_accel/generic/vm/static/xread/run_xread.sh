#!/usr/bin/env bash
# DIE-HBM-10 one-owner crossing read bench: positive must PASS, every mutant must FATAL.
set -uo pipefail
cd "$(dirname "$0")/../../../../../.."
D=rtl/hbm_accel/generic/vm/static
O=${1:?output dir required}; mkdir -p "$O"
src=("$D"/xread/hfd_vms_xread_link.sv "$D"/xread/tb_vms_xread_link.sv "$D"/faces_q0/hfd_vms_bank_native_q0_faces.sv
     "$D"/faces_q0/ot_vms_bank_q0_faces_core.sv "$D"/faces_q0/ot_vms_bank_q0_faces_body.sv "$D"/ot_vms_ce_counter_pipe.sv
     physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
ok=1
for c in positive:0:0 link_short:1:0 link_swap:2:0 link_bitflip:3:0 tie_live:0:1; do
  IFS=: read n l t <<<"$c"
  iverilog -g2012 -s tb_vms_xread_link -Ptb_vms_xread_link.LMUT=$l -Ptb_vms_xread_link.TMUT=$t -o "$O/$n.vvp" "${src[@]}" >"$O/$n.build.log" 2>&1 || { echo "$n BUILD FAIL"; cat "$O/$n.build.log"|head; ok=0; continue; }
  rc=0; vvp "$O/$n.vvp" >"$O/$n.log" 2>&1 || rc=$?
  echo "$n rc=$rc $(grep -m1 -E 'PASS|FATAL' "$O/$n.log")"
  if [[ $n = positive ]]; then grep -q 'XREAD_LINK PASS' "$O/$n.log" && [[ $rc = 0 ]] || ok=0
  else { [[ $rc != 0 ]] && grep -q FATAL "$O/$n.log"; } || { echo "  MUTANT $n NOT CAUGHT"; ok=0; }; fi
done
[[ $ok = 1 ]] && echo "XREAD BENCH PASS: positive accepted, 4 mutants rejected" || { echo "XREAD BENCH FAIL"; exit 1; }
