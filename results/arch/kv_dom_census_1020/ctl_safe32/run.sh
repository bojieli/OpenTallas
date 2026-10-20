#!/bin/bash
set -euo pipefail
D=$PWD
G=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu6c-20261019-230301
N=$G/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_ctl_asap7_ref_gate/base/1_2_yosys.v
sha=$(sha256sum "$N" | cut -d' ' -f1)
printf '%s\n' "$sha" > original.sha256
python3 "$D/kv_grp_safe5.py" --netlist "$N" --parser "$G/src/tools/textbook_lint.py" --sha256 "$sha" --top qkd_kvs_ctl_s32 --out "$D/qkd_kvs_ctl_s32.sv"
image=$(cat /srv/opentallas-scratch/claude/ref_gate/codex_s5_1020/image_id.txt)
printf '%s\n' "$image" > image_id.txt
docker run --rm --network none -v "$D:/work" -v "$G/src:/src:ro" "$image" python3 /work/resynth.py
python3 "$D/kv_grp_safe5_certificate.py" --original "$N" --mapped "$D/qkd_kvs_ctl_s32.mapped.v" --parser "$G/src/tools/textbook_lint.py" --record "$D/qkd_kvs_ctl_s32.json" --out "$D/qkd_kvs_ctl_s32.certificate.json"
echo CTL_SAFE32_GENERATE_RESYNTH_CERTIFICATE_DONE
