#!/bin/bash
# ready12b-A rebind trees on merged tools (s81-lfcs-depth-gate ca5ecd841e = origin/main 59f6e46846 + lane): hardlinks for
# read-only bulk; REAL copies of rtl/ and tools/; CLAND-SLEW-1 rtl/common/ot_dp_clk_landing_ca.sv from the merge.
set -eu
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; M=/srv/opentallas-scratch2/claude/wt/s81-lfcs-merge
for p in main_lfcs:main2_lfcs r12ng_lfcs:r12bA_m; do
  S=$O/bsrc_${p%%:*}; D=$O/bsrc_${p##*:}; test ! -e $D; mkdir -p $D
  for d in $(ls -A $S); do
    case $d in rtl) cp -a $S/rtl $D/ ;; tools) cp -a $M/tools $D/ ;; *) cp -al $S/$d $D/ ;; esac
  done
  cp --remove-destination $M/rtl/common/ot_dp_clk_landing_ca.sv $D/rtl/common/ot_dp_clk_landing_ca.sv
done
python3 -I - <<'PY'
import json
O='/srv/opentallas-scratch2/claude/s81-leaf-floor-2'
s=open(O+'/asbuilt_lfcs.json').read(); assert s.count(O+'/bsrc_main_lfcs')==1
open(O+'/asbuilt_lfcs_m.json','w').write(s.replace(O+'/bsrc_main_lfcs', O+'/bsrc_main2_lfcs'))
PY
echo TREES2_DONE
