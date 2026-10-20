#!/bin/bash
set -eu
W="$PWD/native_synth_out/segcal/work/orfs"
L="$PWD/native_synth_out/segcal/flow.log"
while ! grep -q SEGCAL_SYNTH_ONLY_MAPPED "$L"; do
 if grep -q 'stop-after.*rc=[1-9]' native_synth_out/segcal/STATUS; then echo SYNTH_FAILED; exit 1; fi
 sleep 10
done
cp results/rtl/qlb_c4b_1018/lmh_cal/native_synth/{flatten.py,audit.py} "$W/"
docker run --rm -v "$PWD:/src:ro" -v "$W:/out" -w /out openroad/orfs:latest python3 /out/flatten.py > "$W/flatten.log" 2>&1
cd "$W"
python3 audit.py
