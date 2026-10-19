#!/bin/bash
# L2H-P3 10-19: P3 die structural-repair chain (S3 relay-free GEN of <tag> -> S4..S8 of hnx_p4_chain.sh) from THIS worktree,
# unpinned (data locality via --dir, never --hosts).  Successor of hnx_case_run.sh (which pinned --hosts and a fixed worktree).
#   local driver:  TAG=f4c_t9p3r REACH=360 S8_MEM=256 S8_PRIO=die S8_SKIP_SHORT_UM=150 A=<artifacts> nohup bash hnx_case_run_r.sh > $A/chain.log 2>&1 &
TAG=${TAG:?TAG}; B=/srv/opentallas-scratch/claude/hnx/die_p4; W=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd); H=ot-epyc4
A=${A:?A}; mkdir -p $A; export A
echo "STEP S3 case_$TAG $(date -Is) W=$W HEAD=$(git -C $W rev-parse --short HEAD)"
# add-only sync of the tag's grant/plan inputs into the fleet case src (hardlinked GEN2 copy: never edit files in place)
for d in physical/hbm_next/die/$TAG results/arch/hbm_next_1019/die/plan/$TAG; do
  ssh $H "test ! -e $B/src/$d" || { echo "S3_SRC_EXISTS $d (refusing to overwrite)"; exit 9; }
  ssh $H "mkdir -p $B/src/$d" && rsync -a $W/$d/ $H:$B/src/$d/ || exit 9
done
scp -q $W/physical/hbm_next/die/hnx_case.sh $H:$B/ || exit 9
/home/ubuntu/bin/ot-run --priority die --mem 64 --threads 2 --dir $B -- bash $B/hnx_case.sh $TAG > $A/case_$TAG.otrun 2>&1
echo "CASE rc=$? $(date -Is)"; tail -14 $A/case_$TAG.otrun
grep -q GEN_OK $A/case_$TAG.otrun || { echo S3_CASE_FAIL; exit 11; }
scp -q $H:$B/case_$TAG/layout.png $A/case_${TAG}_layout.png
TAG=$TAG FROM=S4 OT_RUN_PRIO_ENV="" bash $W/physical/hbm_next/die/hnx_p4_chain.sh
