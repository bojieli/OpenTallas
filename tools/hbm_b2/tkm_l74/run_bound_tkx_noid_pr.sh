#!/bin/bash
# TOK-HBM 2026-10-25 18:45: selected TKM path token gate on the CURRENT physical source views:
#   strict pin-reg TKX TX/RX (2097952d2f) + delivered-reset chain3 root kit (root_delivered_chain3_v1, canonical 5cd6679d)
#   + 31 x no-ID common kit (common_noid_v2) + 1 x no-ID terminal kit (terminal_noid_v2), canonical tile core 3118f95a.
# Closure order rule 3 (owner 10-25 18:45): reads ONLY repo-relative paths at the checked-out commit. The kit RTL bytes
# were imported into the repo (noid_v2/, delivered_chain3/, canonical core from physical 4f800e1ed9) and are checked
# against expected_views_noid_pr.sha256 (the kit rtl/ SHAs) before building; a dirty tree is refused.
# usage: run_bound_tkx_noid_pr.sh <out dir>
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
if [ -n "$(git status --porcelain --untracked-files=no -- rtl tools/hbm_b2 physical/asap7_memory_macros)" ];then echo "DIRTY TREE: refuse (rule 3)";exit 3;fi
git rev-parse HEAD > "$o/source_commit.txt"
sha256sum -c tools/hbm_b2/tkm_l74/expected_views_noid_pr.sha256 > "$o/view_sha_check.log"
f=rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face
kc=$f/noid_v2;kt=$f/noid_v2;kr=$f/delivered_chain3
c=rtl/hbm_accel/generic/collective
src=("$c/tkm/tkm_tp192_e86_hier.vlt" tools/hbm_b2/tkm_l74/tb_hbm_tkm_bound_tkx_ft21.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_path_tkx_ft21.sv
 rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat_pr.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_return.sv
 rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv
 "$c/tkm/ot_hgi_coll_tkm_static.sv" "$c/tkm/ot_hgi_coll_tkm.sv" "$c/tkm/ot_hgi_coll_tkm_buffer.sv" "$c/tkm/ot_hgi_coll_tkm_conv_skew.sv"
 "$f/ot_hbm_face_reg.sv"
 "$kr/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__fshell.sv" "$kr/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__wrap.sv" "$kr/ot_hgi_coll_tkm_tp192_root_core__delivered_reset.sv"
 rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_tile_core.sv
 "$kc/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fshell.sv" "$kc/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__wrap.sv"
 "$kt/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__fshell.sv" "$kt/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__wrap.sv"
 rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${src[@]}" > "$o/source_manifest.sha256"
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
