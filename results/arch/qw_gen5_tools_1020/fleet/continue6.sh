#!/bin/bash
set -eu
S=/srv/opentallas-scratch/claude/codex-qw-gen5-tools-coupons-1020
cd "$S"
mkdir -p results6/baseline results6/projected results6/native
cp results5/baseline/* results6/baseline/
cp results5/projected/* results6/projected/
cp results5/runtime_input_receipt.json results6/runtime_input_receipt.json
python3 - <<'VERIFY'
from pathlib import Path
import json,hashlib
for n,h in json.loads(Path('harness6_sha.json').read_text()).items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h
VERIFY
docker run --rm --cpus=2 --memory=8g -v "$S:/work" -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /work/native6.py /work/projected5 /work/results6/native > /work/results6/native/openroad.log 2>&1'
iverilog -g2012 -s tb -o results6/divider.out projected5/rtl/qwen_split/qfd_ckdiv6.sv projected5/results/rtl/qw_gen5_1020/bench/tb_qfd_ckdiv6.sv
vvp results6/divider.out > results6/divider.log
iverilog -g2012 -s tb -DQFD_CKDIV6_MUT_DIV5 -o results6/divider_negative.out projected5/rtl/qwen_split/qfd_ckdiv6.sv projected5/results/rtl/qw_gen5_1020/bench/tb_qfd_ckdiv6.sv
vvp results6/divider_negative.out > results6/divider_negative.log
python3 - <<'RESULT'
from pathlib import Path
import json,hashlib
p=Path('results6');b=json.loads((p/'baseline/results.json').read_text());a=json.loads((p/'projected/results.json').read_text());n=json.loads((p/'native/results.json').read_text())
old='physical/qwen_missing_phy/nface_tall_1017/ot_qfd_ucie_x64_phy'
legacy_identical=all(f.read_bytes()==(Path('projected5')/old/f.name).read_bytes() for f in (Path('baseline')/old).iterdir() if f.is_file())
checks=dict(default_tree_byte_identical=b['legacy_tree_sha256']==a['legacy_tree_sha256'],legacy_phy_byte_identical=legacy_identical,actual_g5_sta_root_export=a['actual_g5_sta_roots']['verdict']=='PASS',native_odb_nominal=n[0]['verdict']=='PASS',native_causal_refusals=all(r['verdict']=='EXPECTED_REFUSAL' for r in n[1:]),native_marginal_reach_refused=n[0]['marginal_reach_refused'],divider_pass='QFD_CKDIV6 PASS' in (p/'divider.log').read_text(),divider_causal_fail='QFD_CKDIV6 FAIL bad=' in (p/'divider_negative.log').read_text(),source_scope_unqualified=a['actual_g5_sta_roots']['physical_qualification_eligible'] is False and json.loads(Path('inputs/clock_contract.json').read_text())['qualification'] is False)
r=dict(verdict='PASS' if all(checks.values()) else 'FAIL',checks=checks,baseline=b,projected=a,native=n,physical_qualification_eligible=a['actual_g5_sta_roots']['physical_qualification_eligible'],scope='Minimum mechanism only; no full die, route, physical clock source or release qualification')
(p/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['verdict']=='PASS' else 1)
RESULT
