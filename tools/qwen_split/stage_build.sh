#!/bin/bash
# stage_build.sh TAG : stage a compute-die build tree on ot-epyc4 (base = the g9 staged physical view subset, overlay = this
# worktree's committed HEAD: tools rtl results/arch results/uarch results/floorplan physical/{common,qwen_missing_phy,asap7_memory_macros_v2_ew})
# and print the ot-run command of the build (relay plan + cuts + reset + pin_align + case + assigned pins).
# Extra build env (e.g. the C4 tile slot) comes from OT_STAGE_ENV="K=V K=V".
set -eu
T=$1; WT=$(cd $(dirname $0)/../.. && pwd); H=ot-epyc4; B=/srv/opentallas-scratch/claude/qwen-split-compute; S=$B/$T
REV=$(git -C $WT rev-parse --short=9 HEAD)
ssh -o ControlPath=none $H "mkdir -p $S/src $S/out && cd $S/src && { [ -d physical/ref_tile ] || cp -a /home/ubuntu/scratch-tp8-r10/g9/src/physical . ; }"
git -C $WT archive --format=tar HEAD tools rtl results/arch results/uarch results/floorplan results/rtl/qwen_dspark_system_20261004/ctx8k/k_AR0.json physical/common physical/common_flow physical/qwen_kv_die_phy physical/qwen_missing_phy physical/asap7_memory_macros_v2_ew $(git -C $WT ls-tree -d --name-only HEAD physical/ref_tile/ | grep "/qfd_") \
  | ssh -o ControlPath=none $H "cd $S/src && tar xf - && echo $REV > SOURCE_COMMIT"
cat <<EOS | ssh -o ControlPath=none $H "cat > $S/run.sh && chmod +x $S/run.sh"
#!/bin/bash
cd $S/src || exit 9
env OT_TP8_SPLIT=compute ${OT_STAGE_ENV:-} OT_RELAY_GATE=warn OT_RESET_GATE=warn OT_PIN_ALIGN_GATE=warn OT_RELAY_DUMP=../dump.json python3 tools/qwen_tp8/relay_data_run.py ../out --case > ../out.log 2>&1
rc=\$?; echo "rc=\$rc" >> ../out.log; exit \$rc
EOS
echo "staged $H:$S src $REV"
