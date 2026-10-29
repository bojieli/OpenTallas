#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81-cores-resume1029/hash_proof
tool_bin=/home/ubuntu/.local/opentallas-tools/bin
cd "$r"
"$tool_bin/verilator" --binary --timing --build-jobs 4 --top-module hash_add_tb --Mdir "$r/obj" -Wall -Wno-fatal -Werror-WIDTH -Werror-SELRANGE "$r/hash_add_miter.sv" "$r/hash_add_tb.sv" > "$r/build.log" 2>&1
"$r/obj/Vhash_add_tb" > "$r/lockstep.log" 2>&1
"$tool_bin/yosys" -Q -T -p "read_verilog -sv $r/hash_add_miter.sv; prep -top hash_add_miter; flatten; memory_map; opt; sat -prove equal64 1 -prove equal28 1 -show-inputs" > "$r/formal.log" 2>&1
for w in 64 28;do
 "$tool_bin/yosys" -Q -T -p "read_verilog -sv $r/hash_add_miter.sv; prep -top hash_add_miter; flatten; memory_map; opt; sat -prove mut_equal$w 1 -show-inputs" > "$r/mutant$w.log" 2>&1
done
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('.')
assert 'LOCKSTEP PASS' in (p/'lockstep.log').read_text()
assert 'no model found: SUCCESS!' in (p/'formal.log').read_text()
for w in (64,28):assert 'model found: FAIL!' in (p/f'mutant{w}.log').read_text()
s=dict(lockstep=(p/'lockstep.log').read_text().splitlines()[0],formal='PASS all 128+56 input bits symbolic, both widths',wrong_carry_mutants='CAUGHT 64 and28 by formal counterexamples',added_cycles=0)
(p/'result.json').write_text(json.dumps(s,indent=1)+'\n');print(json.dumps(s,indent=1))
PY
