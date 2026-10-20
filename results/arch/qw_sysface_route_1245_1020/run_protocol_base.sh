#!/bin/bash
# Functional bare-core adapter, using actual production protocol fixture.
# SRC contains the source-pinned snapshot; INTERMEDIATE contains the parent's
# private new core and actual fixed calendar wrappers. Aliases are test-only.
set -eu
OUT=$1; INTERMEDIATE=$2; M=${3:-0}
R=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
INTERMEDIATE=$(readlink -f "$INTERMEDIATE")
export D2D_MU=1
python3 - "$R" "$OUT" <<'PY'
import subprocess,sys
from pathlib import Path
r,o=map(Path,sys.argv[1:]);p=r/'rtl/test/qwen_split/run_sys_face_bench.sh'
s=p.read_text();assert s.count('\nrc=0\n')==1
prefix=s.split('\nrc=0\n')[0]
prefix+='\nprintf "%s\\n" "$F" > "$OUT/original_sources.txt"\n'
subprocess.run(['bash','-c',prefix,str(p),str(o)],check=True)
PY
V=${VERILATOR:-verilator}
"$V" --version > "$OUT/tool.txt"
grep -q 'Verilator 5.050' "$OUT/tool.txt" || { cat "$OUT/tool.txt";exit 2; }
test -s "$INTERMEDIATE/tb_qfd_sys_face_n32.sv"
test -s "$INTERMEDIATE/qfd_sys_face_core_n32.sv"
test -s "$INTERMEDIATE/qfd_syscal_n32.sv"
mapfile -t FILES < <(tr '[:space:]' '\n' < "$OUT/original_sources.txt" | sed '/^$/d')
S=()
for F in "${FILES[@]}";do
 case "$F" in
 */qfd_sys_face.sv) S+=("$INTERMEDIATE/qfd_sys_face_core_n32.sv");;
 */tb_qfd_sys_face.sv) S+=("$INTERMEDIATE/tb_qfd_sys_face_n32.sv");;
 *) S+=("$F");;
 esac
done
S+=("$R/rtl/qwen_split/qfd_sys_face_record_port_n32.sv"
 "$R/rtl/qwen_split/qfd_sysface_reset32.sv"
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sysface32.sv"
 "$INTERMEDIATE/qfd_syscal_n32.sv"
 "$INTERMEDIATE/protocol_gold_core.sv" "$INTERMEDIATE/protocol_gold_wrapper.sv")
if [ -f "$INTERMEDIATE/protocol_bounded.sv" ];then
 S+=("$INTERMEDIATE/protocol_bounded.sv" "$INTERMEDIATE/protocol_bounded_helpers.sv")
else S+=("$INTERMEDIATE/qfd_sys_face_n32.sv");fi
S+=("$R/rtl/qwen_split/qfd_sysface_logic_helpers.sv" "$R/rtl/qwen_split/qfd_sys_face_record_port_n32_opt.sv")
sha256sum "${S[@]}" "$R/tools/qwen_split/sys_face_image.py" > "$OUT/source.sha256"
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_qfd_sys_face \
 -I"$OUT" -I"$R/rtl/qwen_sys/d2d_static_20261015" -GMUT="$M" -GMU=1 \
 -GIMG=\""$OUT/img"\" --Mdir "$OUT/obj" "${S[@]}" > "$OUT/build.log" 2>&1
set +e
(cd "$OUT" && ./obj/Vtb_qfd_sys_face +OT_ROM_DIR="$OUT/img" > run.log 2>&1)
RC=$?
set -e
grep -E 'SYS_FACE_(PASS|FAIL)|Error|Fatal' "$OUT/run.log" | tail -12 || true
if [ "$M" = 0 ];then
 grep -q '^SYS_FACE_PASS' "$OUT/run.log";test "$RC" = 0
 grep -Eq '^SYSFACE32_WRAPPER_CHECKS [1-9][0-9]*$' "$OUT/run.log"
else grep -q '^SYS_FACE_FAIL' "$OUT/run.log";fi
