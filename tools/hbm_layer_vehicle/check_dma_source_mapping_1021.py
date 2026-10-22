#!/usr/bin/env python3
"""Check compiler source placement against actual vmks->vmdel graph edges."""
import hashlib,importlib.util,json,sys
from pathlib import Path
contract=Path(sys.argv[1]);encoder=Path(sys.argv[2]);output=Path(sys.argv[3]);d=json.loads(contract.read_text())
spec=importlib.util.spec_from_file_location('dma_encoder',encoder);enc=importlib.util.module_from_spec(spec);spec.loader.exec_module(enc)
qs=('SW','SE','NW','NE');rows=[]
for edge in d['edges']:
 s,t=edge['source'],edge['sink']
 if not(s[0].startswith('vmks_') and s[1]=='fill_v' and t[0].startswith('vmdel_')):continue
 origin=s[0][5:7];sm=int(s[0][7:]);pc=4*sm+s[2];stack={'SW':0,'NW':1}[origin]
 assert d['instances'][s[0]]['params']=={'MUT':0,'KRL1':1}
 for port in ['sm_stream','sm_hbm']:
  straps=[v for v in d['straps'] if v['inst']==s[0] and v['port']==port];assert len(straps)==1 and straps[0]['value']==sm,straps
 # row=col=0 and sector PC bits select a concrete legal source address.
 address=(stack<<35)|(pc<<7);actual=enc.source_location(address)
 expected=(qs.index(t[0][6:8]),int(t[0][8:]),t[2]);got=(actual['quarter'],actual['lane'],actual['group']);assert got==expected,(edge,got,expected)
 cmd=[e for e in d['edges'] if e['sink'][0]==s[0] and e['sink'][1]=='vm_v'];assert len(cmd)==1 and cmd[0]['source'][:3]==['vmfc_'+qs[expected[0]],'payload',52],cmd
 rows.append({'origin':origin,'sm':sm,'pc':pc,'landing_quarter':qs[expected[0]],'lane':expected[1],'group':expected[2],'fill_edge':edge['name'],'window_command_edge':cmd[0]['name']})
assert len(rows)==64 and len({(r['origin'],r['pc']) for r in rows})==64
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'status':'PASS','contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),'encoder_sha256':hashlib.sha256(encoder.read_bytes()).hexdigest(),'scope':'64 graph-derived PC-to-landing placements and VM window command fanout; no source producer or physical transport execution claim','rows':rows},indent=2)+'\n');print('DMA_SOURCE_GRAPH_MAPPING_PASS',len(rows))
