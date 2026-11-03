#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
yosys -Q -T -s source_join.ys >source_join.log 2>&1
echo TT_NATIVE_SOURCE_HIERARCHY_DONE
