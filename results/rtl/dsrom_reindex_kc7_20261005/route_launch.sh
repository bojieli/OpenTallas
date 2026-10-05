#!/bin/bash
set -u
source ~/.opentallas-env
cd /srv/opentallas/repos/russell-dsrom-reindex-kc7-fixed-20261005
ROOT=/srv/opentallas-scratch/codex/russell-dsrom-reindex-kc7-20261005
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="pass"; assert r["selection"]["OPT_KC7"]==1' "$ROOT/gate_r2/gather.json" || exit 1
D="$ROOT/route_r1"
if test -e "$D"; then echo 'REFUSE prior route directory'; exit 1; fi
mkdir -p "$D"
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited OT_ORFS_NUM_CORES=16
git rev-parse HEAD > "$D/source.txt"
git status --porcelain > "$D/dirty.txt"
test ! -s "$D/dirty.txt" || exit 1
S=rtl/experimental/dsrom_reindex_kc7_20261005
/srv/opentallas-scratch/admit.sh 40 -- /usr/bin/time -v python3 tools/run_abi3_physical.py --view asap7 --top ot_hdc_v41x_idx_kgctl_kc7_ctx --source "$S/ot_hdc_v41x_idx_kgctl_kc7_ctx.sv" --source "$S/ot_hdc_v41x_idx_kgather_kc7.sv" --param OPT_KC6=1 --param OPT_KC7=1 --clock-period-ns 0.833 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --stages pnr --false-path-io --hold-margin-ns 0.008 --max-transition-ns library --max-fanout 32 --die-area 0 0 310.164 310.164 --core-area 2.052 2.160 308.124 308.070 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --nickname-tag kc7 --keep-workdir "$D/work" --output "$D/physical.json" > "$D/route.log" 2>&1
r=$?
printf '%s\n' "$r" > "$D/route.rc"
if test "$r" != 0; then exit "$r"; fi
N=opentallas_ot_hdc_v41x_idx_kgctl_kc7_ctx_asap7_kc7
python3 tools/qwen_async_seq_incontext_physical.py sta --workdir "$D/work" --nickname "$N" --out "$D/sta.json" > "$D/sta.log" 2>&1
r=$?; printf '%s\n' "$r" > "$D/sta.rc"
if test "$r" != 0; then exit "$r"; fi
python3 tools/dsrom_reindex_close.py groups --workdir "$D/work" --nickname "$N" --block kgctl --out "$D/groups.json" > "$D/groups.log" 2>&1
r=$?; printf '%s\n' "$r" > "$D/groups.rc"
exit "$r"
