#!/bin/bash
# Qwen TP4 asynchronous collective campaign (claude/qwen-async-collective-20261003 @ $(cat SOURCE_REF))
E=/srv/opentallas-scratch/claude/qwen-async-coll
cd $E/src
A='--tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 --tws 38 --ord 7 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll'
O="--token-oracle $E/in/oracle_tp4 --preload $E/in/qwen-vocab-embed-token0/vm_x_fp32.hex"
mkdir -p $E/res $E/exit
step() { echo "$(date -Is) START $1" >> $E/chain.log; }
done_() { echo $2 > $E/exit/$1.rc; echo "$(date -Is) END $1 rc=$2" >> $E/chain.log; }
# J0: fused-epilogue exactness gate (record), in parallel with the build
( step J0_fused_gate; cd tools && rm -rf $E/fe && python3 qwen_fused_epilogue_gate.py --work $E/fe --result $E/res/fused_epilogue_gate.json --seeds 3 > $E/J0.log 2>&1; done_ J0_fused_gate $? ) &
# J1: build
step J1_build
python3 tools/qwen_rom_rt_token_async_w12.py --workdir $E/bld --stages /dev/null $O $A --threads 28 --jobs 100 --build-only > $E/J1_build.log 2>&1
rc=$?; done_ J1_build $rc; [ $rc = 0 ] || { wait; exit 1; }
# J2: A/B/C/D on the one binary (A one-stream img256; B fused; C cut; D fused+cut)
for r in A:img256 B:imgF C:imgC D:imgFC E:imgFC_L0; do
  n=run${r%%:*}; img=${r#*:}; st=$E/$img/stages.txt; [ $n = runE ] && st=$E/imgFC_L0.txt
  rm -rf $E/$n && cp -al $E/bld $E/$n && rm -f $E/$n/qwen_rom_rt $E/$n/*.log $E/$n/*.rss
  ( step J2_$n; [ $n = runE ] && export RT_ITRACE=1; python3 tools/qwen_rom_rt_token_async_w12.py --workdir $E/$n --stages $st $O $A --threads 24 --jobs 8 --result $E/res/$n.json > $E/$n.out 2>&1; done_ J2_$n $? ) &
done
wait
echo "$(date -Is) ALLDONE" >> $E/chain.log
