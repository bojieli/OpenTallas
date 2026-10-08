#!/bin/bash
# ttv_install.sh <SRC> NAME=REPO_DIR [...]  (TT-VIEWS 2026-10-07): copy the view NAME (LEF + SS/FF/TT Liberty from one
# routed db, pushed by tools/tt_views/ttv.py next to this script) into the job snapshot <SRC>/REPO_DIR, overwriting the
# job commit's copy.  Idempotent; fails if any file is missing so the job never routes without its TT view.
set -euo pipefail
T=$(cd "$(dirname "$0")" && pwd); S=${1:?src}; shift
for nv in "$@"; do
  n=${nv%%=*}; d=${nv#*=}
  mkdir -p "$S/$d"
  for f in $n.lef ${n}_ss.lib ${n}_ff.lib ${n}_tt.lib; do
    [ -s "$T/$n/$f" ] || { echo "ttv_install: $T/$n/$f missing" >&2; exit 2; }
    cp "$T/$n/$f" "$S/$d/$f"
  done
  [ -f "$T/$n/PRODUCED.json" ] && cp "$T/$n/PRODUCED.json" "$S/$d/TTV_PRODUCED.json"
  echo "ttv_install: $n -> $S/$d ($(sha256sum "$S/$d/${n}_tt.lib" | cut -c1-12))"
done
