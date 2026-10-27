#!/bin/bash
# QC-SU F4A MIF0 place recipe (plain ORFS make place).  QC-SU-F4E (RULING QC-SU-F4D (b)): rtl_lint is mandatory for
# every kit -- it runs first, inside the same image, and a FAIL / NOT RUN stops the kit before synthesis (FAIL_PREFLOOR).
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name qcsuk2-lint-$(basename $K)-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/rtl_lint.py /work' > "$K/rtl_lint_m0.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown $(id -u):$(id -g) /work/rtl_lint.json /work/rtl_lint.log /work/rtl_lint.ys >/dev/null 2>&1 || true
if [ $rc != 0 ]; then echo "FAIL_PREFLOOR rtl_lint (FAIL or NOT RUN), see rtl_lint.json" | tee -a "$K/FAIL_PREFLOOR"; exit 8; fi
rc=0; docker run --rm --name qcsuk2-$(basename $K)-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' > "$K/place_m0.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
exit $rc
