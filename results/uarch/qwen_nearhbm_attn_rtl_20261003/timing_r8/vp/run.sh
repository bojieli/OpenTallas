#!/bin/bash
# VP row-engine successor (stack_vp_p) + hub_p: the 82 dspark VP jobs, p = 6 blocks (new / hub_p-only / parent binaries),
# and the fenced subsystem (stack_vp_p at VMASK=1, TM=T).  Source wt10 (9a879f832).
S=/srv/opentallas-scratch/claude/nearhbm/vp10; W=/srv/opentallas-scratch/claude/nearhbm/wt10
D=/srv/opentallas-scratch/claude/qwen-rom-dspark-attn; H=/srv/opentallas-scratch/claude/nearhbm/vp8
ADM=/srv/opentallas-scratch/admit.sh
cd $S; mkdir -p bld logs res res6 resf v128 v16
st() { echo "$(date -u +%FT%TZ) $*" >> $S/STATUS.md; }
st "start"
# p = 6 vectors
( cd $W/tools && python3 qwen_nearhbm_attn_verify_ref.py --ctx0 8187 --p 6 --seed $((8187*3+6)) --kind normal --out $S/v128/8187_6_normal > $S/logs/v_8187n.log 2>&1 ) &
( cd $W/tools && python3 qwen_nearhbm_attn_verify_ref.py --ctx0 8187 --p 6 --seed $((8187*3+7)) --kind peaky --out $S/v128/8187_6_peaky > $S/logs/v_8187p.log 2>&1 ) &
( cd $W/tools && python3 qwen_nearhbm_attn_verify_ref.py --ctx0 125 --p 6 --seed $((125*3+6)) --kind mixed --out $S/v128/125_6_mixed > $S/logs/v_125m.log 2>&1 ) &
( cd $W/tools && NHB_HD=16 python3 qwen_nearhbm_attn_verify_ref.py --ctx0 121 --p 6 --seed $((121*3+6)) --kind wide --out $S/v16/121_6_wide > $S/logs/v_121w.log 2>&1 ) &
b() { local n=$1 pk=$2; shift 2; ( NHB_SWAP=hub,stackvp JOBS=8 $ADM $pk -- /usr/bin/time -v $W/rtl/test/nearhbm/hubp_swap.sh $W/rtl/test/nearhbm/build_nearhbm_tb_vp.sh $S/bld/$n "$@" > logs/build_$n.log 2>&1; echo $? > logs/build_$n.rc ) & }
b h16r_vp2 8 16 1 real 2 1
b h128r1_vp1 8 128 1 dpi 1 1
b h128r1_vp2 8 128 1 dpi 2 1
b h128r1_vp4 10 128 1 dpi 4 1
b h128r8_vp1 20 128 8 dpi 1 1
b h128r8_vp2 30 128 8 dpi 2 1
b h128r6_vp2 30 128 6 dpi 2 1
( NHB_SWAP=hub,stackvpfence VJOBS=8 $ADM 30 -- bash $W/rtl/test/nearhbm/hubp_swap.sh $W/rtl/test/qwen_sys/build_nearhbm_sys_fenced.sh $S/bld/fence 128 8 dpi -GLAYER_START_FENCE=1 > logs/build_fence.log 2>&1; echo $? > logs/build_fence.rc ) &
wait
st "builds: $(for f in logs/build_*.rc; do echo -n "$(basename $f .rc)=$(cat $f) "; done)"
# p = 6 job list
: > jobs6.txt
for d in v128/8187_6_normal v128/8187_6_peaky v128/125_6_mixed; do
  for f in 0 1 2 3 4 5; do echo "h128r1_vp1 $d $f" >> jobs6.txt; done
  for f in 0 2 4; do echo "h128r1_vp2 $d $f" >> jobs6.txt; done
  case $d in *8187*) for f in 0 1 2 3 4 5; do echo "h128r8_vp1 $d $f" >> jobs6.txt; done
    for f in 0 2 4; do echo "h128r8_vp2 $d $f" >> jobs6.txt; echo "h128r6_vp2 $d $f" >> jobs6.txt; done;; esac
done
for f in 0 2 4; do echo "h16r_vp2 v16/121_6_wide $f" >> jobs6.txt; done
run82() { b=$1; d=$2; f=$3; n=${b}__$(basename $d)__$f
  [ -x bld/$b/Vtb ] || { echo "nobuild" > res/$n.json; return; }
  bld/$b/Vtb /srv/opentallas-scratch/claude/qwen-rom-dspark-attn/$d $f 16 750 2000000 > res/$n.json 2> res/$n.err; echo $? > res/$n.rc; }
run6() { set=$1; b=$2; d=$3; f=$4; n=${b}__$(basename $d)__$f; mkdir -p res6/$set
  case $set in new) B=bld/$b/Vtb;; hubp) B=/srv/opentallas-scratch/claude/nearhbm/vp8/bld/$b/Vtb;; parent) B=/srv/opentallas-scratch/claude/qwen-rom-dspark-attn/bld/$b/Vtb;; esac
  [ -x $B ] || { echo "nobuild" > res6/$set/$n.json; return; }
  $B /srv/opentallas-scratch/claude/nearhbm/vp10/$d $f 16 750 2000000 > res6/$set/$n.json 2> res6/$set/$n.err; echo $? > res6/$set/$n.rc; }
fence() { spec=$1; f=$2; bld/fence/Vtb ../fence8/v/$spec 16 981 400000 $f > resf/fence__${spec}_f$f.json 2> resf/fence__${spec}_f$f.err; echo $? > resf/fence__${spec}_f$f.rc; }
export -f run82 run6 fence
( cat $D/jobs.txt; for s in new hubp parent; do sed "s/^/$s /" jobs6.txt; done ) > alljobs.txt
( cat $D/jobs.txt | xargs -P 32 -L 1 bash -c "run82 \$0 \$1 \$2"
  for s in new hubp parent; do sed "s/^/$s /" jobs6.txt; done | xargs -P 32 -L 1 bash -c "run6 \$0 \$1 \$2 \$3"
  for spec in 1_normal 128_normal 129_flat 512_wide; do for f in 0 97; do echo $spec $f; done; done | xargs -P 8 -L 1 bash -c "fence \$0 \$1" )
st "runs: $(ls res/*.rc res6/*/*.rc | wc -l) rc files, nonzero: $(grep -L "^0$" res/*.rc res6/*/*.rc | wc -l)"
( cd $D && python3 $W/tools/qwen_nearhbm_attn_vp_gate.py --res $S/res --vectors-root . --source-commit 9a879f832 --out $S/vp_gate_vpp.json > $S/gate.log 2>&1 )
for s in new hubp parent; do python3 $W/tools/qwen_nearhbm_attn_vp_gate.py --res $S/res6/$s --vectors-root $S --source-commit 9a879f832 --out $S/vp6_gate_$s.json > $S/gate6_$s.log 2>&1; done
st "gates done"
echo done > run.done
