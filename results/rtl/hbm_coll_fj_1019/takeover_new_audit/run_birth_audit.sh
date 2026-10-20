#!/bin/bash
set -u
q=$1; gate=$2
if test "$q" = 3;then top=ot_hgi_coll_fj_n2s1_r128;else top=ot_hgi_coll_fj_q2_r128;fi
tag=fj${q}birth
rc=0
python3 run_audit.py "$PWD" "$gate" "$top" "$tag" || rc=1
bash post_native.sh "$q" "$gate" || rc=1
docker run --rm -v "$PWD:/audit" -v "$gate:/frozen:ro" -e AUDIT_ODB=/frozen/routes/gate/work/orfs/results/asap7/opentallas_${top}_asap7_ref_gate/base/5_1_grt.odb -e AUDIT_REACH_REPORT=/audit/${tag}_sequential_reach.json -e AUDIT_OUT=/audit/${tag}_unreached_classes.json --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 -exit -python /audit/classify_unreached.py > ${tag}_unreached.log 2>&1 || rc=1
exit "$rc"
