#!/bin/bash
# KV-TYPES-6: remaining PV ring-band spreads with --bisect (v7, v12 timed out at 8 h linear)
cd /srv/opentallas-scratch2/claude/codex-kv-types-1113-src
E=/srv/opentallas-scratch2/claude/kv-types-6/pv/par
PD=/srv/opentallas-scratch2/claude/kw35/src_e2rd/physical/die_plan/qwen_kvsys/plan_of_record
test -f $PD/eW_sidecar.json || PD=physical/die_plan/qwen_kvsys/plan_of_record
mkdir -p $E
for t in kv3_pv_v7 kv3_pv_v12; do
 ( s=$(date +%s); /usr/local/bin/ot-heavy --mem 12 --tag kv6-rbs-$t -- timeout 7200 python3 -I -B tools/die_plan/ring_band_spread.py --types $t --bisect /srv/opentallas-scratch2/claude/type-safe-2-1108/kv/ev/plan_c.ch.json $PD/eW_sidecar.json $E/$t.plan.json $E/$t.rep.json > $E/$t.log 2>&1; echo $t rc $? $(($(date +%s)-s))s >> $E/done.txt ) &
done
wait
echo ALLDONE >> $E/done.txt
