#!/bin/bash
# IDX index-key stream issuer bench (hgi-1010/g): tools/hgi_unit_tput/run_iks.sh <out dir>   (from the repo root)
# q0 (quarter 0, 342 blocks), q3 (quarter 3, 99 blocks at N 9000), q3m (issuer MUT 1, must FAIL), q0a (adversarial
# controller stalls + delayed credits, exactness only).
set -euo pipefail
out=$(realpath -m "$1"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
Y="-y rtl/hbm_accel/service -y rtl/hbm_accel/loader/service_native -y physical/hbm_accel_die_views/svc/rtl -y physical/hbm_accel_die_views/common"
declare -A G=([q0]="-GQSEL=0" [q3]="-GQSEL=3" [q3m]="-GQSEL=3 -GMUT=1" [qmis]="-GQSEL=0 -GMISALIGN=4096")
for v in q0 q3 q3m qmis; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD ${G[$v]} --top-module tb_hgi_idx_iks $Y \
    -Mdir "$out/$v.obj" -o sim rtl/hbm_accel/generic/idx/ot_hgi_idx_iks_issue.sv rtl/hbm_accel/generic/idx/tb_hgi_idx_iks.sv \
    > "$out/$v.build" 2>&1 &
done
wait
"$out/q0.obj/sim" > "$out/q0.log" 2>&1 || true
"$out/q3.obj/sim" > "$out/q3.log" 2>&1 || true
"$out/q3m.obj/sim" > "$out/q3m.log" 2>&1 || true
"$out/qmis.obj/sim" > "$out/qmis.log" 2>&1 || true
"$out/q0.obj/sim" +ADV=1 > "$out/q0a.log" 2>&1 || true
ok=1
for v in q0 q3 q0a; do grep -q "PASS HGI_IDX_IKS" "$out/$v.log" || ok=0; done
for v in q3m qmis; do grep -q "PASS HGI_IDX_IKS" "$out/$v.log" && ok=0; done
[ $ok = 1 ] && echo "IKS GATE PASS (q0/q3/q0a PASS, q3m/qmis FAIL)" | tee "$out/gate" || { echo "IKS GATE FAIL" | tee "$out/gate"; exit 1; }
