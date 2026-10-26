#!/bin/bash
# PATH-KV-HEAD: S3_COPY master RTL kits (copies of codex master kits newN + S3_COPY RTL) + lockstep vs constant variants
set -eu
M=/srv/opentallas-scratch2/claude/codex-kv-cores-0719/miter
WT=/srv/opentallas-scratch2/claude/wt/path-kv-head-1025
H=$WT/physical/die_plan/qwen_kvsys/cores/harden
D=/srv/opentallas-scratch2/claude/path-kv/s3miter
rm -rf $D; mkdir -p $D
for e in 0 2 6; do
  mkdir -p $D/s3_$e; cp $M/new$e/config.mk $M/new$e/core.json $D/s3_$e/; cp -r $M/new$e/rtl $D/s3_$e/rtl
  cp $WT/rtl/hdc/nearhbm/ot_qkh_subtiles.sv $D/s3_$e/rtl/ot_qkh_subtiles.sv
  n=$(grep -c "ot_qkh_lane8 #(" $D/s3_$e/rtl/kv3_head_eighth_e$e.sv)
  sed -i 's/ot_qkh_lane8 #(/ot_qkh_lane8 #(.S3_COPY(1), /' $D/s3_$e/rtl/kv3_head_eighth_e$e.sv
  echo "e$e lane8 instances $n"
done
# case: name old master bsel hid
cases="0:0:0:00:1 2:2:2:01:1 4:4:6:10:0 6:6:6:11:0"
for c in $cases; do IFS=: read nm o m b h <<<"$c"
  python3 $H/head_master_miter.py $M/old$o $D/s3_$m $D/c$nm --port-map $M/portmap$o.json --strap "strap_bsel=2'b$b" > $D/c$nm.gen.log 2>&1 || { echo gen fail c$nm; cat $D/c$nm.gen.log; }
done
python3 $H/head_master_miter.py $M/old4 $D/s3_6 $D/c4 --port-map $M/portmap4.json --new-mod kv3_head_eighth_e6 --strap "strap_bsel=2'b10" > $D/c4.gen.log 2>&1
# negative: e6 master with wrong BSEL (2 instead of 3)
python3 $H/head_master_miter.py $M/old6 $D/s3_6 $D/mut6 --port-map $M/portmap6.json --strap "strap_bsel=2'b10" > $D/mut6.gen.log 2>&1
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
one() { cd $D/$1 && verilator --binary --timing -j 4 -MAKEFLAGS 'OBJCACHE=' -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 && ./obj/Vtb > sim.log 2>&1; echo "$1: $(grep 'CORE MITER' $D/$1/sim.log 2>/dev/null || echo BUILD/RUN FAIL)"; }
for c in c0 c2 c4 c6 mut6; do one $c & done; wait
