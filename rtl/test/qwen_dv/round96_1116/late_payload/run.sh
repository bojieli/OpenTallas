#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tar -xzf source_capsule.tar.gz
cp sources_repro.f sources.f
bash build.sh
./obj/Vtb +K=2 +MODE=1 +CFG_EDGE=169 >o_late_payload.log 2>&1
./obj/Vtb +K=6 +MODE=1 +CFG_EDGE=169 >down_late_payload.log 2>&1
cat o_late_payload.log down_late_payload.log
