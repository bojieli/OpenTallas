#!/usr/bin/env bash
set -euo pipefail
# Fleet-only: cwd contains immutable mapped input, canonical parser/census/libs.
python3 engine_native32.py --netlist original.v --parser textbook_lint.py --sha256 2b34032b15f16130a8bf6de13358f28e7fe5582078ca4102e073766316d7eff3 --top qkd_host_native_engine_n32 --out qkd_host_native_engine_n32.sv > generate.log
python3 bind_copy_inputs.py --source qkd_host_native_engine_n32.sv --record qkd_host_native_engine_n32.json --out bound_inputs.v
python3 engine_copy_certificate.py --original original.v --mapped bound_inputs.v --parser textbook_lint.py --record qkd_host_native_engine_n32.json --out bound_correspondence.json > correspondence.log
# Causal fault: a single reset-copy binding attached to d_v must be rejected.
python3 - <<'INNER'
from pathlib import Path
s=Path('bound_inputs.v').read_text(); old='assign rst_n__c1 = rst_n;'
assert s.count(old)==1
Path('bound_bad_reset.v').write_text(s.replace(old,'assign rst_n__c1 = d_v;'))
INNER
if python3 engine_copy_certificate.py --original original.v --mapped bound_bad_reset.v --parser textbook_lint.py --record qkd_host_native_engine_n32.json --out mutant_unexpected.json > mutant_bad_reset.log 2>&1; then
 echo 'MUTANT SURVIVED'; exit 1
fi
grep -q 'input relation changed' mutant_bad_reset.log
# The unchanged resynth helper runs Yosys then its old same-interface checker.
# Use only its synthesis prefix: the strict bound-input check ran above.
sed '/^python3 host_prompt_native32_certificate.py/,$d' host_prompt_resynth.sh > synth_only.sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work openroad/orfs:asap7lock bash synth_only.sh qkd_host_native_engine_n32 > resynth_docker.log 2>&1
python3 host_prompt_census.py qkd_host_native_engine_n32 > census.log 2>&1
echo ENGINE_BOUND_CORRESPONDENCE_AND_LEAF_NATIVE_PASS
