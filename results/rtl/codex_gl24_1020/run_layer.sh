#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/codex-gl24-1020
L=$1
cd "$R"
mkdir -p out cases
sha256sum Vtb_toksim_gath > out/exe.sha256
for VIEW in ${VIEWS:-00}; do
 D=${VIEW:0:1}; S=${VIEW:1:1}; C=${L}_v${VIEW}
 python3 src/tools/s81_dv/layer_prog/toksim_gath_vectors.py --fixture fixtures/$L --out cases/$C --view $D,$S > out/gen_$C.log 2>&1 || { cat out/gen_$C.log; exit 3; }
 ./Vtb_toksim_gath +dir=$PWD/cases/$C +seed=1 +static_io=1 +sel_gap=0 > out/run_${C}_g0.log 2>&1
 grep -E '^GATH_T |^SVCRS ' out/run_${C}_g0.log
 grep -q 'verdict=PASS' out/run_${C}_g0.log || exit 1
done
echo GL24_DONE "$L" "${VIEWS:-00}"
