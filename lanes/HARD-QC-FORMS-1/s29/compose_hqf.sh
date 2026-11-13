#!/bin/bash
# HARD-QC-FORMS-1 s29 form compose (final): compose_hqf.sh BASE_PLAN OUT_PLAN [forms...]   TREE env = a tree with tools/die_plan
# order: guarded hqf_apply deltas (CONFLICT exit 3), then F-STM-REACH (stations + reach_fix.sync_fixed_cycles).
# No forwarded-clock re-point here: R-REACH-4 (reach_rules fix --rules 4) runs die-wide in the event AFTER these forms.
set -euo pipefail; cd /
S=$(cd "$(dirname "$0")" && pwd); TREE=${TREE:-$S/../tree}; B=$(readlink -f $1); O=$2; shift 2
FORMS=${*:-f_stm f_su_coll f_suc2 f_sul1 f_cb f_sta2}; W=$(dirname $O)/hqf_work; mkdir -p $W
cur=$B; i=0
for f in $FORMS; do i=$((i+1)); nxt=$W/p$i.json
  python3 -I $S/hqf_apply.py $cur $S/$f.json $nxt $W/rep_$f.json | tail -1; cur=$nxt; done
case " $FORMS " in *" f_stm "*) ( cd $TREE && python3 -I $S/form_stm_reach.py $cur $O $W/rep_stm_reach.json | head -1 );; *) cp $cur $O;; esac
echo "COMPOSE base=$(sha256sum < $B | cut -c1-12) out=$(sha256sum < $O | cut -c1-12) forms=$FORMS"
