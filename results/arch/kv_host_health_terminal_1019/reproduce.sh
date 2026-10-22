#!/usr/bin/env bash
# Run only through fleet ot-run. First materialize immutable sources.json.gz by basename.
set -euo pipefail
python3 - <<'PYSRC'
import gzip,json,pathlib
for k,v in json.load(gzip.open('sources.json.gz')).items():
 pathlib.Path(pathlib.Path(k).name).write_text(v)
PYSRC
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --version > version.txt
sources=(qkd_host_service_guard.sv qkd_host_guard_fifo.sv qkd_host_ctl_service_pins.sv ot_qwen_host_ctl.sv ot_qfd_pkgctl.sv)
"$v" --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir final tb.sv "${sources[@]}" > final.build.log 2>&1
final/Vtb > final.run.log 2>&1
for m in rawdrop lateadmit resetretain; do
 g=0; c=0; s=qkd_host_service_guard.sv
 if [[ $m == rawdrop ]]; then g=1; fi
 if [[ $m == lateadmit ]]; then c=1; fi
 if [[ $m == resetretain ]]; then
  sed 's/sticky<=0;protocol_fault/sticky<=sticky;protocol_fault/' qkd_host_service_guard.sv > guard_resetretain.sv
  s=guard_resetretain.sv
 fi
 "$v" --binary --timing -Wno-fatal --top-module tb -GGMUT="$g" -GCMUT="$c" -j 2 --Mdir "$m" tb.sv "$s" "${sources[@]:1}" > "$m.build.log" 2>&1
 set +e
 "$m/Vtb" > "$m.run.log" 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
done
python3 audit.py
