#!/bin/bash
# re-run the failed split-lint pieces: slices get the ASAP7 v2 ROM macro model, svc runs at low parallelism (were SIGKILLed at 6 jobs)
cd /home/ubuntu/scratch/binder4-1023/s81/b3r8/lint
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator_bin
ROM=/home/ubuntu/wt/binder4-s81-1023/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
one() { d=$1; cd $d; grep -q ot_rom_4096x72_m8.v verilator_lint.f || echo $ROM >> verilator_lint.f
  /usr/bin/time -f "%M" -o maxrss.txt bash -c "ulimit -s unlimited; $V -f verilator_lint.f" > relint.log 2>&1
  echo "$d rc=$? err=$(grep -c '^%Error' relint.log) maxrss_kb=$(cat maxrss.txt)"; }
export -f one; export V ROM
python3 -c "
import json;print('\n'.join(json.load(open('../verify_report.json'))['lint']['failed_runs']))" | xargs -P 2 -I{} bash -c 'one {}'
