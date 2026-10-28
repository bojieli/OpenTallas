#!/bin/bash
# KV-KITS-8 10-28: COORD 06:26 ruling on the KV-KITS-7 head ASK (no strap-capture flop without timed fan-in).
# = QK-CORES-10 regen_heads.sh (flags from each kit freeze.json; kvr2_reserve.tcl carried + sourced first in face_flops.tcl
# as in the GEOM-passed kits) + --head-strap-direct; base claude/kv-kits-8-1028 = main 4d4c968ee0 + STRAP_DIRECT/STRAP_SAMPLE leaves.
set -e
B=/srv/opentallas-scratch2/claude/kv-kits-8-1028
W=/srv/opentallas-scratch2/claude/wt/kv-kits-8-1028
OLD=/srv/opentallas-scratch2/claude/qk-cores-10/kits_heads
O=${1:-$B/kits_heads}
P=/srv/opentallas-scratch2/claude/qk-cores-7/pd/hm_r26q5c39.json
G=$W/physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py
mkdir -p $O $B/logs
cd $W
for e in ${EIGHTHS:-e0 e1 e2 e5 e6}; do
  K=$OLD/kv3_head_eighth_${e}__216x216
  F="--head-lane-ltcopy --no-head-lane-taps --head-strap-direct"
  case $e in e0|e2|e6) F="$F --head-lane-s3copy --head-port-regs";; esac
  rm -rf $O/kv3_head_eighth_${e}__216x216
  CJ=$(python3 -c "import json,hashlib,glob,sys;h=json.load(open(\"$K/freeze.json\"))[\"core_json_sha256\"];m=[f for f in glob.glob(\"results/kv_cores_r*/rtl/kv3_head_eighth_${e}/*_core.json\") if hashlib.sha256(open(f,\"rb\").read()).hexdigest()==h];assert len(m)==1,m;print(m[0])")
  python3 $G --core-json $CJ --plan $P --out $O --kit-rtl /srv/opentallas-scratch2/claude/kv-cores-r6/kit_flat --util 0.6 --sigmax M7 $F --plan-inst head0_$e > $B/logs/gen_$e.log 2>&1
  N=$O/kv3_head_eighth_${e}__216x216
  cp $K/kvr2_reserve.tcl $N/
  { echo "source /work/kvr2_reserve.tcl"; cat $N/face_flops.tcl; } > $N/face_flops.tcl.n && mv $N/face_flops.tcl.n $N/face_flops.tcl
  echo "== $e $(tail -1 $B/logs/gen_$e.log | cut -c1-200)"
  for f in $(cd $N; ls; ls rtl | sed s,^,rtl/,); do [ -d $N/$f ] || cmp -s $N/$f $K/$f || echo "  DIFF $f"; done
  for f in $(cd $K; ls; ls rtl | sed s,^,rtl/,); do [ -e $N/$f ] || echo "  ONLY-OLD $f"; done
done
