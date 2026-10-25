set -u
WT=/srv/opentallas-scratch2/claude/wt/path-kv-head-1025; H=$WT/physical/die_plan/qwen_kvsys/cores/harden; CJ=/srv/opentallas-scratch2/claude/kv-cores-1025r/heads/corejson
PLAN=/srv/opentallas-scratch2/claude/path-kv/plan_f7/physical/die_plan/qwen_kvsys/die_plan.json
rm -rf /srv/opentallas-scratch2/claude/path-kv/heads/s3k2; ssh -o ControlPath=none intel1 "rm -rf /srv/opentallas-scratch2/claude/path-kv/heads/s3k2"
O=/srv/opentallas-scratch2/claude/path-kv/heads/m3; mkdir -p $O
for e in 0 2 6; do
  python3 $H/gen_core_kit_kv.py --core-json $CJ/kv3_head_eighth_e${e}_core.json --plan $PLAN --out $O/e$e --tool $WT/tools/die_plan --head-port-regs --head-lane-ltcopy --head-lane-s3copy --head-strap-master 2>&1 | tail -1 | cut -c1-140
  K=$O/e$e/kv3_head_eighth_e${e}__216x216
  nohup ~/.local/bin/ot-run --mem 24 --threads 16 --dir $K --stage $K -- bash $K/run_kit_kv.sh $K place 24 16 > $O/e${e}_place.log 2>&1 &
done
sleep 25; grep -h "admitted" $O/e*_place.log
