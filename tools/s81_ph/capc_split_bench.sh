#!/bin/bash
# Run the existing full-shape capture/reference comparison on the extracted
# candidate. Only the DUT binding and source list change, never the oracle.
set -eu
out=$1
mkdir -p "$out"
python3 - "$out/split_runner.sh" <<'PY'
from pathlib import Path
import sys
s = Path('tools/s81_ph/capc_bench.sh').read_text()
def one(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)
one('dsfd_sp_capture_c u_dut (', 'dsfd_sp_capture_split_candidate u_dut (.ck_status(ck[0]), .ckv_status(ckv[0]), ')
one('  rtl/v41rom/ot_v41_ret.sv', '  rtl/common/ot_ratio_cdc_fifo.sv rtl/v41rom/ot_v41_ret.sv')
one('rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv $G/capc_shim.sv',
    'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_split_candidate.sv $G/capc_shim.sv')
Path(sys.argv[1]).write_text(s)
PY
bash "$out/split_runner.sh" "$@"
