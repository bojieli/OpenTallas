#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:?output directory required}")
mkdir -p "$OUT"
cd "$ROOT"
D=rtl/hbm_accel/generic/vm/static
for mutant in 0 1 2 3 4; do
    iverilog -g2012 -s tb_vms_hub_static -Ptb_vms_hub_static.MUT="$mutant" \
        -o "$OUT/m$mutant.vvp" "$D/ot_vms_hub_static.sv" "$D/tb_vms_hub_static.sv" \
        >"$OUT/m$mutant.build.log" 2>&1
    set +e
    vvp "$OUT/m$mutant.vvp" >"$OUT/m$mutant.log" 2>&1
    rc=$?
    set -e
    if [[ $mutant == 0 ]]; then
        [[ $rc == 0 ]]
        grep '^VMS_HUB_STATIC_BENCH PASS' "$OUT/m0.log"
    else
        [[ $rc != 0 ]]
        grep '^FATAL:.*mismatch' "$OUT/m$mutant.log"
    fi
    rm "$OUT/m$mutant.vvp"
done
iverilog -g2012 -s tb_vms_hub_static_nc0 -o "$OUT/nc0.vvp" \
    "$D/ot_vms_hub_static.sv" "$D/tb_vms_hub_static.sv" >"$OUT/nc0.build.log" 2>&1
vvp "$OUT/nc0.vvp" >"$OUT/nc0.log" 2>&1
grep '^VMS_HUB_STATIC_NC0 PASS' "$OUT/nc0.log"
rm "$OUT/nc0.vvp"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --lint-only --timing --top-module tb_vms_hub_static \
    "$D/ot_vms_hub_static.sv" "$D/tb_vms_hub_static.sv" >"$OUT/lint.log" 2>&1
python3 - "$ROOT" "$OUT" <<'PY'
import hashlib,json,pathlib,subprocess,sys
root,out=map(pathlib.Path,sys.argv[1:])
files=['rtl/hbm_accel/generic/vm/static/'+x for x in ['ot_vms_hub_static.sv','tb_vms_hub_static.sv','run_hub_static.sh']]
receipt={'scope':'static packet hub local service and explicit remote packet ports; no physical closure claim','sources_sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},'baseline':'PASS','replay_only_NC0':'PASS','mutants':{'1_wrong_bank_decode':'KILLED','2_wrong_tag':'KILLED','3_ignore_compiler_selection':'KILLED','4_wait_for_missing_ack':'KILLED'},'local_throughput':{'responses':2000,'issue_cycles':1000,'packets_per_cycle':2,'roundtrip_edges':10},'mechanisms':['client-selected bank routing','original client tag echo','physical ring CW/CCW destination mask','mirror visibility waits four acknowledgements','remote read response routing','unscheduled request fault','slot overwrite fault','compiler response calendar','missing ack faults on calendar edge','late ack cannot replay'],'iverilog_version':subprocess.check_output(['iverilog','-V'],stderr=subprocess.STDOUT,text=True).splitlines()[0]}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
