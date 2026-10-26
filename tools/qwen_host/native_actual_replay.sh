#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";bin=${1:?existing source-exact binary};out=${2:?out};heads=${3:-1};mode=${4:-edge};mkdir -p "$out";out=$(cd "$out"&&pwd)
python3 tools/qwen_host/native_fixture.py "$out" "$heads" "$mode" > "$out/fixture.log"
read -r nd np ns < <(python3 - "$out/fixture.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]));print(j['descriptors'],j['beats'],j['sectors'])
PY
)
(cd "$out";"$bin" +ND="$nd" +NP="$np" +NSECTOR="$ns") > "$out/run.log" 2>&1
cat "$out/run.log";grep -q '^PASS NATIVE_ACTUAL' "$out/run.log"
