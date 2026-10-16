#!/bin/bash
set -eu
out=$1
mut=${2:-0}
mkdir -p "$out"
python3 - "$out" "$mut" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]);mut=int(sys.argv[2])
s=Path('rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv').read_text();s=s[s.index('module ot_s81_hc_ctfx_cap #'):];s=s[:s.index('endmodule')+len('endmodule')];(out/'ref.sv').write_text(s.replace('ot_s81_hc_ctfx_cap','ot_s81_hc_ctfx_cap_ref',1))
s=Path('rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctfx_cap_pinpipe.sv').read_text()
if mut==1:s=s.replace('fdx <= n_fd;', 'fdx <= fd_in;')
if mut==2:s=s.replace('fv <= n_fv;', 'fv <= fv_in;')
if mut==3:s=s.replace('fdx_local <= fdx;', 'fdx_local <= fdx ^ 1;')
(out/'dut.sv').write_text(s)
PY
iverilog -g2012 -s tb -o "$out/sim" tools/s81_suhc/cap_pinpipe/tb.sv "$out/dut.sv" "$out/ref.sv"
vvp "$out/sim" +mut="$mut"
