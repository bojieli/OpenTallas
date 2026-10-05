#!/bin/bash
set -u
source ~/.opentallas-env
cd /srv/opentallas/repos/russell-dsrom-reindex-kc8-20261005
ROOT=/srv/opentallas-scratch/codex/russell-dsrom-reindex-kc8-20261005
python3 - <<'CHECK'
import json,hashlib
from pathlib import Path
r=json.loads(Path('results/rtl/dsrom_reindex_kc8_20261005/gate_PASS/gather.json').read_text())
assert r['status']=='pass' and len(r['runs'])==20
f='rtl/experimental/dsrom_reindex_kc7_20261005/ot_hdc_v41x_idx_kgather_kc7.sv'
assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==r['source_sha256'][f]
m=json.loads(Path('results/uarch/dsrom_reindex_kc8_20261005/model.json').read_text())
assert m['slot']['remaining_mapping_CTS_repair_budget_um2']>0
CHECK
if test "$?" != 0; then exit 1; fi
D="$ROOT/route_r1"
if test -e "$D"; then echo 'REFUSE prior route directory'; exit 1; fi
mkdir -p "$D"
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited OT_ORFS_NUM_CORES=16 NUM_CORES=16
git rev-parse HEAD > "$D/source.txt"
git status --porcelain > "$D/dirty.txt"
test ! -s "$D/dirty.txt" || exit 1
S=rtl/experimental/dsrom_reindex_kc7_20261005
/srv/opentallas-scratch/admit.sh 40 -- /usr/bin/time -v python3 tools/run_abi3_physical.py --view asap7 --top ot_hdc_v41x_idx_kgctl_kc7_ctx --source "$S/ot_hdc_v41x_idx_kgctl_kc7_ctx.sv" --source "$S/ot_hdc_v41x_idx_kgather_kc7.sv" --param OPT_KC6=1 --param OPT_KC7=1 --param OPT_KC8=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --stages pnr --false-path-io --hold-margin-ns 0.008 --max-transition-ns library --slew-margin-percent 20 --max-fanout 32 --die-area 0 0 310.164 310.164 --core-area 2.052 2.160 308.124 308.070 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --nickname-tag kc8 --keep-workdir "$D/work" --output "$D/physical.json" > "$D/route.log" 2>&1
r=$?
printf '%s\n' "$r" > "$D/route.rc"
if test "$r" != 0; then exit "$r"; fi
N=opentallas_ot_hdc_v41x_idx_kgctl_kc7_ctx_asap7_kc8
python3 tools/qwen_async_seq_incontext_physical.py sta --workdir "$D/work" --nickname "$N" --out "$D/sta.json" > "$D/sta.log" 2>&1
r=$?; printf '%s\n' "$r" > "$D/sta.rc"
if test "$r" != 0; then exit "$r"; fi
python3 tools/dsrom_reindex_close.py groups --workdir "$D/work" --nickname "$N" --block kgctl --out "$D/groups.json" > "$D/groups.log" 2>&1
r=$?; printf '%s\n' "$r" > "$D/groups.rc"
exit "$r"
