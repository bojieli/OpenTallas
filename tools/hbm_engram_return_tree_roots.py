#!/usr/bin/env python3
"""Source-exact logical register inventory for physical return-tree candidates."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);src=ROOT/'rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_return_tree_static.sv';profiles={}
 for row in [0,1]:
  js=out/f'row{row}.json';script=f'read_verilog -sv {src}; chparam -set ONE_ROW {row} ot_hbm_engram_return_tree_static; hierarchy -top ot_hbm_engram_return_tree_static; proc; opt; memory_map; opt; flatten; opt; stat; write_json {js}'
  cp=subprocess.run(['yosys','-p',script],capture_output=True,text=True);(out/f'row{row}.yosys.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout[-2000:]+cp.stderr
  modules=json.loads(js.read_text())['modules'];tops=[m for m in modules.values()if m.get('attributes',{}).get('top')not in (None,'0','00000000000000000000000000000000')];assert len(tops)==1;m=tops[0]
  names={v:f'node_clk[{i}]'for i,v in enumerate(m['ports']['node_clk']['bits'])};roots={}
  for name,c in m['cells'].items():
   t=c['type'].lower()
   if t.startswith(('$dff','$adff','$sdff')):
    ck=c['connections']['CLK'];assert len(ck)==1 and ck[0]in names;key=names[ck[0]];roots[key]=roots.get(key,0)+len(c['connections']['Q'])
   else:assert t.startswith('$')and not any(s in t for s in ['latch','mem','dff','ffsr'])and t not in ('$ff','$sr','$fsm'),(name,t)
  assert len(roots)==31;profiles['one_row'if row else'two_row']=dict(logical_FF_by_root=dict(sorted(roots.items())),total_logical_FF=sum(roots.values()),maximum_root_FF=max(roots.values()),node_roots=len(roots),sampled_latency_HBM_edges=12 if row else 8)
 result=dict(schema='opentallas.hbm.engram.static_return_tree_roots.v1',status='pass',profiles=profiles,actual_SRAMs=0,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),scope='Tree source only, including pipelined error metadata; real16-entry CDC and original frontend/sharedcontroller/hash/programme are additional inventory. 31 physical source roots require samephase HBM clocks and aligned reset. Logical root count is not actual pin/relayplacement<=500um, CTS/STA or performance admission.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
