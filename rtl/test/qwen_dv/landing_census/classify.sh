#!/usr/bin/env bash
set -euo pipefail
for mode in generic4 physical4 generic8 physical8; do
 python3 rtl/test/qwen_dv/landing_census/census.py /work/mapped3/$mode.json landing_vehicle > /work/mapped3/${mode}_roots.json
done
