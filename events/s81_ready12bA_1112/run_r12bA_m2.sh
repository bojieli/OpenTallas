#!/bin/bash
# B3b sidecar collector sync (both bind trees, links broken), bind (elab reused from out_r12bA_m) into out_r12bA_m2, verify
O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; SRC=$O/bsrc_r12bA_m; AB=$O/asbuilt_lfcs_m.json; OUT=$O/out_r12bA_m2; P=physical/die_plan/s81/plan_r12bA3.json
export PYTHONDONTWRITEBYTECODE=1; set -o pipefail
H=physical/die_plan/s81/h2_2249
for sc in landed_sidecar_h2_psplit_all landed_sidecar_h2_psplit_all_gear; do
  python3 -I $O/r12b/stage_sidecar_collector_sync.py $O/r12b/s3_band.json $O/bsrc_main2_lfcs/$H/$sc.json $O/r12b/$sc.sync.json $O/r12b/r3b_$sc.json --expect 2 || exit 4
  for t in bsrc_main2_lfcs bsrc_r12bA_m; do cp --remove-destination $O/r12b/$sc.sync.json $O/$t/$H/$sc.json; done
done
sha256sum $O/bsrc_main2_lfcs/$H/landed_sidecar_h2_psplit_all.json $O/bsrc_r12bA_m/$H/landed_sidecar_h2_psplit_all.json | cut -c1-12
cp --remove-destination $SRC/$P $SRC/physical/die_plan/s81/plan_h2_2249.json
rm -rf $OUT; mkdir -p $OUT; cp -a $O/out_r12bA_m/. $OUT/; rm -rf $OUT/rtl $OUT/bind_report.json $OUT/verify
cd $SRC || exit 9
echo "plan $(sha256sum < $P | cut -c1-12) plan_h2_2249 $(sha256sum < physical/die_plan/s81/plan_h2_2249.json | cut -c1-12)"
prlimit --as=100000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py bind $P --asbuilt $AB --out $OUT --strict > $O/r12b/bind_m2.log 2>&1; echo BIND_RC=$?
prlimit --as=150000000000 nice -n 5 python3 -I -B tools/die_plan/bind.py verify $P --asbuilt $AB --out $OUT --strict > $O/r12b/verify_m2.log 2>&1; echo VERIFY_RC=$?
