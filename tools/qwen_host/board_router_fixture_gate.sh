#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mkdir -p "$out/original/include" "$out/mutant/include" "$out/shared/include";out=$(cd "$out"&&pwd)
for variant in original mutant shared;do
 cp rtl/test/qwen_host/tb_qkd_host_board_router_fixture.cpp "$out/$variant/unit.cpp"
 cp rtl/test/qwen_host/include/qkd_host_board_router_fixture.hpp "$out/$variant/include/"
done
python3 - "$out" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])/'mutant/include/qkd_host_board_router_fixture.hpp';s=p.read_text()
a='credit(unsigned(source),g,1)';b='credit(unsigned((source+1)%8),g,1)'
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
p=Path(sys.argv[1])/'shared/include/qkd_host_board_router_fixture.hpp';s=p.read_text()
a='if(pending_[dest][bucket]==depth)return false';b='if(q_[dest].size()==depth)return false'
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
PY
for variant in original mutant shared;do
 "${CXX:-g++}" -std=c++17 -Wall -Wextra -Werror -O0 "$out/$variant/unit.cpp" -o "$out/$variant/unit"
done
"$out/original/unit" > "$out/original/run.log" 2>&1
set +e
"$out/mutant/unit" > "$out/mutant/run.log" 2>&1
rc=$?
set -e
[[ $rc != 0 ]];grep -q 'destination credit returned only to original source1' "$out/mutant/run.log"
set +e
"$out/shared/unit" > "$out/shared/run.log" 2>&1
rc=$?
set -e
[[ $rc != 0 ]];grep -q 'router reservation queue exhausted' "$out/shared/run.log"
cat "$out/original/run.log"
printf 'PASS BOARD_ROUTER_OWNER_MUTANT_DETECTED wrong_source_credit PIN_FIXTURE_ONLY\n'
printf 'PASS BOARD_ROUTER_SHARED_CAPACITY_MUTANT_DETECTED fullING_excludes_CTRL PIN_FIXTURE_ONLY\n'
rm "$out/original/unit" "$out/mutant/unit" "$out/shared/unit"
