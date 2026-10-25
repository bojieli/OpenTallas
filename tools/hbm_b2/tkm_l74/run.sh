#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$o/vec" > "$o/vectors.log"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
c=rtl/hbm_accel/generic/collective
src=("$c/p2p/qtkm_hier.vlt" tools/hbm_b2/tkm_l74/tb_hbm_tkm_l74.sv  rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv "$c/tkm/ot_hgi_coll_tkm_static.sv" "$c/tkm/ot_hgi_coll_tkm.sv" "$c/tkm/ot_hgi_coll_tkm_buffer.sv"  rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_root_core.sv  rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_tile_core.sv  rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$v" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT  --top-module tb_hbm_tkm_l74 --Mdir "$o/obj" -GTP=192 -GKMAX=2048 -GLINK_STAGES="${LINK_STAGES:-3}" -GRETURN_CTL_STAGES="${RETURN_CTL_STAGES:-11}" -GRETURN_DATA_STAGES="${RETURN_DATA_STAGES:-2}" "${src[@]}" > "$o/build.log" 2>&1
for tc in syn_sel syn_cand rank128_zeros;do
 "$o/obj/Vtb_hbm_tkm_l74" +DIR="$o/vec/$tc" +ROTATE=128 > "$o/$tc.log" 2>&1
 grep TKM_L74 "$o/$tc.log"
done
for m in MUT_PHASE MUT_RETURN;do
 set +e;"$o/obj/Vtb_hbm_tkm_l74" +DIR="$o/vec/syn_sel" +ROTATE=128 +$m > "$o/$m.log" 2>&1;rc=$?;set -e
 if [ "$rc" = 0 ];then echo "$m SURVIVED";exit 1;fi
 grep -m1 -E "TKM_L74 FAIL|L74_TKM_TRANSPORT" "$o/$m.log"
done
printf 'TKM_L74_COMPLETE_PASS\n' > "$o/done"
