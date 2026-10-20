#!/bin/bash
set -eu
S=/srv/opentallas-scratch/claude/codex-qw-gen5-tools-coupons-1020
cd "$S"
mkdir -p baseline projected results2/baseline results2/projected results2/native
tar -C baseline -xf baseline.tar
tar -C projected -xf projected.tar
mkdir -p pytest_portable
tar -C pytest_portable -xf pytest_portable.tar
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
QW_COUPON_PY=python3
python3 cohort.py baseline results2/baseline inputs > results2/baseline/cohort.log 2>&1
python3 cohort.py projected results2/projected inputs > results2/projected/cohort.log 2>&1
PYTHONPATH="$S/pytest_portable:$S/baseline/tools:$S/baseline/tools/die_clock" "$QW_COUPON_PY" -m pytest -q baseline/tools/die_clock/test_regtree.py baseline/tools/die_clock/test_spine.py baseline/tools/die_clock/test_targets.py baseline/tools/die_clock/test_view_targets.py > results2/baseline/tests.log 2>&1
PYTHONPATH="$S/pytest_portable:$S/projected/tools:$S/projected/tools/die_clock" "$QW_COUPON_PY" -m pytest -q projected/tools/die_clock/test_reach_coverage.py projected/tools/die_clock/test_gen5_sources.py projected/tools/die_clock/test_receiver_guard.py projected/tools/die_clock/test_safe_tree.py projected/tools/die_clock/test_spine.py projected/tools/die_clock/test_targets.py projected/tools/die_clock/test_regtree.py projected/tools/die_clock/test_view_targets.py projected/tools/qwen_tp8/test_gen5_clock_roots.py projected/tools/qwen_tp8/test_source_clock_contract.py > results2/projected/tests.log 2>&1
docker run --rm --cpus=2 --memory=8g -v "$S:/work" -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /work/native_odb.py /work/projected /work/results2/native > /work/results2/native/openroad.log 2>&1'
iverilog -g2012 -s tb -o results2/divider.out projected/rtl/qwen_split/qfd_ckdiv6.sv projected/results2/rtl/qw_gen5_1020/bench/tb_qfd_ckdiv6.sv
vvp results2/divider.out > results2/divider.log
iverilog -g2012 -s tb -DQFD_CKDIV6_MUT_DIV5 -o results2/divider_negative.out projected/rtl/qwen_split/qfd_ckdiv6.sv projected/results2/rtl/qw_gen5_1020/bench/tb_qfd_ckdiv6.sv
vvp results2/divider_negative.out > results2/divider_negative.log
python3 - <<'PY'
from pathlib import Path
import json
p=Path('results2');b=json.loads((p/'baseline/results.json').read_text());a=json.loads((p/'projected/results.json').read_text());n=json.loads((p/'native/results.json').read_text())
checks=dict(default_tree_byte_identical=b['legacy_tree_sha256']==a['legacy_tree_sha256'],actual_g5_sta_root_export=a['actual_g5_sta_roots']['verdict']=='PASS',native_odb_nominal=n[0]['verdict']=='PASS',native_causal_refusals=all(r['verdict']=='EXPECTED_REFUSAL' for r in n[1:]),divider_pass='QFD_CKDIV6 PASS' in (p/'divider.log').read_text(),divider_causal_fail='QFD_CKDIV6 FAIL bad=' in (p/'divider_negative.log').read_text(),source_scope_unqualified=a['physical_qualification_eligible'] is False and a['actual_g5_sta_roots']['physical_qualification_eligible'] is False)
r=dict(verdict='PASS' if all(checks.values()) else 'FAIL',checks=checks,baseline=b,projected=a,native=n,physical_qualification_eligible=False,scope='Minimum mechanism only; no full die, route, physical clock source or release qualification')
(p/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['verdict']=='PASS' else 1)
PY
