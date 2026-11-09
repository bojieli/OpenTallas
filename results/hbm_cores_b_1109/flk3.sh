cd /srv/opentallas-scratch3/claude/rm56
n=tools_die_plan_test_landing_band_order.py.log
for t in x y; do echo "== $t"; grep -E "^(FAILED|ERROR)|^E  " $t/$n | sed -E "s#/dev/shm/rm56/[a-z0-9]+#T#g" | sort -u | head -8 | cut -c1-200; tail -n1 $t/$n | cut -c1-120; done
for t in x y; do ( cd /dev/shm/rm56/$t; p=0; for i in 1 2 3 4 5; do timeout 300 python3 -m pytest -q -p no:cacheprovider --basetemp=/dev/shm/rm56/tmp/flk3_${t}_$i "tools/die_plan/test_lec_async.py::test_physical_receipt_before_wait_and_later_scope_reuses_owner" > /dev/shm/rm56/tmp/flk3_$t.$i.log 2>&1 && p=$((p+1)); done; echo "$t lec_async pass=$p/5"; grep -hE "^E  " /dev/shm/rm56/tmp/flk3_$t.*.log | sort | uniq -c | sort -rn | head -3 | cut -c1-200 ) & done; wait
