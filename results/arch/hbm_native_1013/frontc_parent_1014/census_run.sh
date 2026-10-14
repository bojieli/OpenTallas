#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
yosys -Q -s results/arch/hbm_native_1013/frontc_parent_1014/census.ys
