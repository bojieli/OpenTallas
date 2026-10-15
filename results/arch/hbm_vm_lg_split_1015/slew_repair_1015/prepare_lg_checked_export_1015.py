from pathlib import Path
for profile,tt,ff in [('su10',269.9,29.9),('sfu14',251.5,23.17)]:
 b=Path(f'/srv/opentallas-scratch/codex/lg-{profile}-slew-repair-1015');src=f'/srv/opentallas-scratch/codex/lg-{profile}-native-route-1015/src';top=f'hfd_vm_lg_{profile}'
 s='''#!/bin/bash
set -euo pipefail
base=BASE
src=SOURCE
cd "$src"
python3 tools/tt_views/view_export.py --orfs-dir "$base/work" --name TOP --out "$base/views_checked/TOP" --interface-sdc "$src/physical/ref_tile/vm_lg_bank_PROFILE_static_1015/signoff.sdc" --corners ss,ff,tt --post-sdc "$src/physical/ref_tile/vm_lg_bank_PROFILE_static_1015/signoff.sdc" --post-sdc "$src/physical/common_flow/io_ref_routed.sdc" --expect-tt EXPECTTT --expect-ff EXPECTFF --require-check --signal-max-layer M5 --pg-max-layer M5 --signal-audit-tcl "$src/tools/ref_tile/signal_layer_audit.tcl" > "$base/export_checked.log" 2>&1
cp "$base/views_checked/TOP/TOP.lef" "$base/views_checked/TOP/TOP.raw.lef"
python3 tools/hier_contract/abstract_pin_stub.py "$base/views_checked/TOP/TOP.lef" "$base/views_checked/TOP/TOP.lef" > "$base/lef_postprocess.log"
python3 tools/hier_contract/child_lint.py "$base/views_checked/TOP/TOP.lef" --libs "$base/views_checked/TOP" --cap M5 --strict-pockets --json > "$base/strict_child_lint.json"
cp "$base/ck_routed.json" "$base/views_checked/TOP/insertion.json"
'''.replace('BASE',str(b)).replace('SOURCE',src).replace('PROFILE',profile).replace('TOP',top).replace('EXPECTTT',str(tt)).replace('EXPECTFF',str(ff))
 (b/'check_export.sh').write_text(s)
