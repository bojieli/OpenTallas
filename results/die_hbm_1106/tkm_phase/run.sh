#!/bin/bash
# Run inside an admitted ot-run job. Each execution gets a new evidence directory.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SOURCE=$(realpath "$1")
RUN=${2:-$(mktemp -d "$HERE/run.XXXXXX")}
mkdir -p "$RUN"
if [ -e "$RUN/root.sv" ]; then echo 'fresh evidence directory required' >&2; exit 2; fi
cp "$SOURCE" "$RUN/root.sv"
for name in build_phase.py algebra.c leaf.v csa_miter.v job5.sh job2.sh job_mutant.sh csa_job.sh algebra_job.sh; do cp "$HERE/$name" "$RUN/$name"; done
cd "$RUN"
python3 build_phase.py
yosys -p 'read_verilog -sv phase_actual.sv; hierarchy -top phase_actual; proc; opt; async2sync; opt_clean; write_rtlil phase_actual.il' > prepare_actual.log 2>&1
yosys -p 'read_verilog -sv phase_induct.sv; hierarchy -top phase_actual; proc; opt; async2sync; opt_clean; write_rtlil phase_induct.il' > prepare_induct.log 2>&1
bash job5.sh
bash job2.sh
bash job_mutant.sh
bash csa_job.sh
bash algebra_job.sh
cat algebra_result.json
