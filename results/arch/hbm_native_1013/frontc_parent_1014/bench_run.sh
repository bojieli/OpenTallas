#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "${1:-split}" = mut ]; then exec ./work_bench/Vtb +MUTCLK; else exec ./work_bench/Vtb; fi
