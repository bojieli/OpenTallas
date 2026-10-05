#!/bin/bash
# Run only from a fresh pinned source packet; shared measured-headroom admission is external.
set -eu
cd "$(dirname "$0")/.."
mkdir gate
trap 'rc=$?; printf "%s\n" "$rc" > gate/terminal.exit' EXIT
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 - <<'PY'
import json,hashlib,pathlib,subprocess,datetime,resource
pins=json.loads(pathlib.Path('source_pins.json').read_text())
for p,h in pins['files'].items():
 if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h: raise ValueError('source changed '+p)
if resource.getrlimit(resource.RLIMIT_FSIZE)[0] != resource.RLIM_INFINITY:raise ValueError('finite inherited FSIZE')
a={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':pins,'meminfo':pathlib.Path('/proc/meminfo').read_text(),'load':pathlib.Path('/proc/loadavg').read_text(),'disk':subprocess.check_output(['df','-B1','.'],text=True),'compiler':subprocess.check_output(['g++','--version'],text=True),'verilator':subprocess.check_output(['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--version'],text=True),'policy':'4 compile workers, measured admission24GiB+100GiB reserve. No arbitrary wall/FSIZE/AS cap. Finite fixture cycle guard is an incompletion verdict, not build deadline.'}
pathlib.Path('gate/admission.json').write_text(json.dumps(a,indent=2)+'\n')
PY
v=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o gate/build.metrics "$v" --binary --timing --top-module tb_dsrom_field_addr --Mdir gate/obj -j 4 -Wno-fatal -DOT_PQ_ROM_PORTS -CFLAGS '-O2 -fno-fast-math -ffp-contract=off -fno-associative-math' -MAKEFLAGS 'OPT_FAST=-O2 OPT_SLOW=-O2' rtl/test/dsrom_sys/tb_dsrom_field_addr.sv rtl/v41die/ot_v41_spine_pq_w17w10.sv rtl/v41die/ot_v41_spine_pq_addr_w17w10.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv > gate/build.log 2>&1
/usr/bin/time -v -o gate/sim.metrics gate/obj/Vtb_dsrom_field_addr > gate/sim.log 2>&1
