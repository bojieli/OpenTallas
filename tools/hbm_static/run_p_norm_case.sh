#!/usr/bin/env bash
set -euo pipefail
binary=$1
case_dir=$2
out=$3
mkdir -p "$out"
name=$(basename "$case_dir")
if [[ $name == mutant_* ]];then
 if "$binary" +CASE_DIR="$case_dir" >"$out/$name.log" 2>&1;then cat "$out/$name.log";echo 'FAIL mutant passed';exit 1;fi
 cat "$out/$name.log"
 grep -Eq 'real VM phase|real producer fault' "$out/$name.log"
 echo "PASS actual programme $name rejected"
else
 "$binary" +CASE_DIR="$case_dir" >"$out/$name.log" 2>&1
 cat "$out/$name.log"
fi
