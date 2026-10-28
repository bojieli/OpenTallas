#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-kv-9-1028/pvcount
for t in kv3_pv kv3_pv_v1 kv3_pv_v1n kv3_pv_v2 kv3_pv_v2n kv3_pv_v3 kv3_pv_v3n kv3_pv_v4 kv3_pv_v4n kv3_pv_v5 kv3_pv_v5n kv3_pv_v6 kv3_pv_v6n kv3_pv_v7 kv3_pv_v8 kv3_pv_v12; do
  until grep -q "^$t \(ys ready\|KITRTL_FAIL\|SWAP_FAIL\)" ../die-kv-9-1028/pvcount.log; do sleep 5; done
  [ -f $R/$t.ys ] || continue
  docker run -d --rm --name kv9_pvc_$t -m 24g -v /srv:/srv openroad/orfs:asap7lock bash -c "yosys -q -s $R/$t.ys > $R/$t.log 2>&1; echo rc=\$? > $R/$t.rc"
done
