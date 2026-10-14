#!/usr/bin/env bash
# hgi-1010/c2 (AUDIT N1 / N2 / N5): die-master benches of the HGI record-unit die views.
#   usage: run_hgi_die_masters.sh <outdir> <case>      case: fused | fused_mut | su | su_mut | sfu | hc_lock
#   fused / fused_mut  tb_hgi_fused_station on hfd_quant (quant_hgi view; fused_mut: the wrapper regenerated with the
#                      station's MUT 1 = wl lane from the wrong sector bits: must FAIL)
#   fused_hce          el1011-hbm-fused: the same bench + hfd_hc_eng (HCE 2 over fused_ne), LANE_LOAD, the d 5120 HC
#                      cases only (FUSED_HC_ONLY FUSED_ONLY_D=5120 FUSED_HLL=1); fused_hce_m4 / fused_hce_m2: the hc_eng view
#                      regenerated at engine MUT 4 (retire before the writes land) / MUT 2 (lane-0 row swap): must FAIL
#   su / su_mut / sfu  tb_hgi_su_die on hfd_su / hfd_sfu (su_mut: the bench unpacks the rdn tap in another order: FAIL)
#   hc_lock            the hbm_die_wrap lockstep bench of hfd_hc (binding only: HC weights are open, AUDIT N3)
# Vectors and file lists are prepared by prep (needs the repo's python deps): run_hgi_die_masters.sh <outdir> prep
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); CASE=$2
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
V=physical/hbm_accel_die_views
mkdir -p "$OUT"; cd "$ROOT"
if [ "$CASE" = prep ]; then
  FUSED_HLL=1 python3 tools/hgi_adapters/fused_bench.py --out "$OUT/fuvec" > "$OUT/fuvec.log"     # the die is HLL (GPK gain at d 5120)
  FUSED_HLL=1 FUSED_HC_ONLY=1 FUSED_ONLY_D=5120 python3 tools/hgi_adapters/fused_bench.py --out "$OUT/fuvec_hc" > "$OUT/fuvec_hc.log"
  python3 tools/hgi_unitrate/su_prod_vec.py --out "$OUT/suvec" > "$OUT/suvec.log"
  C=$V/common/ot_hfd_oreg1.sv,$V/quant/rtl/ot_hfd_actquant_m.sv
  fl() { python3 - "$1" "$C" <<'EOF'
import sys
sys.path.insert(0, 'tools')
import die_top_lint as L
r = L.rtl_closure(sys.argv[1].split(','), sys.argv[2].split(','))
print('\n'.join(r[0] if isinstance(r, tuple) else r))
EOF
  }
  fl ot_hgi_fused_station,ot_hgi_hc_eng_station,ot_hgi_vm_unit,ot_hgi_vm_lanearb,ot_hgi_hbm_rdq_server,ot_hfd_oreg5,ot_hfd_sink1,ot_hfd_actquant_m > "$OUT/fl_fused.f"
  fl ot_hgi_su_unit,ot_hgi_vm_unit,ot_hgi_vm_lanearb,ot_hfd_oreg2,ot_hfd_sink1 > "$OUT/fl_su.f"
  fl ot_hgi_hc_unit,ot_hfd_oreg2,ot_hfd_sink1 > "$OUT/fl_hc.f"
  # the FUSED mutant wrapper (station MUT 1), module hfd_quant in its own build
  python3 - "$OUT" <<'EOF'
import json, sys
s = json.load(open('physical/hbm_accel_die_views/quant_hgi/rtl/spec.json'))
s['instances'][0]['params']['MUT'] = 1
json.dump(s, open(sys.argv[1] + '/spec_fused_mut.json', 'w'))
EOF
  OT_VIEW_PORTS_ROOT=$V/ports_r25gqn python3 tools/hbm_die_wrap.py --variant r25gqn --spec "$OUT/spec_fused_mut.json" --out "$OUT/fused_mut_wrap" > /dev/null
  for m in 4 2; do      # the hc_eng engine mutants (module hfd_hc_eng in their own builds)
    python3 - "$OUT" $m <<'EOF'
import json, sys
s = json.load(open('physical/hbm_accel_die_views/hc_eng_hgi/rtl/spec.json'))
s['instances'][0]['params']['MUT'] = int(sys.argv[2])
json.dump(s, open(sys.argv[1] + '/spec_hce_m' + sys.argv[2] + '.json', 'w'))
EOF
    OT_VIEW_PORTS_ROOT=$V/ports_r25gqn python3 tools/hbm_die_wrap.py --variant r25gqn --spec "$OUT/spec_hce_m$m.json" --out "$OUT/hce_m${m}_wrap" > /dev/null
  done
  echo prepared; exit 0
fi
Y=$(for d in physical/asap7_memory_macros/*/; do printf -- "-y %s " "${d%/}"; done)   # SRAM macro behavioural models
W="-Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-PINMISSING"
run() {   # top, vecdir, defines, files...
  local top=$1 vec=$2 defs=$3; shift 3
  "$VL" --binary --timing -O1 $W $Y $defs --top-module "$top" -I"$vec" -Mdir "$OUT/obj_$CASE" "$@" -j ${J:-32} \
    > "$OUT/build_$CASE.log" 2>&1 || { tail -30 "$OUT/build_$CASE.log"; exit 2; }
  "$OUT/obj_$CASE/V$top" +DIR="$vec" ${SIMARGS:-} | tee "$OUT/run_$CASE.log" | tail -${TAILN:-16}
}
case "$CASE" in
  fused)     run tb_hgi_fused_station "$OUT/fuvec" "-DLANE_LOAD" $(cat "$OUT/fl_fused.f") $V/quant_hgi/rtl/hfd_quant.sv $V/hc_eng_hgi/rtl/hfd_hc_eng.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv ;;
  fused_mut) run tb_hgi_fused_station "$OUT/fuvec" "-DLANE_LOAD" $(cat "$OUT/fl_fused.f") "$OUT/fused_mut_wrap/hfd_quant.sv" $V/hc_eng_hgi/rtl/hfd_hc_eng.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv ;;
  fused_hce) run tb_hgi_fused_station "$OUT/fuvec_hc" "-DLANE_LOAD" $(cat "$OUT/fl_fused.f") $V/quant_hgi/rtl/hfd_quant.sv $V/hc_eng_hgi/rtl/hfd_hc_eng.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv ;;
  fused_hce_m4|fused_hce_m2)
             run tb_hgi_fused_station "$OUT/fuvec_hc" "-DLANE_LOAD" $(cat "$OUT/fl_fused.f") $V/quant_hgi/rtl/hfd_quant.sv "$OUT/hce_${CASE#fused_hce_}_wrap/hfd_hc_eng.sv" rtl/hbm_accel/generic/adapters/tb/tb_hgi_fused_station.sv ;;
  su)        run tb_hgi_su_die "$OUT/suvec" "" $(cat "$OUT/fl_su.f") $V/su_hgi/rtl/hfd_su.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_die.sv ;;
  su_mut)    run tb_hgi_su_die "$OUT/suvec" "-DMUT_TAP" $(cat "$OUT/fl_su.f") $V/su_hgi/rtl/hfd_su.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_die.sv ;;
  sfu)       run tb_hgi_su_die "$OUT/suvec" "-DSFU" $(cat "$OUT/fl_su.f") $V/sfu_hgi/rtl/hfd_sfu.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_die.sv ;;
  hc_lock)   run tb_hfd_hc "$OUT" "-DOT_WW_MACRO" $(cat "$OUT/fl_hc.f") $V/hc_hgi/rtl/hfd_hc.sv $V/hc_hgi/rtl/tb_hfd_hc.sv ;;
  *) echo "unknown case $CASE"; exit 1 ;;
esac
