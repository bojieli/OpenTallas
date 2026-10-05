#!/bin/bash
set -u
source ~/.opentallas-env
VARIANT=$1
WT=/srv/opentallas/repos/russell-reindex-parallel-$VARIANT-20261005
D=/srv/opentallas-scratch/codex/russell-reindex-parallel-20261005/$VARIANT
cd "$WT"
mkdir -p "$D"
git rev-parse HEAD > "$D/source.txt"
git status --porcelain > "$D/dirty.txt"
test ! -s "$D/dirty.txt" || exit 1
export OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited OT_ORFS_NUM_CORES=16 NUM_CORES=16
if test "$VARIANT" = split2; then
 /srv/opentallas-scratch/admit.sh 8 -- /usr/bin/time -v python3 tools/dsrom_reindex_kc7_split_gate.py --out "$D/gate" --gold /mnt/epyc1-scratch/claude/dsrom-reindex/gold > "$D/gate.log" 2>&1
 r=$?; echo "$r" > "$D/gate.rc"; test "$r" = 0 || exit "$r"
 S=rtl/experimental/dsrom_reindex_kc7_split_20261005
 TOP=ot_hdc_v41x_idx_kgctl_kc7_split_ctx
 SOURCES=(--source "$S/ot_hdc_v41x_idx_kgctl_kc7_split_ctx.sv" --source "$S/ot_hdc_v41x_idx_kgather_kc7_split.sv")
 PARAMS=(--param OPT_KC6=1 --param OPT_KC7=1 --param OPT_SPLIT_CMP=1)
 FLOOR=(--die-area 0 0 310.164 310.164 --core-area 2.052 2.160 308.124 308.070)
else
 S=rtl/experimental/dsrom_reindex_kc7_20261005
 TOP=ot_hdc_v41x_idx_kgctl_kc7_ctx
 SOURCES=(--source "$S/ot_hdc_v41x_idx_kgctl_kc7_ctx.sv" --source "$S/ot_hdc_v41x_idx_kgather_kc7.sv")
 PARAMS=(--param OPT_KC6=1 --param OPT_KC7=1)
 U=${VARIANT#u}
 FLOOR=(--core-utilization "$U")
 python3 -c 'import hashlib,json,sys; from pathlib import Path; r=json.load(open("results/rtl/dsrom_reindex_kc7_20261005/gate_r2_PASS/gather.json")); assert r["status"]=="pass"; p=sys.argv[1]; assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==r["source_sha256"][p]' "$S/ot_hdc_v41x_idx_kgather_kc7.sv" || exit 1
fi
/srv/opentallas-scratch/admit.sh 40 -- /usr/bin/time -v python3 tools/run_abi3_physical.py --view asap7 --top "$TOP" "${SOURCES[@]}" "${PARAMS[@]}" --clock-period-ns 0.833 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --stages pnr --false-path-io --hold-margin-ns 0.008 --max-transition-ns library --max-fanout 32 "${FLOOR[@]}" --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --nickname-tag "kc7_$VARIANT" --keep-workdir "$D/work" --output "$D/physical.json" > "$D/route.log" 2>&1
r=$?; echo "$r" > "$D/route.rc"; test "$r" = 0 || exit "$r"
N="opentallas_${TOP}_asap7_kc7_$VARIANT"
python3 tools/qwen_async_seq_incontext_physical.py sta --workdir "$D/work" --nickname "$N" --out "$D/sta.json" > "$D/sta.log" 2>&1
r=$?; echo "$r" > "$D/sta.rc"; test "$r" = 0 || exit "$r"
python3 tools/dsrom_reindex_close.py groups --workdir "$D/work" --nickname "$N" --block kgctl --out "$D/groups.json" > "$D/groups.log" 2>&1
r=$?; echo "$r" > "$D/groups.rc"; exit "$r"
