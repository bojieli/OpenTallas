#!/bin/bash
# owner rule: minimum components. L0 two-step job (verify P=255 np4 -> commit 1 -> verify P'=256 np4 over the RTL HBM),
# AR L0 at P=255, heads H0 (p=1), H1/H2 (p=4 + accept), drafter layer D0 (S=3).
E=/srv/opentallas-scratch/claude/qwen-dspark-system; SRC=$E/src-aec77a75f; C=$E/comp
step() { echo "$(date -u +%FT%TZ) $*" >> $E/chain.log; }
cd $SRC
step "components start src $(cat SOURCE_REF)"
python3 tools/qwen_dspark_step_plans.py --oracle $E/oracle --img4 $E/img_p4 --img1 $E/img_p1 --out $C --layers 1 > $E/plans.log 2>&1 || { step "plans failed"; exit 1; }
python3 tools/qwen_rom_rt_vprm_w12.py --workdir $E/bld --build-only --hbm-layers 3 --code-banks 1 --jobs 32 > $E/build_fix.log 2>&1; step "relink rc=$?"
run() { # name jobdir extra
  local n=$1 j=$2; shift 2
  /srv/opentallas-scratch/admit.sh 6 -- python3 tools/qwen_rom_rt_vprm_w12.py --workdir $E/runs/$n --build-dir $E/bld --hbm-layers 3 --code-banks 1 \
     --plan $j/plan --expect $j/expect.json --result $E/res/$n.json --threads 6 "$@" > $E/runs/$n.out 2>&1
  echo $? > $E/runs/$n.rc; step "$n rc=$(cat $E/runs/$n.rc)"; }
rm -rf $E/runs/c_* ; mkdir -p $E/res
run c_L0 $C/L0 --kv-dir $E/oracle/kv_P255 &
run c_AR0 $C/AR0 --kv-dir $E/oracle/kv_P255 &
run c_H0 $C/H0 &
run c_H1 $C/H1 &
run c_H2 $C/H2 &
run c_D0 $E/drafter/g0 --kv-dir $E/drafter/g0/kv &
wait
step "components done"
