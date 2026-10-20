#!/bin/bash
set -eu
docker run --rm -v "$PWD:/w" -w /w openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l off_step_equiv.log -s off_step_equiv.ys' ; tail -15 off_step_equiv.log
