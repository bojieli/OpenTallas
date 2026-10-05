#!/bin/bash
# Detached chain for stream qwen-rom-dspark (step 1 verify-layer gate).  Survives agent death.
# 1 build (VPOS+ARP die), 2 L0/L1 verify layers at p=1,2,4 (parallel), 3 head stage p=1,4 once head inputs exist.
E=/srv/opentallas-scratch/claude/qwen-rom-dspark
SRC=$E/src-a0c4818dd
cd $SRC
B="--tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --coll-lat 339 --coll-depth 1024 --enable-ar256 --vpos 1 --enable-arp 1"
step() { echo "$(date -u +%FT%TZ) $*" >> $E/chain.log; }
step "build start"
python3 tools/qwen_rom_rt_verify_w12.py --workdir $E/bld --stages /dev/null --token-oracle $E/oracle_tp4 --preload $E/preload_p1.hex $B --threads 32 --jobs 96 --build-only > $E/build.log 2>&1
rc=$?; echo $rc > $E/build.rc; step "build rc=$rc"
[ $rc = 0 ] || exit $rc
mkdir -p $E/res
for r in run1 run2 run4; do rm -rf $E/$r && cp -al $E/bld $E/$r && rm -f $E/$r/qwen_rom_rt $E/$r/*.log $E/$r/*.rss; done
run() { # name p oracle preload xbases stages
  python3 tools/qwen_rom_rt_verify_w12.py --workdir $E/$1 --stages $6 --token-oracle $3 --preload $4 $B --threads 32 --jobs 8 --positions $2 ${5:+--xbases $5} --result $E/res/$1.json > $E/$1.out 2>&1
  echo $? > $E/$1.rc; step "$1 rc=$(cat $E/$1.rc)"; }
step "layer runs start"
run run1 1 $E/oracle_tp4 $E/preload_p1.hex "" $E/img_p1/stages.txt &
run run2 2 $E/oracle_p2 $E/preload_p2.hex 8192,101232 $E/img_p2/stages.txt &
run run4 4 $E/oracle_p4 $E/preload_p4.hex 16384,109424,202464,295504 $E/img_p4/stages.txt &
wait
step "layer runs done"
# head stage: needs $E/head_oracle_p4/{oracle.json,vm_x_block.hex} and $E/img_head_p{1,4}/stages_head.txt (copied in by the agent)
for i in $(seq 1 720); do [ -f $E/HEAD_READY ] && break; sleep 60; done
[ -f $E/HEAD_READY ] || { step "head inputs never arrived"; exit 0; }
for r in head1 head4; do rm -rf $E/$r && cp -al $E/bld $E/$r && rm -f $E/$r/qwen_rom_rt $E/$r/*.log $E/$r/*.rss; done
step "head runs start"
run head4 4 $E/head_oracle_p4 $E/head_oracle_p4/vm_x_block.hex 16384,109424,202464,295504 $E/img_head_p4/stages_head.txt &
run head1 1 $E/head_oracle_p1 $E/head_oracle_p1/vm_x_block.hex 4096 $E/img_head_p1/stages_head.txt &
wait
step "chain done"
