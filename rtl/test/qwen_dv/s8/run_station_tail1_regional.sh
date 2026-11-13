#!/bin/bash
# QKO-SLICE2-STN 10-21: existing regional-station equivalence bench (run_station_regional.sh) retargeted to
# qfd_dv_s8_station_tail1: the 8 region copies use tail1; phase-2 cfg_nwords constrained to >= JB=8 (the legacy
# regime where tail1 must equal the monolith edge-for-edge; nwords<8 is the new LASTK tail, monolith wraps at 8).
# args: work MUT RMUT
# QC-TAIL1-TRIAGE 11-13: tail1 (SCALE_LAT 7) puts r_v/r_idx/r_last/r_d XR=1 edge late; the tb only applies that
# shift when PIN != 0, so PIN=0 can never match (fails REGIONAL_STATION_MISMATCH edges 91-95). Default PIN=1, the
# gated form (physical/ref_tile/qfd_dv_s8_station_tail1_p7b/job.json), and refuse PIN=0 with XR != 0.
set -euo pipefail
work=$1;mut=${2:-0};rmut=${3:-0}
PIN=${PIN:-1};XR=${XR:-1}
if [ "$PIN" = 0 ] && [ "$XR" != 0 ]; then echo "TB_XR_SHAPE: tail1 XR=$XR needs PIN=1 (PIN=0 compares results 1 edge early)" >&2; exit 2; fi
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
tag=t1p${PIN}m${mut}r${rmut}
mkdir -p "$work/gen_$tag"
sed 's/cfg_nwords = 1 + (\$random & 63)/cfg_nwords = 8 + ($random \& 63)/' rtl/test/qwen_dv/safe_storage/tb_station_regional.sv > "$work/gen_$tag/tb.sv"
grep -q 'cfg_nwords = 8 + ' "$work/gen_$tag/tb.sv"
sed 's/(\* keep_hierarchy = "yes" \*) qfd_dv_redstn2_region #(/(* keep_hierarchy = "yes" *) qfd_dv_s8_station_tail1 #(/' rtl/qwen_dv/qfd_dv_redstn2_regional.sv > "$work/gen_$tag/regional.sv"
grep -q 'qfd_dv_s8_station_tail1 #(' "$work/gen_$tag/regional.sv"
verilator --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_station_regional -GMUT="$mut" -GRMUT="$rmut" -GPIN="$PIN" -GXR="$XR" --Mdir "$work/obj_$tag" \
 "$work/gen_$tag/tb.sv" rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv "$work/gen_$tag/regional.sv" rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv rtl/qwen_dv/qfd_dv_station_math_g.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_safe.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv rtl/common/landed_parent/ot_pl_land_n32.sv \
 rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > "$work/build_$tag.log" 2>&1
"$work/obj_$tag/Vtb_station_regional"
