#!/bin/bash
# TOK-HBM 2026-10-25 18:45: selected TKM path token gate on the CURRENT physical source views:
#   strict pin-reg TKX TX/RX (2097952d2f) + delivered-reset chain3 root kit (root_delivered_chain3_v1, canonical 5cd6679d)
#   + 31 x no-ID common kit (common_noid_v2) + 1 x no-ID terminal kit (terminal_noid_v2), canonical tile core 3118f95a.
# Tile/root RTL is taken BYTE-FOR-BYTE from the kit rtl/ dirs (the files synthesized by those kits); SHA manifest written.
# usage: run_bound_tkx_noid_pr.sh <out dir> <kit base>
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");K=$(realpath "${2:?kit base}");mkdir -p "$o/src"
kc=$K/common_noid_v2/rtl;kt=$K/terminal_noid_v2/rtl;kr=$K/root_delivered_chain3_v1/rtl
cmp "$kc/ot_hgi_coll_tkm_tp192_tile_core.sv" "$kt/ot_hgi_coll_tkm_tp192_tile_core.sv"
cmp "$kc/ot_hgi_coll_tkm.sv" rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv
cmp "$kc/ot_hbm_face_reg.sv" rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face/ot_hbm_face_reg.sv
# e86 tile module text must be identical between the kit copy and the bench copy of ot_hgi_coll_tkm_static.sv
python3 - "$kc/ot_hgi_coll_tkm_static.sv" rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static.sv <<'PY'
import sys,re
def e86(p):
    s=open(p).read();i=s.index("module ot_hgi_coll_tkm_tile_e86(");return s[i:s.index("endmodule",i)]
a,b=e86(sys.argv[1]),e86(sys.argv[2]);assert a==b,"e86 tile text differs";print("E86_IDENTICAL")
PY
c=rtl/hbm_accel/generic/collective
src=("$c/tkm/tkm_tp192_e86_hier.vlt" tools/hbm_b2/tkm_l74/tb_hbm_tkm_bound_tkx_ft21.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_path_tkx_ft21.sv
 rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat_pr.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_return.sv
 rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv
 "$c/tkm/ot_hgi_coll_tkm_static.sv" "$c/tkm/ot_hgi_coll_tkm.sv" "$c/tkm/ot_hgi_coll_tkm_buffer.sv" "$c/tkm/ot_hgi_coll_tkm_conv_skew.sv"
 "$kc/ot_hbm_face_reg.sv"
 "$kr/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__fshell.sv" "$kr/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__wrap.sv" "$kr/ot_hgi_coll_tkm_tp192_root_core__delivered_reset.sv"
 "$kc/ot_hgi_coll_tkm_tp192_tile_core.sv"
 "$kc/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fshell.sv" "$kc/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__wrap.sv"
 "$kt/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__fshell.sv" "$kt/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__wrap.sv"
 rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" > "$o/source_manifest.sha256"
git rev-parse HEAD > "$o/source_head.txt"; git status --porcelain -- tools/hbm_b2 rtl >> "$o/source_head.txt"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$o/vec" > "$o/vectors.log"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
defs=(+define+ROOT_CB=21 +define+ROOT_CLRB=0 +define+TILE_FT -GCTL_BCAST_STAGES=21 -GCLR_SYSTOLIC=1 +define+TKM_DELIVERED_ROOT_VIEW +define+TKM_NOID_VIEW +define+TKM_PR_ENDPOINTS)
"$v" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs "${BUILD_JOBS:-2}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hbm_tkm_bound_tkx_ft21 --Mdir "$o/obj" -GTP=192 -GKMAX=2048 -GLINK_STAGES="${LINK_STAGES:-2}" -GRETURN_CTL_STAGES="${RETURN_CTL_STAGES:-2}" -GRETURN_DATA_STAGES="${RETURN_DATA_STAGES:-2}" -GHOP=2 -GFRT=4 "${defs[@]}" "${src[@]}" > "$o/build.log" 2>&1
b="$o/obj/Vtb_hbm_tkm_bound_tkx_ft21"
for m in MUT_PHASE MUT_FLIT;do
 set +e;"$b" +DIR="$o/vec/rank128_zeros" +ROTATE=128 +$m > "$o/$m.log" 2>&1;rc=$?;set -e
 if [ "$rc" = 0 ];then echo "$m SURVIVED";exit 1;fi
 echo "$m CAUGHT rc=$rc: $(grep -m1 -E 'TKM_L74 FAIL|L74_TKM_TRANSPORT|MISMATCH|LOCKSTEP|TIMELINE|FAULT|Error' "$o/$m.log")"
done
for tc in ${CASES:-rank128_zeros syn_sel syn_cand};do
 "$b" +DIR="$o/vec/$tc" +ROTATE=128 > "$o/$tc.log" 2>&1
 grep TKM_L74 "$o/$tc.log"
done
printf 'TKM_L74_NOID_PR_BOUND_PASS\n' > "$o/done"
