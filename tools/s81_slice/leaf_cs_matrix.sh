#!/bin/bash
# leaf_cs_matrix.sh <outdir> (cwd = repo root; run through ot-run): LF-CS (S81-LEAF-FLOOR-2 11-12) per-class station
# evidence for the plan's leaf depths.  Each class at its plan depth must PASS on the bench that exercises its seam;
# the station mutants must FAIL (the bench sees a one-station skew):
#   leaf_bench (SU: vp+vn+vq+vs+vsw+RA lanes)  VNI VNO Y U SW SWR RA RAR PVS VSP, all-classes at plan max;
#   leaf_eng_bench (ENG: + ve)                 VE VER;
#   beat_bench (vp hc_post lanes)              HI/HO 2 (GS 2) -- the leaf SU bench never drives the vp lanes, so it is
#                                              blind to OT_S81SL_CST_MUT_LANE (it PASSes); the beat bench FAILs it.
# Exit 0 only when every case gives its expected verdict.  Summary: <outdir>/matrix.tsv
set -u; O=$1; mkdir -p $O; : > $O/matrix.tsv; bad=0
MAC=physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v
ALL="-GCS_HI_D=2 -GCS_HI_GS=2 -GCS_HO_D=2 -GCS_HO_GS=2 -GCS_VNI_D=1 -GCS_VNO_D=1 -GCS_Y_D=2 -GCS_U_D=1 -GCS_SW_D=1 -GCS_SWR_D=1 -GCS_RA_D=1 -GCS_RAR_D=1 -GCS_PVS_D=1 -GCS_VSP_D=1 -GCS_VE_D=1 -GCS_VER_D=1"
run() {   # name expect(PASS|FAIL) cmd...
    local n=$1 e=$2; shift 2
    "$@" > $O/$n.log 2>&1; local rc=$?
    local got=FAIL; grep -qE '^PASS ' $O/$n.log && got=PASS
    [ "$got" = "$e" ] && v=ok || { v=WRONG; bad=1; }
    printf '%s\t%s\t%s\t%s\n' "$n" "$e" "$got" "$v" | tee -a $O/matrix.tsv
}
for c in VNI VNO Y U SW SWR RA RAR PVS VSP; do
    run leaf_$c PASS env S81SL_CST="-GCS_${c}_D=1" bash tools/s81_slice/leaf_bench.sh $O/leaf_$c 0 L0
done
run leaf_Y2 PASS env S81SL_CST="-GCS_Y_D=2" bash tools/s81_slice/leaf_bench.sh $O/leaf_Y2 0 L0
run leaf_all PASS env S81SL_CST="$ALL" bash tools/s81_slice/leaf_bench.sh $O/leaf_all 0 L0
run leaf_mutuv FAIL env S81SL_CST="-GCS_U_D=1 +define+OT_S81SL_CST_MUT_UV" bash tools/s81_slice/leaf_bench.sh $O/leaf_mutuv 0 L0
for c in VE VER; do
    run eng_$c PASS env S81_VS_EXTRA_SOURCES=$MAC S81SL_CST="-GCS_${c}_D=1" bash tools/s81_slice/leaf_eng_bench.sh $O/eng_$c 0
done
run eng_all PASS env S81_VS_EXTRA_SOURCES=$MAC S81SL_CST="$ALL" bash tools/s81_slice/leaf_eng_bench.sh $O/eng_all 0
run beat_hio2 PASS env S81SL_CST="-GCS_HI_D=2 -GCS_HI_GS=2 -GCS_HO_D=2 -GCS_HO_GS=2 $MAC" bash tools/s81_slice/beat_bench.sh $O/beat_hio2 base
run beat_mutlane FAIL env S81SL_CST="-GCS_HI_D=2 -GCS_HI_GS=2 -GCS_HO_D=2 -GCS_HO_GS=2 +define+OT_S81SL_CST_MUT_LANE $MAC" bash tools/s81_slice/beat_bench.sh $O/beat_mutlane base
echo "LF_CS_MATRIX $([ $bad = 0 ] && echo PASS || echo FAIL)"; exit $bad
