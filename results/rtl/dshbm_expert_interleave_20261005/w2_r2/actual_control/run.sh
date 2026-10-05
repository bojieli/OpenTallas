#!/bin/bash
set -euo pipefail
export TMPDIR=/srv/opentallas/jobs-overflow/hubble-w2-chunks-r2/tmp NUM_CORES=4 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
S=/srv/opentallas/repos/hubble-expert-w2-07e7ffc8f
O=/srv/opentallas/jobs-overflow/hubble-w2-chunks-r2
cd "$S"
python3 - "$O" <<'PY'
import sys,pathlib
sys.path.insert(0,"tools")
from dshbm_expert_interleave_native import vectors
vectors(pathlib.Path(sys.argv[1])/"reference.txt")
PY
verilator --binary --timing -O2 -Wno-fatal -j 4 --top-module tb_hbm_accel_wg_dispatch --Mdir "$O/obj" rtl/hbm_accel/service/ot_hbm_accel_wg_dispatch.sv rtl/test/hbm_accel/tb_hbm_accel_wg_dispatch.sv > "$O/compile.log" 2>&1
"$O/obj/Vtb_hbm_accel_wg_dispatch" +VECTORS="$O/reference.txt" > "$O/dispatch.log" 2>&1
"$O/obj/Vtb_hbm_accel_wg_dispatch" +VECTORS="$O/reference.txt" +mut=1 > "$O/duplicate.log" 2>&1
grep -q "DISPATCH_PASS patterns=117649 accepted_descriptors=4941258" "$O/dispatch.log"
grep -q DUPLICATE_REJECTED_NO_DESCRIPTOR "$O/duplicate.log"
printf PASS_W2_CHUNK_CONTROL_ONLY > "$O/terminal.txt"
