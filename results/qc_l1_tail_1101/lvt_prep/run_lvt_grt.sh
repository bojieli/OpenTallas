#!/bin/bash
set -euo pipefail
mkdir -p run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base
exec docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work -e OT_GEOM_OUT=/work/lvt_place_geom.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/load_lvt_grt.tcl' > lvt_grt.log 2>&1
