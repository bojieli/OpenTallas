#!/usr/bin/env bash
set -euo pipefail
cd partition_probe_r3
ln -sfn ../libs libs
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l cut_json.log -p "$L read_verilog -lib ../macro_bb.v; read_verilog partitioned.v; hierarchy -check -top qkd_hr_ingest_qm; write_json partitioned.json" > cut_json_stdout.log 2>&1
