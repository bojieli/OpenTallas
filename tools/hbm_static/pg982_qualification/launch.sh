#!/bin/bash
set -euo pipefail
ROOT=${1:?immutable remote run root}
MODE=${2:?bench or native}
case "$MODE" in
 bench) /home/ubuntu/bin/ot-run --mem 56 --threads 8 --dir "$ROOT/src" -- env PG982_RUN_ROOT="$ROOT" bash tools/hbm_static/pg982_qualification/bench.sh ;;
 native) /home/ubuntu/bin/ot-run --mem 32 --threads 4 --dir "$ROOT/src" -- env PG982_RUN_ROOT="$ROOT" bash tools/hbm_static/pg982_qualification/native.sh ;;
 *) exit 2 ;;
esac
