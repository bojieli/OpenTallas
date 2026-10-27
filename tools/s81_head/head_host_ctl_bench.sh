#!/usr/bin/env bash
# Minimum two-core integration: real peer safe8 lanes -> HBC authority ->
# HOST276 -> ctl config/ordinary stage forwarding. TEST boot profile only.
# Invoke through ot-run in a clean pinned worktree or staged source closure.
set -euo pipefail
ROOT=${OT_SOURCE_ROOT:-$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)}
O=$(realpath -m "${1:?fresh output directory}")
if [ -e "$O" ];then echo "refusing existing output $O" >&2;exit 2;fi
mkdir -p "$O";cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version >"$O/verilator_version.txt"
python3 tools/s81_dv/hostctx_1021/gen_vectors.py "$O/vec" >"$O/gen.log"
python3 - "$O" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,'tools/s81_head')
from head_control_plan_delta import CTL_SOURCES
from head_host_plan_delta import SOURCES
ps=list(dict.fromkeys(CTL_SOURCES+SOURCES+['rtl/dsrom_sys/s81_head/test/tb_s81hd_host_ctl_boot.sv']))
missing=[p for p in ps if not Path(p).is_file()]
if missing:raise SystemExit('source closure missing: '+str(missing))
(Path(sys.argv[1])/'sources.f').write_text('\n'.join(ps)+'\n')
PY
for m in 0 3;do
 "$V" --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_s81hd_host_ctl_boot -GMUT="$m" \
 +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF -Mdir "$O/obj$m" -f "$O/sources.f" --build-jobs "${J:-4}" >"$O/build$m.log" 2>&1
 set +e
 "$O/obj$m/Vtb_s81hd_host_ctl_boot" +VEC="$O/vec" >"$O/run$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep 'HEAD_HOST_CTL_BOOT PASS' "$O/run$m.log"
 else test "$rc" != 0;grep 'ordinary HFWD full512 payload mismatch' "$O/run$m.log";fi
done
echo HEAD_HOST_CTL_GATE_PASS
