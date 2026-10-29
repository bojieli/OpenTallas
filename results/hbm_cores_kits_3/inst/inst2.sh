#!/bin/bash
# HBM-CORES-KITS-3 probe: macro instance paths per master (yosys hierarchy+proc+flatten, kit read-only). inst2.sh KIT
set -u
K=$1; N=$(basename $K); O=/srv/opentallas-scratch2/claude/hbm-cores-kits-3/inst/$N; mkdir -p $O
v() { sed -nE "s/^export $1 = (.*)/\1/p" $K/config.mk | tail -1; }
TOP=$(v DESIGN_NAME)
{ for l in $K/macros/*_tt.lib; do echo "read_liberty -lib /work/macros/$(basename $l)"; done
  echo "read_verilog -sv -defer $(v VERILOG_DEFINES) $(v VERILOG_INCLUDE_DIRS | sed -E "s#(/[^ ]+)#-I\1#g") $(v VERILOG_FILES)"
  printf "hierarchy -top $TOP\nproc\nflatten\n"
  for l in $K/macros/*.lef; do m=$(basename $l .lef); echo "tee -q -o /out/sel_$m.txt select -list t:$m"; done; } > $O/i2.ys
docker run --rm --name hck3inst2-$(echo $N | cut -c1-40)-$$ --cpus=2 --memory=24g --memory-swap=24g -v $K:/work:ro -v $O:/out -w /work openroad/orfs:asap7lock bash -lc "
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 timeout 3600 yosys -q -s /out/i2.ys > /out/i2.log 2>&1; echo RC=\$? > /out/rc2
 chown -R $(id -u):$(id -g) /out"
for f in $O/sel_*.txt; do m=$(basename $f .txt); m=${m#sel_}; grep -E "^$TOP/" $f | sed "s#^$TOP/##; s#\$#=$m#"; done > $O/inst_m.txt
echo "$N $(cat $O/rc2) $(wc -l < $O/inst_m.txt)"
