#!/usr/bin/env bash
# Current generated hd_tile wrapper, released-checkpoint data, independent
# boundary-delay miter and incorrect ROW0 negative control. Run via ot-run.
set -euo pipefail
TASK_ROOT=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
cd "$TASK_ROOT"
O=${1:?fresh repo-relative output directory}
case "$O" in /*) echo 'output must be repo-relative' >&2;exit 2;;esac
if [ -e "$O" ];then echo 'refusing existing output' >&2;exit 2;fi
mkdir -p "$O"
python3 - <<'PY'
import json,pathlib,subprocess
r=pathlib.Path.cwd();p=json.loads((r/'physical/die_plan/s81_head/die_plan.json').read_text())
src={s for t in p['partition_types'].values() for s in t.get('sources',[])}
src.update(l.split('#')[0].strip() for l in (r/'tools/s81_head/head_portbind_extra.f').read_text().splitlines() if l.split('#')[0].strip())
pre='results/rtl/s81_head_tile_1021/img/'
src.update(s for s in subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD',pre],text=True).splitlines() if pathlib.Path(s).name.startswith(('h','x')))
for s in sorted(src):
 q=r/s
 if not q.exists():q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(subprocess.check_output(['git','show','HEAD:'+s]))
PY
python3 tools/s81_head/head_source_delta.py physical/die_plan/s81_head/die_plan.json "$O/die_plan.json" --report "$O/source_delta.json" > "$O/source_delta.log" 2>&1
python3 tools/s81_head/head_die_portbind.py "$O/die_plan.json" --out "$O/bind" > "$O/bind.log" 2>&1
python3 tools/s81_head/head_token_sources.py "$O/die_plan.json" "$O/bind/portbind.f" "$O/native" > "$O/native.log" 2>&1
python3 tools/s81_head/hd_reskew_images.py results/rtl/s81_head_tile_1021/img "$O/img_sk11" --from 8 --to 11 > "$O/images.log" 2>&1
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_head_partition_token -f "$O/native/native.f" rtl/dsrom_sys/s81_head/test/tb_head_partition_token.sv --Mdir "$O/obj" --build-jobs "${J:-16}" -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > "$O/build.log" 2>&1
"$O/obj/Vtb_head_partition_token" +DIR="$O/img_sk11" +OT_ROM_DIR="$O/img_sk11" > "$O/positive.log" 2>&1
grep 'HEAD_PARTITION_TOKEN PASS' "$O/positive.log"
set +e
"$O/obj/Vtb_head_partition_token" +DIR="$O/img_sk11" +OT_ROM_DIR="$O/img_sk11" +MUT_ROW=1 > "$O/mut_row.log" 2>&1
rc=$?
set -e
test "$rc" != 0
grep 'HEAD_PARTITION lockstep mismatch' "$O/mut_row.log"
echo HEAD_PARTITION_GATE_PASS
