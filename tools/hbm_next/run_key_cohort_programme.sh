#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
O=$(mkdir -p "${1:?output}" && readlink -f "$1")
python3 - "$R" "$O" <<'PY'
from pathlib import Path
import hashlib,json,sys
r,o=map(Path,sys.argv[1:]);p=r/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_id.sv'
s=p.read_text();a=s.index(' wire[11:0]c_roff=');b=s.index(' always @(posedge stream_clk or negedge stream_rst_n)',a)
t='''`timescale 1ps/1fs
module actual_key_reloc(input wire stream_clk,input wire[134:0]word,input wire[52:0]wctx,input wire[15:0]wit,input wire wlast,word_v,input wire[31:0]ordinal,output wire[33:0]read_port,output wire[82:0]command,output wire retire);
localparam integer PREL=1,XSLOT=1;
wire[1098:0]packet_observe=0;
'''+s[a:b]+'''
assign read_port=rd_r[33:0];assign command=cmd_c;assign retire=ret_c;
endmodule
'''
(o/'actual_key_reloc.sv').write_text(t)
(o/'extract.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'verbatim actual feed R/C relocation; cache/HBM not included'},indent=2)+'\n')
PY
cp "$R/rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv" "$O/"
cp "$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$O/"
cp "$R/rtl/test/hbm_key_programme_1029/tb_programme.sv" "$O/"
cp "$R/results/hbm_key_cohort_1029/synthetic_programme.hex" "$O/programme.hex"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$O"
for m in 0 1 3;do
 verilator --binary --timing -Wno-fatal --top-module tb_programme -GMUT=$m -j 4 --Mdir obj$m *.sv *.v > build$m.log 2>&1
 set +e
 ./obj$m/Vtb_programme > run$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q KEY_PROGRAMME_PASS run$m.log;else test "$rc" != 0;grep -q PROGRAMME_ run$m.log;fi
done
echo KEY_PROGRAMME_ALL_PASS
