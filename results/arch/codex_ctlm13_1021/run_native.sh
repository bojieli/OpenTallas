#!/bin/bash
# Independent mapped native admission before any layout. Actual ORFS image TT libraries.
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
root=$(pwd)
mkdir -p libs native
docker image inspect openroad/orfs:latest --format '{{.Id}}' > native/tool_image_id.txt
docker run --rm -v "$root:/w" openroad/orfs:latest bash -lc '
 set -e
 p=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 for family in AO INVBUF OA SIMPLE SEQ; do
  for f in "$p"/asap7sc7p5t_${family}_RVT_TT_*.lib*; do
   n=$(basename "$f" .gz)
   if [[ "$f" = *.gz ]]; then gzip -dc "$f" > "/w/libs/$n"; else cp "$f" "/w/libs/$n"; fi
  done
 done
'
{
 for lib in "$root"/libs/*.lib; do printf 'read_liberty -lib %s\n' "$lib"; done
 printf 'read_verilog -sv -DSYNTHESIS rtl/qwen_dv/lp9f_rrloc/qfd_tt_ctlm_dv_np_lp.sv rtl/qwen_dv/lp9f_rrloc/qfd_tt_ctlm_dv_np_helpers.sv rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv\n'
 printf 'hierarchy -check -top qfd_tt_ctlm_dv_np_lp\ntcl physical/common_flow/ot_keep_regs.tcl\nsynth -noabc -top qfd_tt_ctlm_dv_np_lp -flatten\n'
 printf 'dfflibmap -liberty %s/libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib\nabc' "$root"
 for family in SIMPLE INVBUF AO OA; do printf ' -liberty %s' "$root"/libs/asap7sc7p5t_${family}_RVT_TT_*.lib; done
 printf '\nopt_clean -purge\nautoname\nwrite_verilog -noattr %s/native/mapped.v\nstat\n' "$root"
} > native/run.ys
yosys -V > native/yosys_version.txt
yosys -ql native/synth.log native/run.ys
args=()
for lib in "$root"/libs/*.lib; do args+=(--liberty "$lib"); done
python3 tools/ref_tile/native_census.py --netlist native/mapped.v --top qfd_tt_ctlm_dv_np_lp --out native/census.json "${args[@]}" > native/census.log 2>&1
cat native/census.log
