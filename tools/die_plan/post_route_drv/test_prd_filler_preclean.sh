#!/bin/bash
# Run inside the OpenROAD image, under normal ot-run admission.
# Args: helper directory, immutable routed ODB with PG-connected filler, fresh output dir.
set -eu
T=$1; S=$2; O=$3
mkdir -p "$O"
B="$O/negative_filler_signal.odb"
openroad -exit -python "$T/make_filler_signal_mutant.py" "$S" "$B" "$O/mutation.json" > "$O/make_mutant.log" 2>&1
set +e
openroad -exit -python "$T/prd_filler_preclean.py" "$B" "$O/refused.odb" "$O/refused.json" > "$O/nonpg_refusal.log" 2>&1
PG_RC=$?
openroad -exit -python "$T/prd_filler_preclean.py" "$S" "$O/alias" "$O/alias" > "$O/alias_refusal.log" 2>&1
ALIAS_RC=$?
set -e
test "$PG_RC" -ne 0
test "$ALIAS_RC" -ne 0
grep -q 'refuse filler connected to non-PG net' "$O/nonpg_refusal.log"
grep -q 'refuse input/output alias or existing output' "$O/alias_refusal.log"
test ! -e "$O/refused.odb"
test ! -e "$O/refused.json"
test ! -e "$O/alias"
python3 - "$O" "$PG_RC" "$ALIAS_RC" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);x={'status':'NEGATIVE_CONTROLS_PASS','nonpg_filler_rc':int(sys.argv[2]),'output_manifest_alias_rc':int(sys.argv[3]),'unsafe_outputs_absent':True,'mutation':json.loads((p/'mutation.json').read_text()),'reconstructible_mutant_bytes':(p/'negative_filler_signal.odb').stat().st_size}
(p/'negative_controls.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
PY
rm -- "$B"
