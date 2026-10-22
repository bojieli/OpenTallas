#!/usr/bin/env bash
set -u
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd);cd "$ROOT"
C=rtl/hbm_accel/generic/collective/tkm
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
sha256sum "$C/ot_hgi_coll_tkm.sv" "$C/tb_tkm_e86_v5_fourstate.sv" "$C/tb_hgi_coll_tkm_tile_rg_crep.sv" "$C/run_tile_rg_crep.sh" "$C/ot_hgi_coll_tkm_tile_e86_v6.sv" "$0" > "$OUT/sources.sha256"
iverilog -g2012 -s tb_tkm_e86_v5_fourstate -o "$OUT/fourstate" "$C/tb_tkm_e86_v5_fourstate.sv" "$C/ot_hgi_coll_tkm.sv" > "$OUT/fourstate.build.log" 2>&1 || exit 2
vvp -n "$OUT/fourstate" > "$OUT/fourstate.log" 2>&1 || exit 2
grep -q 'E86_V6_FOURSTATE PASS' "$OUT/fourstate.log" || exit 2
cat "$OUT/fourstate.log"
for m in 0 1 3 4 5 6;do
 FAN32=2 SEAM=1 LT_GROUP=5 GCFOLD=1 KLEAF=1 bash "$C/run_tile_rg_crep.sh" "$OUT/m$m" 4000 "$m" > "$OUT/m$m.summary.log" 2>&1
 rc=$?;cat "$OUT/m$m.summary.log"
 if [ "$m" = 0 ];then [ "$rc" = 0 ] || exit 3;else [ "$rc" = 1 ] || exit 4;fi
 echo "E86_V6_CASE m=$m rc=$rc QUALIFIED"
done
echo 'E86_V6_SOURCE_QUAL PASS'
