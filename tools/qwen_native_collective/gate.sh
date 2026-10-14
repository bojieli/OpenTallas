#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exe=${1:?exe};out=${2:?out};mkdir -p "$out"
f=tools/qwen_native_collective/fixture
ranks=("$f/rank0.hex" "$f/rank1.hex" "$f/rank2.hex" "$f/rank3.hex" "$f/rank4.hex" "$f/rank5.hex" "$f/rank6.hex" "$f/rank7.hex")
python3 tools/qwen_native_collective/runtime.py --exe "$exe" --out "$out/positive" --words 256 --messages 2 --gap 23 --skew 5 --ranks "${ranks[@]}" --expected "$f/expected.hex"
# No expected file is read in this second run. Compare observed RTL outputs
# externally after completion; they must be identical to the checked run.
python3 tools/qwen_native_collective/runtime.py --exe "$exe" --out "$out/no_oracle" --words 256 --messages 2 --gap 23 --skew 5 --ranks "${ranks[@]}"
for rank in {0..7};do cmp "$out/positive/rank$rank.hex" "$out/no_oracle/rank$rank.hex";done
set +e
python3 tools/qwen_native_collective/runtime.py --exe "$exe" --out "$out/data_mut" --words 256 --messages 2 --ranks "$f/rank0_data_mut.hex" "${ranks[@]:1}" --expected "$f/expected.hex"
data_rc=$?
python3 tools/qwen_native_collective/runtime.py --exe "$exe" --out "$out/order_mut" --words 256 --messages 2 --ranks "${ranks[1]}" "${ranks[0]}" "${ranks[@]:2}" --expected "$f/expected.hex"
order_rc=$?
set -e
[[ "$data_rc" == 1 && "$order_rc" == 1 ]]
python3 - "$out" <<'PY'
import json,re,sys
from pathlib import Path
p=Path(sys.argv[1])
for name in ['data_mut','order_mut']:
 log=(p/name/'run.log').read_text();m=re.search(r'mismatches=(\d+)',log)
 assert m and int(m.group(1))>0 and '\nFAIL\n' in log,(name,log[-1000:])
print('PASS ACTUAL_COLLECTIVE 2x256words all8rankoutputs observer_only_optional actual_rank_data_and_order_mutants_mismatch')
PY
cat "$out/positive/run.log"
