#!/bin/bash
# Final coherent bind intake only. Does not mutate either source tree.
set -euo pipefail
ROOT=$(realpath "${1:?source root}"); BIND=$(realpath "${2:?final KV bind}"); CST=${3:?final QC six seam stages}; OUT=$(realpath -m "${4:?new output directory}")
[ ! -e "$OUT" ] || { echo "refuse overwrite $OUT";exit 2; }
python3 -I - "$BIND" "$CST" <<'PY'
from pathlib import Path
import json,sys
b=Path(sys.argv[1]);r=json.loads((b/'bind_report.json').read_text());e=r['errors'];assert r['n_errors']==len(e)
allowed='PARAM_REGEN kv_pv_col_regen.py: pair image pair_image_txdp.json is stale for this bind:'
assert all(x.startswith(allowed) for x in e),'non-pair-image bind error: compile deferred'
cs=list(map(int,sys.argv[2].split(',')));assert len(cs)==6 and all(0<=x<256 for x in cs)
assert (b/'bus_groups.json').is_file() or (b/'bus_groups.json.gz').is_file()
PY
mkdir -p "$OUT"
export CST OT_KV_HEAD_PREP_EDGES=21 OT_KV_COMPUTE_RECORD_TXD=18 OT_KV_CAL_OFS=-2
# KST/HRT/EMBRT are derived by run_mu833.sh from the selected bind, never reused.
unset KST HRT EMBRT OT_KV_ATTN_SERVICE_PAD NO_CONTRACT
bash "$ROOT/physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh" "$BIND" "$OUT"
python3 -I "$(dirname "$0")/pair_extract1116.py" "$ROOT" "$BIND" "$OUT"
python3 -I - "$ROOT" "$BIND" "$OUT" <<'PY'
from pathlib import Path
import hashlib,json,sys
r,b,o=map(Path,sys.argv[1:]);sys.path.insert(0,str(r/'tools/mem_compiler'));import kv_dcal_profile as P
image=o/'img_bnd/d2d_cal_image.svh';pr=P.extract_sv(image.read_text());rec=P.personalise(pr,o/'dcal_profile_delta',instance='kv_dcal')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=dict(status='COMPILED_BOOTSTRAP_REBIND_AND_PAIR_RUNTIME_PENDING',bind=str(b),image_sha256=sha(image),profile=pr,
 files=dict(QC_include='rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_qc_pair.svh',
 source_image=str(image),KV_profile_generated=str(o/'dcal_profile_delta'),KV_profile_target='physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/content',
 pair_transport_record='physical/die_plan/qwen_kvsys/bind/kvbind1025/pair_image_txdp.json',source_record=str(o/'pair_image_txdp.generated.json'),
 KV_native_programmes=str(o/'cmp_mu833/target*.hex'),KV_boot_bundle=str(o/'cmp_mu833/boot_bundle.json')),
 required_next='Install data delta into new QC and KV source cohorts together. Rebind both; verify TXDP and all compiled/profile words. Final literal source/runtime pair gate still required.',
 limits='No source file is modified by this script. A sole stale-pair record bind error is bootstrap input only, never a qualified bind. Existing old image not qualified by this compile.')
(o/'source_delta.json').write_text(json.dumps(inputs,indent=2)+'\n');print(json.dumps(inputs))
PY
