#!/bin/bash
set -euo pipefail
root="$PWD"
src="${A0_SYNTH_SOURCE:-src}"
work="${A0_SYNTH_WORK:-synth_work}"
census="${A0_SYNTH_CENSUS:-copies_census.json}"
docker run --rm -v "$root/$src":/src:ro -v "$root/$work":/work \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc \
  'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth'
docker run --rm -v "$root":/a0 \
  -e A0_ODB=/a0/$work/results/asap7/opentallas_qfd_tile_nk_rp2_romleaf_rr_asap7_ref_gate/base/1_synth.odb \
  -e A0_CENSUS=/a0/$census openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /a0/audit_odb.py
