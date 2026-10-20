#!/bin/bash
set -euo pipefail
O=$1;mkdir -p "$O"
python3 - "$O" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=Path('rtl/test/qwen_dv/s5/ctlsafe/ctl_gate2_snapshot.sv').read_text()
s=s.replace('wire rst;\n    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));','''wire rst, rst_face;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_face));
    // One boot-only assertion AND release stage; permits32-ary distribution after2face stages.
    reg rst_distribution;
    always @(posedge ck) rst_distribution <= rst_face;
    assign rst = rst_distribution;''')
assert 'reg rst_distribution;' in s
(p/'ctl_resetstage.sv').write_text(s)
PY
yosys -Q -p "read_verilog -sv $O/ctl_resetstage.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv; hierarchy -check -top qfd_dv_s5_ctl; synth -top qfd_dv_s5_ctl -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/generic.json" > "$O/generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/generic.json" --load-cap 16 --top qfd_dv_s5_ctl --name qfd_dv_s5_ctl_bounded4_rst1 --out "$O/qfd_dv_s5_ctl_bounded4_rst1.sv" --helpers "$O/qfd_dv_s5_ctl_bounded_helpers.sv" --record "$O/construction.json" > "$O/construct.log" 2>&1
