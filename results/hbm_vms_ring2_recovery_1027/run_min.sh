#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);OUT=${1:?scratch out}
REF=$ROOT/results/hbm_vms_ring2_recovery_1027/ref
mkdir -p "$OUT"
cd rtl/hbm_accel/generic/vm/static
sed -E 's/\b(ot_vms_slice_static_glue|ot_vms_hub_static|ot_vms_rstop_static|hfd_hgi_vms_static_(SW|NW|SE|NE)_glue)\b/\1_ref/g' "$REF/ot_vms_rstop_static.sv" "$REF/ot_vms_hub_static.sv" "$REF/hfd_hgi_vms_static_glue.sv" > "$OUT/ref.sv"
COMMON=(ot_vms_rstop_static.sv ot_vms_hub_static.sv ot_vms_rcl_static.sv ot_vms_status_static.sv hfd_hgi_vms_static_glue.sv)
for m in 0 1 2 3;do
  iverilog -g2012 -s tb_vms_ring2_default_eq -Ptb_vms_ring2_default_eq.MUT=$m -o "$OUT/eq$m.vvp" "${COMMON[@]}" "$OUT/ref.sv" tb_vms_ring2_default_eq.sv > "$OUT/eq$m.build" 2>&1
  vvp "$OUT/eq$m.vvp" > "$OUT/eq$m.log" 2>&1 || true
  if test "$m" = 0;then grep -q 'VMS_RING2_EQ PASS' "$OUT/eq$m.log";else grep -Eq 'VMS_RING2_EQ FAIL .*errors=[1-9]' "$OUT/eq$m.log";fi
  grep 'VMS_RING2_EQ ' "$OUT/eq$m.log"
done
for config in 'nom_l3 LINK=3' 'nom_l26 LINK=26' 'mut_payload LINK=3 RMUT=1' 'mut_ack LINK=3 HMUT=5';do
  read -ra f <<< "$config";tag=${f[0]};P=()
  for v in "${f[@]:1}";do P+=("-Ptb_vms_ring2_static.$v");done
  iverilog -g2012 -s tb_vms_ring2_static "${P[@]}" -o "$OUT/$tag.vvp" "${COMMON[@]}" hfd_hgi_vms_ring2_glue.sv tb_vms_ring2_static.sv > "$OUT/$tag.build" 2>&1
  vvp "$OUT/$tag.vvp" > "$OUT/$tag.log" 2>&1 || true
  if [[ "$tag" = nom* ]];then grep -q 'VMS_RING2 PASS' "$OUT/$tag.log";else grep -Eq 'VMS_RING2 FAIL .*errors=[1-9]' "$OUT/$tag.log";fi
  grep 'VMS_RING2 \(PASS\|FAIL\)' "$OUT/$tag.log" | tail -1
done
echo NATIVE_VMS_RING2_MINIMUM_GATE_PASS
