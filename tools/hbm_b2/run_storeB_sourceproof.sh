#!/bin/bash
# Run only in one normally admitted12GB/2T ot-run scope. Never enters PLACE/P&R.
set -euo pipefail
ot_store_repo=$(cd "$1" && pwd)
ot_store_out=$2
mkdir -p "$ot_store_out"
python3 "$ot_store_repo/tools/hbm_b2/storeA_native_master_preflight.py" --repo "$ot_store_repo" --selected-abi "$ot_store_repo/results/hbm_storeB_native_capsule_0136/selected_native_macro_ABIs.json" --out "$ot_store_out/native_master_abi.json"
python3 "$ot_store_repo/tools/hbm_b2/storeB_current_native_kit.py" --repo "$ot_store_repo" --profile-out "$ot_store_out/profile.json" --out "$ot_store_out/kits" --tag source_eq --trial > "$ot_store_out/GEN.log" 2>&1
ot_store_kit=$(python3 - "$ot_store_out/kits" <<'PY'
import sys
from pathlib import Path
ks=[p.parent for p in Path(sys.argv[1]).glob('*/config.mk')]
if len(ks)!=1:raise SystemExit('expected one fresh native kit')
k=ks[0]
if (k/'reset_contract.json').exists():raise SystemExit('new selected StoreB must not inherit historical reset receipt')
print(k)
PY
)
export OT_LEC_ASYNC=0
export OT_LEC_RESET_CYCLES=4
bash "$ot_store_repo/physical/die_plan/hbm_arch_cores/run_kit_hbm.sh" "$ot_store_kit" synth 12 2
python3 - "$ot_store_kit" "$ot_store_out" <<'PY'
import json,sys
from pathlib import Path
k,out=map(Path,sys.argv[1:]);p=k/'lec/lec.json'
if not p.is_file():raise SystemExit('official native mapped LEC result missing')
a=json.loads(p.read_text());r=dict(status='PASS_CONDITIONAL_NATIVE_SOURCE_EQ'if a.get('verdict')=='EQUIVALENT'else'FAIL',official_lec=a.get('verdict'),official_receipt=str(p),formal_input_reset_assert_edges=4,physical_parent_reset_phase='HELD rst_n_t22→native3edge→store; no generic4/64receipt transfer',SOURCE13_mutated=False,PNR_dispatched=False)
(out/'sourceproof_result.json').write_text(json.dumps(r,indent=2)+'\n')
if a.get('verdict')!='EQUIVALENT':raise SystemExit('official native equivalence did not fully prove')
print(json.dumps(r))
PY
