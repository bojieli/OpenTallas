#!/usr/bin/env python3
"""Exact mapped D/Q and clock/reset role census for the four-FF source probe."""
import argparse,re,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raw=a.netlist.read_bytes();s=raw.decode();cells=[]
for m in re.finditer(r'(\w+)\s+(\\\S+|\w+)\s*\((.*?)\);',s,re.S):
 ports=dict((k,v.strip())for k,v in re.findall(r'\.(\w+)\((.*?)\)',m[3],re.S))
 if ports:cells.append({'master':m[1],'instance':m[2],'ports':ports})
ff=[c for c in cells if c['master'].startswith('DFF')];assert len(ff)==4
assert all(c['ports']['CLK']=='clk'for c in ff)
payload=[]
for bit in range(2):
 matches=[c for c in ff if c['ports']['D']==f'd[{bit}]'];assert len(matches)==1;payload.append(matches[0])
assert len({c['instance']for c in payload})==2
sync=[c for c in ff if c not in payload];assert all(c['ports']['RESETN']=='arst_n'for c in sync)
assert all(c['ports']['D']not in ['clk','arst_n']for c in ff)
drivers={}
for c in cells:
 for port in ['Y','QN','Q','H']:
  if port in c['ports']:drivers[c['ports'][port]]=(c,port)
def trace(net,seen=None):
 seen=set()if seen is None else seen;assert net not in seen;seen.add(net);c,port=drivers[net]
 if c in ff:return c,1,[c['instance']]
 assert c['master'].startswith(('INV','BUF'));f,depth,path=trace(c['ports']['A'],seen);return f,depth,path+[c['instance']]
outputs=[]
for bit in range(2):
 c,depth,path=trace(f'q[{bit}]');assert c==payload[bit]and depth==1;outputs.append({'output':f'q[{bit}]','source_D':c['ports']['D'],'register_edges':depth,'mapped_Q_path_instances':path})
r={'status':'ACTUAL_MAPPED_FOUR_FF_ONE_DATA_EDGE_ROLE_PROOF','netlist_sha256':hashlib.sha256(raw).hexdigest(),'flops':4,'payload_ff':2,'reset_sync_ff':2,'clock_roots':{'clk':4},'literal_clock_ports':['clk'],'literal_reset_ports':['arst_n'],'registered_clock_or_reset_as_data':False,'generic_added_data_stages':0,'outputs':outputs,'scope':'Actual mapped synthesis D/Q role census only; routed FF recovery/removal, hold, pin access and native ETM remain OPEN.'};a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
