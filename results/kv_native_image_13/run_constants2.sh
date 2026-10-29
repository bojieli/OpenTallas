#!/bin/bash
set -u
# Inputs (env): KV_BIND=KV strict bind dir, QC_BIND=QC bind dir, QC_SRC=QC source tree, OUT=output dir.
W=${W:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
O=${OUT:?set OUT}
K=${KV_BIND:?set KV_BIND}
Q=${QC_BIND:?set QC_BIND}
QS=${QC_SRC:-$W}
mkdir -p "$O"
cd "$W"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound "$K" --peer "$Q" --src-root "$W" --out-json "$O/kv_constants2.json" --out-sv "$O/kv_constants2.svh" > "$O/kv_constants2.log" 2>&1
echo "KV_CONSTANTS_RC=$?"
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound "$Q" --peer "$K" --src-root "$QS" --out-json "$O/qc_constants2.json" --out-sv "$O/qc_constants2.svh" > "$O/qc_constants2.log" 2>&1
echo "QC_CONSTANTS_RC=$?"
python3 physical/die_plan/qwen_kvsys/boot_v36/kst.py "$K/bus_groups.json" > "$O/kst.txt"
echo "KST_RC=$?"
python3 - "$K" "$O" <<'PY'
import json,re,sys
from pathlib import Path
K,O=map(Path,sys.argv[1:]);j=json.load(open(K/'bind_sinks.json'))
cs={k:v for k,v in j.items() if re.fullmatch(r'ectl_(EN|ES|WN|WS)_\d.cfg\[[0-4]\]',k)}
assert len(cs)==160,len(cs)
(O/'cfg_sinks.json').write_text(json.dumps(cs,indent=1)+'\n')
PY
python3 tools/qwen_kv_die/native_die_cfg_contract.py \
 rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_ctl_nc32.sv \
 rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_dcfg.sv \
 rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_misc.sv \
 rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv \
 rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv \
 rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_land.sv \
 "$O/cfg_sinks.json" --out "$O/native_contract.json" > "$O/native_contract.log" 2>&1
echo "NATIVE_CONTRACT_RC=$?"
H=$W/physical/die_plan/qwen_kvsys/boot_v36
AS=$O/asbuilt_rtl6;mkdir -p "$AS"
cp "$H/asbuilt_rtl6/kv_flags.env" "$H/asbuilt_rtl6/SOURCE_COMMIT" "$AS/"
for f in "$H"/asbuilt_rtl6/*.json.gz;do zcat "$f" > "$AS/$(basename "${f%.gz}")";done
set -a;. "$AS/kv_flags.env";set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1 PYTHONDONTWRITEBYTECODE=1
python3 "$H/kv_boot_v36.py" prep --rs "$AS/relay_stages.json" --model "$AS/static_model.json" --groups "$K/bus_groups.json" --out "$O/prep_native2" > "$O/prep_native2.log" 2>&1
echo "NATIVE_PREP_RC=$?"
