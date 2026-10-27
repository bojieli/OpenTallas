#!/bin/bash
set -eu
E=/srv/opentallas-scratch2/claude/codex-qc-xhead-1027
T=$E/tree
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1
export DV_LOWER_VFLAGS='-GMU_NU=4 -GFACE=3 +define+OT_STATION_REGIONAL +define+OT_S5_HARD +define+OT_S6_SIM +define+OT_S8_SIM +define+OT_QFD_UP4_CK_ENTRIES -Wno-WIDTHCONCAT +define+OT_S8_CROM_ALIGN'
A=$E/cal/xhead_ages.json
B=$T/rtl/test/qwen_dv/xhead_bench.py
mkdir -p $E/pts $E/runs
cd $T
for c in o down qkv; do
  for g in $(seq -10 12); do echo "$c $g 12"; done
  for l in $(seq -4 10); do echo "$c 20 $l"; done
done > $E/points.txt
export E T A B
xargs -P 24 -L 1 bash -c 'python3 "$B" --work "$E/pts" --build-dir "$E/build" --vec-ages "$E/cal/vec_ages.json" --ages "$A" --point "$0" --go-lag "$1" --xpf-lead "$2" > "$E/pts/pt_${0}_g${1}_x${2}.out" 2>&1' < $E/points.txt
python3 "$B" --work "$E/pts" --ages "$A" --merge "$E/xhead_ages.json" > $E/merge.log 2>&1
for c in qkv gu o down; do
 for m in nominal goearly xpflate isaxbase; do
  [ "$c:$m" = qkv:xpflate ] && continue
  [ "$c:$m" = qkv:isaxbase ] && continue
  echo "$c $m"
 done
done > $E/runlist.txt
xargs -P 14 -L 1 bash -c '
 ma=(); [ "$1" = nominal ] || ma=(--mutant "$1")
 set +e
 python3 "$B" --work "$E/runs" --build-dir "$E/build" --vec-ages "$E/cal/vec_ages.json" --ages "$E/xhead_ages.json" --run "$0" "${ma[@]}" > "$E/runs/${0}_${1}.out" 2>&1
 echo "rc=$?" >> "$E/runs/${0}_${1}.out"
' < $E/runlist.txt
python3 $E/collect.py $E
