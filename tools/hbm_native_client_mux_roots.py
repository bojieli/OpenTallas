#!/usr/bin/env python3
"""Actual logical clock-root inventory of the finite native K ownership mux."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);src=ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_native_client_mux.sv';js=(out/'mux.json').resolve()
 script=f'read_verilog -sv {src}; hierarchy -top ot_hbm_native_client_mux; proc; flatten; opt; memory_map; opt; stat; write_json {js}'
 cp=subprocess.run(['yosys','-p',script],capture_output=True,text=True);(out/'yosys.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout[-2000:]+cp.stderr
 mod=json.loads(js.read_text())['modules']['ot_hbm_native_client_mux'];names={v:f'pc_clk[{i}]'for i,v in enumerate(mod['ports']['pc_clk']['bits'])};roots={};latches=[]
 for name,c in mod['cells'].items():
  if 'latch' in c['type'].lower():latches.append(name)
  if c['type'].lower().startswith(('$dff','$adff','$sdff')):
   key=names[c['connections']['CLK'][0]];roots[key]=roots.get(key,0)+len(c['connections']['Q'])
 assert not latches and len(roots)==32
 result=dict(schema='opentallas.hbm.native_K_client_mux_roots.v1',status='pass',logical_FF_by_root=roots,total_logical_FF=sum(roots.values()),maximum_root_FF=max(roots.values()),actual_SRAMs=0,read_owner_entries_per_PC=64,write_owner_entries_per_PC=32,client_id_bits=2,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),scope='Mux only; add exactly once per shared physical stack. Native common controller/response SRAMs and clients are separate inventory. pc_clk32 must have the same HBM frequency/phase. Logical count is not CTS or physical admission.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
