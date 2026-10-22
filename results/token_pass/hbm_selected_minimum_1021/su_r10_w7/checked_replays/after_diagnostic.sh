#!/bin/bash
set -euo pipefail
localroot=/home/ubuntu/scratch/codex-selected-su-minimum-1021
buildroot=/srv/opentallas-scratch/claude/codex-selected-su-minimum-1021
checkroot=/srv/opentallas-scratch/claude/codex-selected-su-checks-1021
while ! grep -q 'ot-run: RAN on .*exit ' "$localroot/client.log"; do sleep 10; done
if ! grep -q 'ot-run: RAN on .*exit 0' "$localroot/client.log";then echo ORIGINAL_BUILD_OR_DIAGNOSTIC_FAILED;exit 2;fi
ssh ot-epyc9 "test -x $buildroot/out/obj/Vtb_hbm_slice && mkdir -p $checkroot && cp $buildroot/out/obj/Vtb_hbm_slice $checkroot/Vtb_hbm_slice && cd $checkroot && sha256sum Vtb_hbm_slice > binary.sha256"
rsync -a "$localroot/checks_render/replay/" ot-epyc9:"$checkroot/replay/"
rsync -a "$localroot/half_render/replay/" ot-epyc9:"$checkroot/replay/"
rsync -a "$localroot/rank1_half_render/replay/" ot-epyc9:"$checkroot/replay/"
scp -q "$localroot/checks_run.sh" ot-epyc9:"$checkroot/run.sh"
/home/ubuntu/bin/ot-run --mem 8 --threads 1 --disk 2 --dir "$checkroot" -- bash run.sh > "$localroot/checks_client.log" 2>&1
