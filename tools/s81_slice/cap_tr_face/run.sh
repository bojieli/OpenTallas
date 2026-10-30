#!/bin/bash
set -eu
O=$1
mkdir -p "$O/src"
R=$(pwd)
python3 - "$R" "$O" <<'PY2'
from pathlib import Path
import sys
r,o=map(Path,sys.argv[1:]);s=r/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv'
import subprocess
g=subprocess.check_output(['git','show','b3546d09c02d79f8e05f9a1b242b781756064fbb:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv'],text=True)
(o/'src/gold.sv').write_text(g.replace('module ot_s81sl_cap_tr #(','module gold_cap_tr #('))
c=s.read_text();m=c[:c.index('endmodule')+len('endmodule')]
m=m.replace('module ot_s81sl_cap_tr #(','module mut_cap_tr #(').replace('rv_raw[0] && rv_raw[1]','rv_raw[0] || rv_raw[1]')
(o/'src/mut.sv').write_text(m+'\n`default_nettype wire\n')
PY2
V=$HOME/.local/opentallas-tools/bin/verilator
"$V" --binary --timing -O1 --build-jobs 4 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -DOT_S81_CAP_TR_FACE_REGS --top-module tb -Mdir "$O/obj" rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv "$O/src/gold.sv" rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv "$O/src/mut.sv" tools/s81_slice/cap_tr_face/tb.sv > "$O/build.log" 2>&1
"$O/obj/Vtb" > "$O/run.log" 2>&1
cat "$O/run.log"
