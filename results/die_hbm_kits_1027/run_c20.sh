#!/bin/bash
# DIE-HBM/KITS: C20 wave = views -> mk_c20 (4 batches) -> kit_preflight.  run_c20.sh  (on intel2)
set -u
W=/srv/opentallas-scratch2/claude/wt/die-hbm-kits-1027; P=/srv/opentallas-scratch2/claude/die-hbm-1027/c20
D=/srv/opentallas-scratch2/claude/die-hbm-1027/kits/${WAVE:-c20}; mkdir -p $D; cd $D
echo "$(date) start plan $(cat $P/die_plan.sha256 2>/dev/null | cut -c1-12) src $(git -C $W rev-parse --short=10 HEAD)"
( cd $W/physical/die_plan/hbm_arch_cores && python3 views_b2r2.py --plan $P/die_plan.json --out $D/views_c20.json ) > $D/views.log 2>&1
tail -n +2 /srv/opentallas-scratch2/claude/hbm-streets3-1027/kits/native_view_kits.tsv | cut -f1 \
  | grep -v -E "tailx_sk_steady|topk_link_static" > $D/mods.txt     # OWNED-LIVE Codex: never generated here
split -n r/4 -d $D/mods.txt $D/batch_
for b in batch_00 batch_01 batch_02 batch_03; do
  MKTAG=_$b python3 $W/results/die_hbm_kits_1027/mk_c20.py $P $D/views_c20.json $D/slices_$b $D/kits $W $(paste -sd, $b) --tag _c20 > $D/mk_$b.log 2>&1 &
done
wait
echo "$(date) gen done"
bash $W/results/die_hbm_kits_1027/pf_all.sh $P $D/kits $D/preflight $W > $D/pf_all.log 2>&1
echo "$(date) preflight done"; touch $D/RUN_DONE
