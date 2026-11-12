#!/bin/bash
# s26 v2 (779178a990b5) gates with the v2 gate tree src_s26b (= v1 tools + land-ring-2 506b5064f28d); s25 baseline from v1.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-event-s26/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr; S=$W/src_s26b; P=plan_qc99_s26; PL=$W/planq/$P.json; V=v2
echo "gates2 start $(date) plan=$(sha256sum $PL|cut -c1-12) gen_phys=$(sha256sum $S/tools/die_plan/gen_phys.py|cut -c1-12)"
( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $W/schema_${P}_$V.log 2>&1; echo "rc=$?" >> $W/schema_${P}_$V.log ) &
( mkdir -p $W/g0_${P}_$V; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $W/g0_${P}_$V --quiet > $W/g0_${P}_$V.log 2>&1; echo "rc=$?" >> $W/g0_${P}_$V.log ) &
( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $W/station_lint_${P}_$V.tsv > $W/station_lint_${P}_$V.log 2>&1; echo "rc=$?" >> $W/station_lint_${P}_$V.log ) &
( O=$W/bind_${P}_$V; L=$W/bind_${P}_$V.log; echo "bind start $(date) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12)" > $L
  rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait
echo "gates2 end $(date)"
