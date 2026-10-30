#!/bin/bash
set -e
K=/srv/opentallas-scratch2/claude/codex-head-collect-1030/hb4_lockfix
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/hb4_clock_reference
python3 - "$R" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);x=json.loads((p/'clock_recipe.json').read_text());x['cells'][0]['xy_dbu'][0]+=54;(p/'wrong_site_control.json').write_text(json.dumps(x))
PY
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-clock-ref-import-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work:ro -v "$R":/out -v /srv/opentallas-scratch2/claude/codex-head-collect-1030/clock_recipe.py:/clock_recipe.py:ro openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
ACTION=import INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb RECIPE=/out/clock_recipe.json OUTPUT_ODB=/out/old_reference_v2_frozen.odb REPORT=/out/import_old_reference_v2_PASS.json openroad -python -exit /clock_recipe.py > /out/import_old_reference.log 2>&1
ACTION=verify INPUT_ODB=/out/old_reference_v2_frozen.odb RECIPE=/out/clock_recipe.json REPORT=/out/verify_old_reference_v2_PASS.json openroad -python -exit /clock_recipe.py > /out/verify_old_reference.log 2>&1
set +e
ACTION=import INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/4_cts.odb RECIPE=/out/wrong_site_control.json OUTPUT_ODB=/out/MUST_NOT_EXIST.odb REPORT=/out/wrong_site_control_v2_EXPECTED_FAIL.json openroad -python -exit /clock_recipe.py > /out/wrong_site_control.log 2>&1
rc=$?; test $rc != 0 || exit 42; test ! -f /out/MUST_NOT_EXIST.odb || exit 43; cat /out/import_old_reference_v2_PASS.json /out/verify_old_reference_v2_PASS.json /out/wrong_site_control_v2_EXPECTED_FAIL.json'
