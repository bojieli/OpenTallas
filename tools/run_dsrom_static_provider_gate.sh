#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir gate
trap 'rc=$?; printf "%s\n" "$rc" > gate/terminal.exit' EXIT
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 - <<'PY'
import pathlib,json,hashlib,subprocess,resource
pins=json.loads(pathlib.Path('source_pins.json').read_text())
for p,h in pins['files'].items():
 if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h:raise ValueError('source pin '+p)
if resource.getrlimit(resource.RLIMIT_FSIZE)[0]!=resource.RLIM_INFINITY:raise ValueError('finite FSIZE')
pathlib.Path('gate/admission.json').write_text(json.dumps({'pins':pins,'meminfo':pathlib.Path('/proc/meminfo').read_text(),'load':pathlib.Path('/proc/loadavg').read_text(),'disk':subprocess.check_output(['df','-B1','.'],text=True),'policy':'2 compile workers, measured2GiB estimate plus100GiBhostreserve; no arbitrarywall/FSIZE/AS caps'},indent=2)+'\n')
PY
/usr/bin/time -v -o gate/build.metrics /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --top-module tb_dsrom_static_provider --Mdir gate/obj -j 2 -Wno-fatal -CFLAGS '-O2 -fno-fast-math -ffp-contract=off -fno-associative-math' -MAKEFLAGS 'OPT_FAST=-O2 OPT_SLOW=-O2' rtl/test/dsrom_sys/tb_dsrom_static_provider.sv rtl/v41die/static_controls/ot_v41_stage37_control_rom.sv rtl/v41die/static_controls/ot_v41_stage38_control_rom.sv > gate/build.log 2>&1
/usr/bin/time -v -o gate/sim.metrics gate/obj/Vtb_dsrom_static_provider > gate/sim.log 2>&1
