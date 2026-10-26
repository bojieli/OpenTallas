#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for n in 2 3;do
 "$v" --binary --timing -j 2 -Wno-fatal --top-module tb_tkx_pinreg -GLINK_STAGES=$n --Mdir "$o/obj$n" tools/hbm_b2/tkm_l74/tb_tkx_pinreg.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat{,_pr}.sv rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/ot_hbm_face_reg.sv > "$o/build$n.log" 2>&1
 for m in BASE BAD_PRICE MUT_PHASE MUT_BANK;do
  args=();[ "$m" = BASE ] || args+=(+$m)
  set +e;"$o/obj$n/Vtb_tkx_pinreg" "${args[@]}" > "$o/N${n}_${m}.log" 2>&1;rc=$?;set -e
  if [ "$m" = BASE ];then [ "$rc" = 0 ] || { cat "$o/N${n}_${m}.log";exit 1; };else [ "$rc" != 0 ] || { echo "$m SURVIVED";exit 1; };fi
  head -3 "$o/N${n}_${m}.log"
 done
done
