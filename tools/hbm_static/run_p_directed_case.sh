#!/usr/bin/env bash
set -euo pipefail
binary=$1
cases=$(realpath "$2")
case_name=$3
out=$(realpath -m "$4")
mkdir -p "$out"
if [[ $case_name = mutant_* ]];then
 set +e
 "$binary" +CASE_DIR="$cases/$case_name" >"$out/$case_name.log" 2>&1
 status=$?
 set -e
 cat "$out/$case_name.log"
 if [ "$status" = 0 ] || ! grep -Eq 'real MB|real SE|real VM phase|real producer fault' "$out/$case_name.log";then exit 1;fi
 printf '%s\n' "$status" >"$out/$case_name.exit"
 echo "PASS actual programme $case_name rejected"
else
 "$binary" +CASE_DIR="$cases/$case_name" >"$out/$case_name.log" 2>&1
 cat "$out/$case_name.log"
fi
