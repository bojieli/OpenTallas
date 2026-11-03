#!/bin/bash
# OWNER 11-03 RE-FORM pre-build gate (die-agnostic): ORFS synth + floorplan + global place + resize (no CTS, no route)
# on a kit dir, then OpenSTA TT setup with ideal clocks at the kit's planned insertion latency, then gen-time lint.
#   prebuild_gate.sh KIT_DIR OUT_DIR [CPUS] [MEM_GB]
# PASS iff worst setup >= +10% of the clock period AND the lint passes (see prebuild_gate.py).
# Runs in docker (openroad/orfs:asap7lock) with a memory cap; never run it on the coordinator host.
set -u
KIT=$(cd "$1" && pwd -P); OUT=$(mkdir -p "$2" && cd "$2" && pwd -P); CPUS=${3:-4}; MEM=${4:-24}
HERE=$(cd "$(dirname "$0")" && pwd -P); IMG=${PREBUILD_GATE_IMAGE:-openroad/orfs:asap7lock}
mkdir -p "$OUT/work"
rsync -a --delete --exclude run --exclude lec --exclude 'eco_*' --exclude '*.odb' --exclude logs "$KIT/" "$OUT/work/"
echo "$KIT" > "$OUT/kit_src.txt"
N=pbgate-$(basename "$OUT")-$$
docker run --rm --name "$N" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" \
  -v "$OUT/work":/work -v "$HERE":/gate:ro -w /OpenROAD-flow-scripts/flow "$IMG" bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=gate NUM_CORES=$CPUS'
st=ok; for s in synth do-floorplan do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized; do
  [ \$s = do-floorplan ] && \$M floorplan >> /work/gate_flow.log 2>&1 && continue
  \$M \$s >> /work/gate_flow.log 2>&1 || { st=\$s; break; }
done
echo \"GATE_FLOW stop=\$st\" > /work/gate_flow.status
R=\$(ls -d /work/run/results/asap7/*/gate | head -n 1)
ODB=\$R/3_4_place_resized.odb; STAGE=place_resized
[ -f \$ODB ] || { ODB=\$R/3_3_place_gp.odb; STAGE=place_gp; }
[ -f \$ODB ] || { ODB=\$R/1_synth.odb; STAGE=synth_zero_wire; }
SDC=\$R/1_synth.sdc; [ -f \$R/2_floorplan.sdc ] && SDC=\$R/2_floorplan.sdc
LIBS=\"\$(\$M print-TC_LIB_FILES 2>/dev/null | sed -n 's/^TC_LIB_FILES *[:=] *//p')\"
[ -n \"\$LIBS\" ] || LIBS=\"\$(\$M print-LIB_FILES 2>/dev/null | sed -n 's/^LIB_FILES *[:=] *//p')\"
RC=\$(\$M print-SET_RC_TCL 2>/dev/null | sed -n 's/^SET_RC_TCL *[:=] *//p')
LAT=\$(sed -n 's/^export OT_VCLK_TT *= *//p' /work/config.mk | tail -n 1)
echo \"GATE_STAGE \$STAGE\" >> /work/gate_flow.status
GATE_ODB=\$ODB GATE_SDC=\$SDC GATE_LIBS=\"\$LIBS\" GATE_RC=\"\$RC\" GATE_CLK_LAT=\${LAT:-0} GATE_STAGE=\$STAGE \
  openroad -no_init -exit /gate/prebuild_gate_sta.tcl > /work/gate_sta.log 2>&1; echo \"GATE_STA rc=\$?\" >> /work/gate_flow.status
cp -f \$R/1_synth.v /work/gate_synth.v 2>/dev/null; cp -f \$R/mem.json /work/gate_mem.json 2>/dev/null
cp -f /work/run/reports/asap7/*/gate/synth_stat.txt /work/gate_synth_stat.txt 2>/dev/null
chown -R $(id -u):$(id -g) /work"
python3 -I "$HERE/prebuild_gate.py" "$OUT"
