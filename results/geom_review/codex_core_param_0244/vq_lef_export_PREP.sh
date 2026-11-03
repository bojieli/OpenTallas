#!/bin/bash
# PREP ONLY. No controller submitted. ROOT must select this exact AQ_XMEM2 source and authorize the view repair.
# Existing source/profile/context joins remain HOLD; this exports geometry only, never timing/count/proof credit.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/s81ck5/kits/ot_s81sl_vq_rt6e_hx3
O=/srv/opentallas-scratch2/claude/codex-vq-native-view-PREP
B=$K/run/results/asap7/kl_ot_s81sl_vq_rt6/base
mkdir -p "$O"
test ! -e "$O/ot_s81sl_vq.raw.lef"
sha256sum "$B/6_final.odb" > "$O/immutable_native.sha256"
cat > "$O/export.tcl" <<'TCL'
read_db /work/run/results/asap7/kl_ot_s81sl_vq_rt6/base/6_final.odb
write_abstract_lef /out/ot_s81sl_vq.raw.lef
exit
TCL
docker run --rm --network none --memory=4g --memory-swap=4g --cpus=2 -v "$K":/work:ro -v "$O":/out openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 2 -exit /out/export.tcl > "$O/export.log" 2>&1
sha256sum --check "$O/immutable_native.sha256" > "$O/immutable_PASS.txt"
# Apply source-pinned tools/hier_contract/abstract_pin_stub.py and strict geometry child_lint under current normal
# TT/FF release convention; preserve raw LEF and failed outputs. Do not silently mark old incomplete view complete.
