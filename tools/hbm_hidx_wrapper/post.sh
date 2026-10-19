#!/bin/bash
set -euo pipefail
# Correct initial draft max/min input-arrival inconsistency; no physical STA ran.
if test -f out/coupon.sdc;then cp out/coupon.sdc out/coupon_initial_draft_NOT_QUALIFIED.sdc;fi
python3 tools/hbm_hidx_wrapper/constraints.py
python3 tools/hbm_hidx_wrapper/geometry.py
python3 tools/hbm_hidx_wrapper/loaded_caps.py
python3 tools/hbm_hidx_wrapper/pg_model.py
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for corner in TT FF;do
 docker run --rm --network none -e CORNER="$corner" -v "$PWD:/work" -w /work "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit tools/hbm_hidx_wrapper/source_sta.tcl >out/source_sta_$corner.log 2>&1
 if grep -Eq '\[ERROR|^Error:' out/source_sta_$corner.log;then exit 1;fi
done
sha256sum tools/hbm_hidx_wrapper/* canonical/* out/*.json out/*.log out/*.v out/*.lib out/*.sdc out/*.tcl >out/SHA256SUMS_FINAL
