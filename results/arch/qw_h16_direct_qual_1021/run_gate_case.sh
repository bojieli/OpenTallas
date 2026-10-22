#!/bin/bash
# usage: run_gate_case.sh WORK img0|imgh [BMUT]
# Every fixture is in tracked frozen_baseline.tgz. No git/network/remote reads.
set -euo pipefail
qual=$(dirname "$(readlink -f "$0")")
src=$(pwd)
work=$(realpath -m "$1")
image=$2
case "$image" in img0|imgh) ;; *) exit 2;; esac
mkdir -p "$work"
(
 flock 9
 if [ ! -f "$work/PREPARED" ]; then
  tar xzf "$qual/frozen_baseline.tgz" -C "$work"
  mkdir -p "$work/candidate" "$work/qualification"
  cp "$src/results/rtl/qw_head_safe32_1020/h16z/net/native32_1r_param.v" "$work/candidate/"
  cp "$src/results/rtl/qw_head_safe32_1020/h16z/net/native32_helpers.sv" "$work/candidate/"
  cp "$qual/prepare_bench.py" "$qual/baseline_manifest.json" "$work/qualification/"
  cd "$work"
  python3 - <<'PY'
import hashlib,json
from pathlib import Path
m=json.loads(Path('qualification/baseline_manifest.json').read_text())
for f,sha in m['files'].items():
    assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==sha,f
assert hashlib.sha256(Path('candidate/native32_1r_param.v').read_bytes()).hexdigest()=='44d54f850a0630849746de3cb907e132ec579b6155fbb10ef21fd5e20c44a9d7'
assert hashlib.sha256(Path('candidate/native32_helpers.sv').read_bytes()).hexdigest()=='1e021ff33742ef24529373bfab456eeb95f90c693f597963cd8c2f368c3bec88'
PY
  python3 qualification/prepare_bench.py --native-dir candidate
  touch PREPARED
 fi
) 9>"$work/prepare.lock"
cd "$work"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
args=()
if [ -n "${3:-}" ]; then args+=(--bmut "$3"); fi
python3 rtl/test/qwen_dv/tt_ctlm_prog_h16z_qualification.py --decode 3 --hard 1 --segcal 1 --work "runs/$image" --img "results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/$image" "${args[@]}"
