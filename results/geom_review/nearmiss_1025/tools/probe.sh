#!/bin/bash
# usage: probe.sh <signoff_dir> <out_dir> <mem_gb>   (diagnostic probe; docker --memory; read-only mounts of the run)
set -e
SO=$1; OUT=$2; MEM=${3:-24}; T=$(dirname $0)
mkdir -p $OUT
KIT=$(python3 -c "import json;print(json.load(open('$SO/signoff.json'))['inputs']['kit'])")
for c in tt ff; do
  C=${c^^}
  cmd=$(cat $SO/$c/cmd.sh)
  mounts=$(echo "$cmd" | grep -o -- '-v [^ ]*' | grep -v ':/out$' | tr '\n' ' ')
  n=$(grep -n '^so_timing STD' $SO/$c/session.tcl | cut -d: -f1)
  { head -n $n $SO/$c/session.tcl; sed "s/@C@/$C/g" $T/dump_tail.tcl; } > $OUT/dump_$c.tcl
  libs=$(sed -n '1,8p' $SO/$c/session.tcl | grep -E '^foreach l|^read_liberty')
  MINL=$(grep -oP 'MIN_ROUTING_LAYER\s*\??=\s*\K\S+' $KIT/config.mk | head -1); MINL=${MINL:-M2}
  MAXL=$(grep -oP 'MAX_ROUTING_LAYER\s*\??=\s*\K\S+' $KIT/config.mk | head -1); MAXL=${MAXL:-M7}
  python3 - "$T/ckest.tcl.in" "$OUT/ckest_$c.tcl" "$C" "$MINL" "$MAXL" <<PY
import sys; s=open(sys.argv[1]).read(); libs=open("$SO/$c/session.tcl").read().split("read_db")[0].split("\n")
libs="\n".join(l for l in libs if l.startswith("foreach l") or l.startswith("read_liberty"))
open(sys.argv[2],"w").write(s.replace("@LIBS@",libs).replace("@C@",sys.argv[3]).replace("@MINL@",sys.argv[4]).replace("@MAXL@",sys.argv[5]))
PY
  name=nm_$(basename $OUT)_$c
  docker run --rm --name ${name}_d --memory ${MEM}g $mounts -v $OUT:/nm openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /nm/dump_$c.tcl > $OUT/dump_$c.log 2>&1 &
  if [ $c = tt ] && [ ! -s $OUT/ckest_tt.tsv ]; then
    docker run --rm --name ${name}_e --memory ${MEM}g $mounts -v $OUT:/nm openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /nm/ckest_$c.tcl > $OUT/ckest_$c.log 2>&1 &
  fi
done
wait
grep -h "NM_.*DONE" $OUT/*.log
