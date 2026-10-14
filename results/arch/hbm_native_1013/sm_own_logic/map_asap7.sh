#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock bash -lc '
set -euo pipefail
libdir=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
libargs=""
for family in AO OA SIMPLE INVBUF; do
 src=$(find "$libdir" -maxdepth 1 -name "asap7sc7p5t_${family}_RVT_TT_*.lib.gz" | head -1)
 gzip -dc "$src" > "${family}.lib"
 libargs="$libargs -liberty ${family}.lib"
done
cp "$libdir/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" SEQ.lib
libargs="$libargs -liberty SEQ.lib"
for v in eg wg; do
 yosys -Q -p "read_liberty -lib SEQ.lib; read_json ${v}_mapinput.json; hierarchy -check -top ot_smh_own_${v}; synth -top ot_smh_own_${v} -flatten; dfflibmap -liberty SEQ.lib; abc $libargs -D 833.333; clean; stat $libargs; write_json ${v}_asap7.json; write_verilog -noattr ${v}_asap7.sv" > "${v}_asap7.log"
done
'
