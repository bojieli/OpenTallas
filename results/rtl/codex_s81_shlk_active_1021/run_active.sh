#!/usr/bin/env bash
set -euo pipefail
O=../out_active;mkdir -p "$O"
find rtl physical -type f -name '*.sv' -o -name '*.v' | sort | xargs sha256sum > "$O/sources.sha256"
export VL_EXTRA="-DOT_N32_LEFT_SPLIT -DOT_N32_ADDR_CSA -DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E -DOT_S81_SH_ACKP -DTB_HSH=8 -DTB_HSC=9"
bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh "$O/seqhost" '1 2' > "$O/seqhost.log" 2>&1
cat "$O/seqhost.log"
export N32_EXTRA="-DOT_N32_ADDR_CSA -DOT_N32_LEFT_SPLIT"
bash rtl/hdc/ingest/test/run_n32_lockstep.sh "$O/n32_base" '1 2 3' > "$O/n32_base.log" 2>&1
cat "$O/n32_base.log"
for m in BYP GOD WIN KIND FQS CQR;do
 set +e
 bash rtl/hdc/ingest/test/run_n32_lockstep.sh "$O/n32_$m" 1 "$m" > "$O/n32_$m.log" 2>&1
 rc=$?
 set -e
 cat "$O/n32_$m.log"
 test "$rc" = 1
 grep -q '^FAIL LOCKSTEP' "$O/n32_$m/run_1.log"
 echo "ACTIVE_N32_CONTROL $m CAUGHT"
done
echo ACTIVE19_GATE_PASS
