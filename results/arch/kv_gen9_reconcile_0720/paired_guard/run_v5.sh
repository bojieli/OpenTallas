#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/claude/codex-kv-binding-guard-paired-0720
mirror=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
ref=c08afcc64ff982004ef092375996905b90bd7836
if ! git --git-dir="$mirror" cat-file -e "$ref^{commit}"; then git --git-dir="$mirror" fetch https://github.com/bojieli/OpenTallas main; fi
if [ ! -f "$base/src/.git" ]; then git --git-dir="$mirror" worktree add --detach --no-checkout "$base/src" "$ref" >> "$base/checkout.log" 2>&1; fi
# Materialize the immutable revision without changing shared mirror/worktree config.
if [ ! -f "$base/src/tools/qwen_kv_die/test_phy_fdi_binding.py" ]; then
 git --git-dir="$mirror" archive "$ref" tools rtl physical results/arch results/rtl | tar -x -C "$base/src"
fi
git --git-dir="$mirror" show "$ref:tools/qwen_kv_die/kv_bound_netlist.py" > "$base/src/tools/qwen_kv_die/kv_bound_netlist.py"
if [ ! -d "$base/python_deps/pytest" ]; then python3 -m pip install --target "$base/python_deps" pytest > "$base/install_pytest.log" 2>&1; fi
export PYTHONPATH="$base/python_deps${PYTHONPATH:+:$PYTHONPATH}"
for f in base.log projected.log base.xml projected.xml comparison.json; do if [ -f "$base/$f" ]; then cp "$base/$f" "$base/unpinned_$f"; fi; done
export KV_PARAMETER_ACTUAL_ROOT="$base/src"
cd "$base/src"
files=(tools/qwen_kv_die/test_kv_expand_alias.py tools/qwen_kv_die/test_kv_expand_parameters.py tools/qwen_kv_die/test_phy_fdi_binding.py)
python3 -m pytest -q "${files[@]}" --junitxml="$base/base.xml" > "$base/base.log" 2>&1 || echo "$?" > "$base/base.rc"
cp tools/qwen_kv_die/kv_bound_netlist.py "$base/base_kv_bound_netlist.py"
cp "$base/projected_kv_bound_netlist.py" tools/qwen_kv_die/kv_bound_netlist.py
python3 -m pytest -q "${files[@]}" --junitxml="$base/projected.xml" > "$base/projected.log" 2>&1 || echo "$?" > "$base/projected.rc"
python3 "$base/check_binding_source_guard.py" --root . > "$base/causal.json"
python3 - "$base" <<'PY'
from pathlib import Path
import json,sys,xml.etree.ElementTree as ET,hashlib
b=Path(sys.argv[1]);out={}
for side in ['base','projected']:
 root=ET.parse(b/f'{side}.xml').getroot();tests=root.findall('.//testcase');failed=[f"{x.get('classname')}::{x.get('name')}" for x in tests if x.find('failure') is not None or x.find('error') is not None];out[side]=dict(tests=len(tests),failed_ids=sorted(failed),skipped=sum(x.find('skipped') is not None for x in tests))
out['new_failure_ids']=sorted(set(out['projected']['failed_ids'])-set(out['base']['failed_ids']));out['removed_failure_ids']=sorted(set(out['base']['failed_ids'])-set(out['projected']['failed_ids']));out['base_ref']='c08afcc64ff982004ef092375996905b90bd7836';out['source_sha256']={n:hashlib.sha256((b/n).read_bytes()).hexdigest() for n in ['base_kv_bound_netlist.py','projected_kv_bound_netlist.py']};(b/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
PY
