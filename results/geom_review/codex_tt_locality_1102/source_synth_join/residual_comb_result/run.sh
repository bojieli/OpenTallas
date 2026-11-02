#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work/producer/residual_comb_69067efa0
python3 -I - <<'PY'
import hashlib
assert hashlib.sha256(open('miter.v','rb').read()).hexdigest()=='10643b2f55d40d4de49766fac480759da91ac3514630600519d182970e89887d'
PY
yosys -Q -T -p 'read_verilog miter.v; prep -top tt_residual_anon_d_comb; sat -verify -prove mismatch 0 -show-inputs' > production.log 2>&1
grep -q 'SAT proof finished - no model found: SUCCESS' production.log
set +e
yosys -Q -T -p 'read_verilog miter.v; prep -top tt_residual_anon_d_comb; sat -verify -prove mutant_mismatch 0 -show-inputs' > mutant.log 2>&1
mutant_rc=$?
set -e
test "$mutant_rc" -ne 0
grep -q 'proof did fail' mutant.log
python3 -I - <<'PY'
import json
open('result.json','w').write(json.dumps(dict(status='PASS_D_FUNCTION_COMBINATIONAL_ONLY',free_actual_leaf_bits=133,mutant='REJECTED',miter_sha256='10643b2f55d40d4de49766fac480759da91ac3514630600519d182970e89887d',native_base_proved=False,anonymous_aliases_accepted=False,full_lec_credit=False,physical_release=False),indent=1)+'\n')
PY
cat result.json
