#!/usr/bin/env bash
# VMX-TOK-1: tok_func_hbm.sh step 3 tail on the 9 emissions: SU component calendar reservation, then ONE TB (gen_slice_tb.py)
# for all sets (NEV as the script computes it).  Output: $R/tb/{tb_slice.sv,replay/<v>_ds_l<l>/}
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/vmx-tok-1; T=$W/tools/hbm_layer_vehicle
R=/srv/opentallas-scratch2/claude/vmx-tok-1; B=$R/vehicle/slice/boundary.json; RJ=$R/rj; mkdir -p $RJ $R/log
NAMES=()
for v in base h0 h1; do for l in 0 2 14; do n=${v}_ds_l$l
  cp $R/emit/$v/ds_l$l/replay.json $RJ/$n.json
  python3 $T/native_su_calendar.py reserve-component $RJ/$n.json $B $RJ/$n.calendar.json > $R/log/calendar_$n.log 2>&1
  mv $RJ/$n.calendar.json $RJ/$n.json; NAMES+=($n); done; done
NEV=$(python3 -c "import json,sys; print(max(16, 1 + max(sum(e['k']!='M' for e in json.load(open(f))['events']) for f in sys.argv[1:])))" $(for n in ${NAMES[@]}; do echo $RJ/$n.json; done))
echo NEV=$NEV
rm -rf $R/tb; python3 $T/gen_slice_tb.py --boundary $B --out $R/tb --nev $NEV $(for n in ${NAMES[@]}; do echo --replay $RJ/$n.json; done) > $R/log/tb.log 2>&1
tail -1 $R/log/tb.log; sha256sum $R/tb/tb_slice.sv; ls $R/tb/replay
