R=/srv/opentallas-scratch2/claude/wt/master-plan-r6-main-ref; W=/srv/opentallas-scratch2/claude/wt/master-plan-r6-1026; D=/srv/opentallas-scratch2/claude/master-plan-r6-1026/bi
run(){ t=$1; n=$2; d=$3; rm -rf $D/$n; cd $t && prlimit --as=60000000000 /usr/bin/time -v python3 -u -X faulthandler tools/die_plan/die_infra.py master-plan $R/physical/die_plan/$d/die_plan.json --out $D/$n > $D/$n.log 2>&1; }
for d in s81 s81_head qwen_compute qwen_kvsys hbm; do run $R main_$d $d & run $W r6_$d $d & done
wait
