#!/usr/bin/env python3
"""Extract exact top ports from cached Yosys JSON without loading its cell graph."""
import argparse,hashlib,json,pathlib,re

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=pathlib.Path,required=True);ap.add_argument('--receipt',type=pathlib.Path,required=True);ap.add_argument('--graph',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args()
 r=json.loads(a.receipt.read_text());g=json.loads(a.graph.read_text());digest=sha(a.netlist);assert digest==r['bit_netlist_sha256']==g['input_sha256']
 with a.netlist.open() as f:prefix=f.read(8<<20)
 top=re.search(r'"modules"\s*:\s*\{\s*"'+re.escape(r['top'])+r'"\s*:\s*\{',prefix);assert top,'Expected top must be first/only flattened module'
 ports_start=re.search(r'"ports"\s*:\s*',prefix[top.end():]);assert ports_start
 ports,_=json.JSONDecoder().raw_decode(prefix[top.end()+ports_start.end():]);clocks=g['clock_roots'];rows={}
 for name,p in ports.items():
  rows[name]={'direction':p['direction'],'width':len(p['bits']),'offset':p.get('offset',0),'upto':p.get('upto',0),'source_netlist_bit_ids':p['bits'],'physical_face_grant':None,'physical_pin_positions':None}
  if name in clocks:
   assert p['direction']=='input' and len(p['bits'])==1;rows[name]['clock_root_flop_bits']=clocks[name]['flop_bits']
  elif p['direction']=='input':rows[name]['registered_sink_roots']=g['external_ports'][name]['registered_sink_roots']
  elif p['direction']=='output':rows[name]['max_output_generic_logic_levels']=g['external_output_logic_levels'][name]
 assert set(clocks).issubset(rows)
 result={'scope':'EXACT_FULL_CURRENT_JOINED23_TOP_PORTS_NO_FACE_OR_PAD_GRANT','top':r['top'],'input_scalar_netlist_sha256':digest,'receipt_sha256':sha(a.receipt),'graph_sha256':sha(a.graph),'tool_sha256':sha(pathlib.Path(__file__)),'clock_roots':{c:v['flop_bits'] for c,v in clocks.items()},'ports':rows,'includes':['actual 512-bit PMA pins and register gearboxes','both external core487 CDCs','internal FEC CDC and actual 613-step frame transport'],'excludes':['caller TX6/RX2 endpoint state and SRAM','analog PHY/pad macros and placement grant'],'physical_qualified':False}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ports':len(rows),'clock_roots':len(clocks),'input_bits':sum(x['width'] for x in rows.values() if x['direction']=='input'),'output_bits':sum(x['width'] for x in rows.values() if x['direction']=='output')}))
if __name__=='__main__':main()
