#!/bin/sh
# DIE-QC-85 11-06: plan_qc53 candidate v3 = START4 base (Codex plan_qc53_candidate_v2, sha256
# 6641f0fdf7497b673818b8c87b2ff11cb2ebc6a1f8516663b93c33fef14576e9) + SU2 south channel + tap class (qc53) + CBN ring split.
# Order matters: SU2 and tap are hash-guarded on the v2 base types (disjoint type sets); CBN split last (it rewrites the
# 2 cbn_q00 types after their tap patch). Must run with the intermediate plan inside plan_of_record/ (pin tables).
set -e
BASE=$1; R=$(cd "$(dirname "$0")/../../../.." && pwd); Q=$R/physical/die_plan/qwen_compute; T=$(mktemp -d)
python3 -I $Q/su2_channel_1106/apply_event.py --plan "$BASE" --out-plan $T/s1.json
python3 -I $Q/tap_density_class_1106/qc53/apply_event.py $T/s1.json $Q/plan_of_record/_s2_tmp.json
python3 -I $Q/delta_cbn_ring_split_1106.py $Q/plan_of_record/_s2_tmp.json $Q/plan_of_record/plan_qc53_candidate_v3.json $T/cbn_report.json
rm -f $Q/plan_of_record/_s2_tmp.json; sha256sum $Q/plan_of_record/plan_qc53_candidate_v3.json
