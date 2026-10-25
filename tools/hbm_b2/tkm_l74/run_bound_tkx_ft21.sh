#!/bin/bash
# PATH-HBM/TOK 2026-10-25: face-shelled TKM path gate (r4).  run_shell.sh <out dir>
set -euo pipefail
# hier config: tkm_tp192_e86_hier.vlt (e86 wrapper = hier block). r3 / r4 / r4b / r4c used p2p/qtkm_hier.vlt, whose tile_rg
# hier block Verilator does not substitute through the e86 wrapper: all 32 tile bodies flattened into the top pass -> memcg
# OOM at 128 / 192 GB (verilator_bin 191 GB).
export ROOT_VARIANT=ft21
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?out}");mkdir -p "$o"
OPENBLAS_NUM_THREADS=1 python3 tools/hgi_coll_tkm_tp192_vectors.py --out "$o/vec" > "$o/vectors.log"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
c=rtl/hbm_accel/generic/collective
f=rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192_face
# ROOT_VARIANT cb14 = root core of ot_hgi_coll_tkm_m_tp192_pf (clr+conv broadcast 14); cb21 = ..._pf21 (conv broadcast 21
# to tile 31 + deskew, clr systolic down the chain); ft21 = cb21 root + the IN-TILE clr/conv lanes (tile_clr_o/tile_conv_o,
# shell in face/ft) instead of the parent relays.  The bench checks its CB/CLRB against the root's.
case "${ROOT_VARIANT:-cb21}" in
 cb14) rcore="$f/ot_hgi_coll_tkm_tp192_root_core.sv";defs=(+define+ROOT_CB=14 +define+ROOT_CLRB=14 -GCTL_BCAST_STAGES=14 -GCLR_SYSTOLIC=0);;
 cb21) rcore="$f/cb21/ot_hgi_coll_tkm_tp192_root_core.sv";defs=(+define+ROOT_CB=21 +define+ROOT_CLRB=0 -GCTL_BCAST_STAGES=21 -GCLR_SYSTOLIC=1);;
 ft21) rcore="$f/cb21/ot_hgi_coll_tkm_tp192_root_core.sv";defs=(+define+ROOT_CB=21 +define+ROOT_CLRB=0 +define+TILE_FT -GCTL_BCAST_STAGES=21 -GCLR_SYSTOLIC=1);;
 *) echo "bad ROOT_VARIANT";exit 2;;
esac
if [ "${STATIC_IDS:-1}" = 0 ];then defs+=(+define+TKM_LEGACY_TIMED_ID_VIEW);fi
rootshell="$f/ot_hgi_coll_tkm_m_tp192__root__fshell.sv"
rootwrap="$f/ot_hgi_coll_tkm_m_tp192__root__wrap.sv"
if [ "${DELIVERED_ROOT:-0}" = 1 ];then
 rcore="$o/root_delivered/ot_hgi_coll_tkm_tp192_root_core__delivered_reset.sv"
 python3 tools/hbm_b2/tkm_l74/overlay_root_delivered_reset.py "$f/cb21/ot_hgi_coll_tkm_tp192_root_core.sv" "$rcore" --face-dir "$f" > "$o/root_reset_overlay.log"
 rootshell="$o/root_delivered/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__fshell.sv"
 rootwrap="$o/root_delivered/ot_hgi_coll_tkm_m_tp192__root__delivered_reset__wrap.sv"
 defs+=(+define+TKM_DELIVERED_ROOT_VIEW)
fi
tsh=$f;[ "${ROOT_VARIANT:-cb21}" = ft21 ] && tsh=$f/ft
src=("$c/tkm/tkm_tp192_e86_hier.vlt" tools/hbm_b2/tkm_l74/tb_hbm_tkm_bound_tkx_ft21.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_path_tkx_ft21.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkx_2beat.sv rtl/hbm_accel/die_glue/b2/ot_hbm_tkm_return.sv rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv
 "$c/tkm/ot_hgi_coll_tkm_static.sv" "$c/tkm/ot_hgi_coll_tkm.sv" "$c/tkm/ot_hgi_coll_tkm_buffer.sv" "$c/tkm/ot_hgi_coll_tkm_conv_skew.sv"
 "$f/ot_hbm_face_reg.sv" "$rootshell" "$rootwrap" "$rcore"
 "$tsh/ot_hgi_coll_tkm_tp192_tile_core__idpin__fshell.sv" "$tsh/ot_hgi_coll_tkm_tp192_tile_core__idpin__wrap.sv"
 "$f/terminal/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__fshell.sv" "$f/terminal/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__wrap.sv"
 rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192/ot_hgi_coll_tkm_tp192_tile_core.sv
 "$f/strap/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__fshell.sv" "$f/strap/ot_hgi_coll_tkm_tp192_tile_core__idpin__strap__wrap.sv"
 "$f/terminal_strap/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__fshell.sv" "$f/terminal_strap/ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin__strap__wrap.sv"
 rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$v" --binary --timing --hierarchical --verilate-jobs 2 --build-jobs "${BUILD_JOBS:-2}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT --top-module tb_hbm_tkm_bound_tkx_ft21 --Mdir "$o/obj" -GTP=192 -GKMAX=2048 -GLINK_STAGES="${LINK_STAGES:-2}" -GRETURN_CTL_STAGES="${RETURN_CTL_STAGES:-2}" -GRETURN_DATA_STAGES="${RETURN_DATA_STAGES:-2}" -GHOP=2 -GFRT=4 "${defs[@]}" "${src[@]}" > "$o/build.log" 2>&1
b="$o/obj/Vtb_hbm_tkm_bound_tkx_ft21"
for tc in ${CASES:-rank128_zeros};do
 "$b" +DIR="$o/vec/$tc" +ROTATE=128 > "$o/$tc.log" 2>&1
 grep TKM_L74 "$o/$tc.log"
done
for m in MUT_PHASE MUT_TID;do
 set +e;"$b" +DIR="$o/vec/rank128_zeros" +ROTATE=128 +$m > "$o/$m.log" 2>&1;rc=$?;set -e
 if [ "$rc" = 0 ];then echo "$m SURVIVED";exit 1;fi
 echo "$m CAUGHT rc=$rc: $(grep -m1 -E 'TKM_L74 FAIL|L74_TKM_TRANSPORT|TILE_TID|MISMATCH|LOCKSTEP|TIMELINE|Error' "$o/$m.log")"
done
printf 'TKM_L74_BOUND_MINIMUM_PASS\n' > "$o/done"
