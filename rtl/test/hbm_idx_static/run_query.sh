#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
mkdir -p out
for m in 0 1 2 3; do
  iverilog -g2012 -s tb_query_static -Ptb_query_static.MUT="$m" -o "out/q$m.vvp" *.sv > "out/qbuild$m.log" 2>&1
  set +e
  vvp "out/q$m.vvp" > "out/qrun$m.log" 2>&1
  rc=$?
  set -e
  cat "out/qrun$m.log"
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
done
