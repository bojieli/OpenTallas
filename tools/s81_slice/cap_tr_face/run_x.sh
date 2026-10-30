#!/bin/bash
set -eu
O=$1
mkdir -p "$O/src"
python3 - "$O" <<'PY2'
from pathlib import Path
import subprocess,sys
o=Path(sys.argv[1]);g=subprocess.check_output(['git','show','b3546d09c02d79f8e05f9a1b242b781756064fbb:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv'],text=True)
(o/'src/gold.sv').write_text(g.replace('module ot_s81sl_cap_tr #(','module gold_cap_tr #('))
s=Path('rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv').read_text();m=s[:s.index('endmodule')+len('endmodule')].replace('module ot_s81sl_cap_tr #(','module mut_cap_tr #(')
a="""    reg fault_next;
    always @* begin
        fault_next = fault_state;
        if ((|n_f) || (|(l_v & l_e)) || (|l_f)) fault_next = 1'b1;
    end"""
assert m.count(a)==1
m=m.replace(a,"    wire fault_next = fault_state | (|n_f) | (|(l_v & l_e)) | (|l_f);")
(o/'src/mut.sv').write_text(m+'\n`default_nettype wire\n')
PY2
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
iverilog -g2012 -D OT_S81_CAP_TR_FACE_REGS -s tb_x -o "$O/run.vvp" rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv "$O/src/gold.sv" rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv "$O/src/mut.sv" tools/s81_slice/cap_tr_face/tb_x.sv > "$O/build.log" 2>&1
vvp "$O/run.vvp" > "$O/run.log" 2>&1
cat "$O/run.log"
