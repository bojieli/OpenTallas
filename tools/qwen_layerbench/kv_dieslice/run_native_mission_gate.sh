#!/bin/bash
# Minimal proof of the actual installed expression added to the native C45 HOST.
# HOST_C45 is the prepared native source; SRC contains its production bridge RTL.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
SRC=$(readlink -f "$2"); OUT=$(mkdir -p "$3" && readlink -f "$3")
python3 - "$1" "$OUT" <<'PY'
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
m=re.search(r'\.installed\((static_setup_ready.*)\), \.boot_begin\(d2d_boot_begin\)',s)
if not m or 'mission_start' not in m[1]:raise ValueError('expected prepared HOST mission gate')
t='''`timescale 1ps/1fs
module kv_native_mission_gate #(parameter integer MUT=0)(input wire clk,rst_n,request,static_setup_ready,program_ready,mission_start,output wire boot_begin);
 localparam integer REQUIRE_MISSION_START=1;
 wire installed = '''+m[1]+''';
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) u_bridge(clk,rst_n,request,MUT==1?(static_setup_ready&&program_ready):MUT==2?1'b0:installed,boot_begin);
endmodule
'''
Path(sys.argv[2],'kv_native_mission_gate.sv').write_text(t)
PY
cp "$SRC/rtl/qwen_sys/kv_host_obs_20261019/qkd_d2d_boot_event_bridge.sv" "$OUT/"
cp "$H/../../../rtl/test/qwen_static_kv/tb_native_mission_gate.sv" "$OUT/"
cd "$OUT"
for m in 0 1 2;do
verilator --binary --timing --x-initial unique -Wno-fatal --top-module tb_native_mission_gate -GMUT=$m --Mdir obj$m -j 2 qkd_d2d_boot_event_bridge.sv kv_native_mission_gate.sv tb_native_mission_gate.sv >build$m.log 2>&1
set +e
./obj$m/Vtb_native_mission_gate +verilator+rand+reset+2 >run$m.log 2>&1
rc=$?
set -e
if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q MISSION_GATE_ run$m.log;fi
done
