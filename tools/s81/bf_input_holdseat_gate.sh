#!/bin/bash
# Run only through the host admission guard in a clean, source-pinned checkout.
set -eu
run=${1:?absolute output directory}
mkdir -p "$run"
python3 - "$run" <<'PY'
import ast, hashlib, json, pathlib, sys
# Evaluate the actual component function from the unified model. Importing
# every architecture also loads unrelated physical artifacts; this minimum
# component gate needs the hold-seat model and its complete accounting only.
source = pathlib.Path('tools/uarch_model.py').read_bytes()
tree = ast.parse(source, filename='tools/uarch_model.py')
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name == 's81_bf_input_holdseat_model']
assert len(functions) == 1
namespace = {}
exec(compile(ast.Module(body=functions, type_ignores=[]), 'tools/uarch_model.py', 'exec'), namespace)
r = namespace['s81_bf_input_holdseat_model'](seats=4)
r['unified_model_source_sha256'] = hashlib.sha256(source).hexdigest()
pathlib.Path(sys.argv[1], 'model.json').write_text(json.dumps(r, indent=2)+'\n')
assert r['added_cycles'] == 0 and r['capture_rate_beats_per_cycle'] == 1
print('BF_INPUT_HOLDSEAT_MODEL candidate_no_timing_credit=1')
PY
set +e
/usr/bin/time -v python3 tools/s81/bf_txn_bench.py --variant recut --level 2 \
    --params INPUT_HOLD_SEATS=4,CG=0 --jobs 8 --work "$run/exact" \
    --no-default-mutants --mutant mutant_input_seat=BF_INPUT_SEAT_MUTANT \
    > "$run/exact.log" 2>&1
result=$?
set -e
echo "$result" > "$run/exact.exit"
exit "$result"
