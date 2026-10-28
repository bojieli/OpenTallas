#!/bin/bash
# End-to-end ohier demo on ORFS asap7/riscv32i (4 x fakeram7_256x32), flat vs hierarchical.
# Run on a fleet host with docker + openroad/orfs:asap7lock (NOT on a laptop/localhost:
# ORFS runs take ~10-20 min and several GB).  Heavy stages are wrapped in ot-run when
# OT_RUN is set (OpenTallas fleet), else run directly.
#   run_demo.sh BASE_DIR [REGION_MAP]   (default: region_map.json here: 3 locality regions -> 3 partitions)
set -euo pipefail
B=$1; RMAP=${2:-$(cd "$(dirname "$0")" && pwd)/region_map.json}
H=$(cd "$(dirname "$0")/../.." && pwd)          # opentools/hier
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
PL=/OpenROAD-flow-scripts/flow/platforms/asap7
OTR=${OT_RUN:-}
D=$B/demo; mkdir -p "$D" "$B/libs"
dock() { docker run --rm --memory 8g --user "$(id -u):$(id -g)" -v "$B:$B" -v "$H:$H" "$IMG" bash -c "$*"; }

# 0. hierarchical synthesis with every module kept (ORFS synth, stops at synth_odb: see README limits)
if [ ! -f "$B/hsynth/results/asap7/riscv32i/base/1_2_yosys.v" ]; then
  mkdir -p "$B/hsynth"
  dock "source /OpenROAD-flow-scripts/env.sh >/dev/null; cd /OpenROAD-flow-scripts/flow && \
        make WORK_HOME=$B/hsynth DESIGN_CONFIG=designs/asap7/riscv32i/config.mk SYNTH_MINIMUM_KEEP_SIZE=0 synth" || true
fi
# 1. TT RVT libs + macro views for the planner, design SDC, Yosys JSON
dock "for f in $PL/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_2*.lib.gz; do zcat \$f > $B/libs/\$(basename \${f%.gz}); done; \
      cp $PL/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib $PL/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_TT_nldm_FAKE.lib \
         $PL/lib/NLDM/fakeram7_256x32.lib $PL/lef/fakeram7_256x32.lef $B/libs/; \
      cp /OpenROAD-flow-scripts/flow/designs/asap7/riscv32i/constraint.sdc $D/design.sdc; \
      $H/scripts/export_json.sh $B/hsynth/results/asap7/riscv32i/base/1_2_yosys.v riscv_top $D/net.json $B/libs/*.lib"
# 2. plan + emit
G=$D/gen; rm -rf "$G"
( cd "$H" && python3 -m ohier plan --region-map "$RMAP" --netlist "$D/net.json" --top riscv_top --lib "$B/libs/*.lib" --lef "$B/libs/*.lef" \
    --macro-lef '$(PLATFORM_DIR)/lef/fakeram7_256x32.lef' --macro-lib '$(PLATFORM_DIR)/lib/NLDM/fakeram7_256x32.lib' \
    --sdc "$D/design.sdc" --period-ps 950 --latency-ps 100 --io-budget-ps 118.75 \
    --nick riscv32i_ohier --out "$G" ) > "$D/plan_summary.json"
# 3. structural equivalence of the emitted partitioned and flat netlists
cat "$G/top.v" $(ls "$G"/*/*.v | grep -v /flat/) > "$D/part_all.v"
dock "$H/scripts/export_json.sh $D/part_all.v riscv_top $D/part.json $B/libs/*.lib"
( cd "$H" && python3 -m ohier verify --orig "$D/net.json" --part "$D/part.json" --top riscv_top --lib "$B/libs/*.lib" ) > "$D/verify.json"
# 4. ORFS: partitions in parallel -> abstracts -> top; flat baseline in parallel
rm -rf "$D/work" "$D/work_flat"
$OTR "$H/scripts/orfs_flow.sh" "$G" "$D/work" blocks && $OTR "$H/scripts/orfs_flow.sh" "$G" "$D/work" top &
$OTR "$H/scripts/orfs_flow.sh" "$G" "$D/work_flat" flat &
wait
# 5. abstract check: LEF/ETM vs plan, partition clock insertion -> shared plan
( cd "$H" && python3 -m ohier abstract --gen "$G" --work "$D/work" --nick riscv32i_ohier ) > "$D/abstract.json"
# 6. STA views + correlation
( cd "$H" && python3 -m ohier sta-scripts --gen "$G" --work "$D/work" --flat-work "$D/work_flat" \
    --nick riscv32i_ohier --lib "$B/libs/*.lib" --out "$D/sta" )
"$H/scripts/sta_run.sh" "$D/sta" "$B" "$H"
( cd "$H" && python3 -m ohier compare --gen "$G" --sta-dir "$D/sta" --out "$D/sta/compare.json" )
