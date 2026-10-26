#!/usr/bin/env bash
# Freeze exact committed source on both EPYC NVMe roots, then one admitted job.
# Usage: bash tools/hbm_static/su_native_vm_launch.sh LOCAL_RECEIPT_DIR
set -euo pipefail
cd "$(dirname "$0")/../.."
lock=/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock
assert_owner(){ python3 - "$lock" <<'PYLOCK'
import datetime,json,sys
v=json.load(open(sys.argv[1]))
if v.get('owner')!='codex': raise SystemExit('STOP: coordinator lock is not codex')
if datetime.datetime.fromisoformat(v['until'])<=datetime.datetime.now(datetime.timezone.utc): raise SystemExit('STOP: codex coordinator lease expired')
PYLOCK
}
git diff --quiet
git diff --cached --quiet
pin=$(git rev-parse HEAD)
local_out=$(realpath -m "$1")
remote=/home/ubuntu/hbm-su-native-composed-1103-$pin
assert_owner; mkdir -p "$local_out"
assert_owner; git archive --format=tar.gz -o "$local_out/source.tar.gz" HEAD rtl tools/hbm_static tools/hdc_golden.py \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2
assert_owner; sha256sum "$local_out/source.tar.gz" > "$local_out/source.sha256"
for host in ot-epyc1tb ot-epyc4; do
 assert_owner; ssh -o BatchMode=yes "$host" "mkdir -p '$remote'"
 assert_owner; scp -q "$local_out/source.tar.gz" "$host:$remote/source.tar.gz"
 assert_owner; ssh -o BatchMode=yes "$host" "cd '$remote' && tar xzf source.tar.gz && sha256sum source.tar.gz" > "$local_out/stage_$host.log"
done
assert_owner
# Keep this process alive: its PID and ot-run output are the admission handle.
SU_NATIVE_TOP=tb_hbm_su_native_composed_top /home/ubuntu/bin/ot-run --mem 160 --threads 4 --disk 30 --dir "$remote" -- \
 env SU_NATIVE_TOP=tb_hbm_su_native_composed_top bash tools/hbm_static/su_native_vm_top_run.sh "$remote/run" \
 > "$local_out/ot_run.log" 2>&1
