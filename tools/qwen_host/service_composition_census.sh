#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
P=${PREREQ_ROOT:-$root}
if [ -z "${PREREQ_ROOT:-}" ] && [ -d "$root/prereq/rtl" ];then P="$root/prereq";fi
mkdir -p "$out"
S=("$root/rtl/qwen_sys/host_20261013/"*.sv)
for f in "$P/rtl/qwen_sys/host_20261013/"*.sv;do
 if [ ! -f "$root/rtl/qwen_sys/host_20261013/$(basename "$f")" ];then S+=("$f");fi
done
S+=("$P/rtl/physical/ot_qkd_host_prompt_capture_pins.sv" "$P/rtl/physical/ot_qfd_prompt_sram_capture.sv" "$P/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$P/rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv" "$P/rtl/physical/ot_qwen_host_ctl.sv" "$P/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$P/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$P/rtl/lib/ot_reset_sync.sv")
python3 - "$P/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$out/memory_bb.sv" <<'PYGEN'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text();a=s.index('module ot_sram_');b=s.index(');',a)+2
pathlib.Path(sys.argv[2]).write_text('(* blackbox *) '+s[a:b]+'\nendmodule\n')
PYGEN
readcmd="read_verilog -defer -sv ${S[*]}"
yosys -Q -T -p "read_verilog -lib $out/memory_bb.sv; $readcmd; hierarchy -top qkd_host_control_packet_capture_service -chparam ENABLE_SERVICE 1; proc; opt; memory_map; opt; write_json $out/composition.json; stat" > "$out/composition-census.log"
python3 - "$out/composition.json" <<'PY' | tee "$out/composition-census-summary.log"
import json,sys
mods=json.load(open(sys.argv[1]))['modules']
def own(m):return sum(len(c['connections']['Q']) for c in m['cells'].values() if 'dff' in c['type'].lower())
def total(n):return own(mods[n])+sum(total(c['type']) for c in mods[n]['cells'].values() if c['type'] in mods)
def walk(n,path):
 m=mods[n]
 if n in ['qkd_host_control_packet_capture_service','qkd_host_control_prompt_capture_service','qkd_host_fullcontrol_service','qkd_host_packet_bundle_service'] or path.count('.')<=3:
  print(path,n,'ownFF',own(m),'recursiveFF',total(n),'pins',sum(len(p['bits'])for p in m['ports'].values()))
 for k,c in m['cells'].items():
  if c['type']in mods:walk(c['type'],path+'.'+k)
walk('qkd_host_control_packet_capture_service','top')
PY
