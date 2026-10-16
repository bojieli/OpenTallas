"""Enumerate actual six-child HOST source edges at proposed pin coordinates.

This is geometry evidence; PG/RC/parent external grants remain required.
"""
import re,json,hashlib,sys
from pathlib import Path
P=Path('physical/s81_die_pins/host_sd_sliced_1016')
files={};pins={};orig={'ectl':(399.6,0),'native':(0,25.92),**{f'data{k}':(19.44+95.04*k,0) for k in range(4)}}
for child in orig:
 n={'ectl':'s81_host_ectl_local','native':'s81_host_ingest_native_local'}.get(child,f's81_host_sd_data64_s{child[-1]}')
 p=P/(n+'.tcl');files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();pins[child]={}
 for m in re.finditer(r'pin_name \{([^}]+)\}.*?-layer (\w+) -location \{([\d.]+) ([\d.]+)\}',p.read_text()):
  pins[child][m[1]]=[round(float(m[3])+orig[child][0],3),round(float(m[4])+orig[child][1],3),m[2]]
edges=[]
def e(a,ap,b,bp,net):
 pa=pins[a][ap];pb=pins[b][bp];edges.append(dict(net=net,source=[a,ap],target=[b,bp],source_xy_layer=pa,target_xy_layer=pb,manhattan_um=round(abs(pa[0]-pb[0])+abs(pa[1]-pb[1]),3)))
for i in range(515):e('ectl',f'native_host_word[{i}]','native',f'host_word[{i}]',f'host_word[{i}]')
e('ectl','native_tcr','native','t_cr','tcr');e('ectl','native_ocr','native','o_cr','ocr')
for i in range(8):e('ectl',f'native_ack[{i}]','native',f'host_ack_n[{i}]',f'ack[{i}]')
for a,b,n in [('t_v','native_tv','tv'),('fault','native_fault','nf'),('o_v','native_ov','ov'),('o_we','native_owe','owe')]:e('native',a,'ectl',b,n)
for i in range(64):e('native',f't_d[{i}]','ectl',f'native_td[{i}]',f'td[{i}]')
for i in range(32):e('native',f'o_addr[{i}]','ectl',f'native_oa[{i}]',f'oa[{i}]')
for i in range(2):e('native',f'o_d[{64+i}]','ectl',f'native_marker[{i}]',f'od[{64+i}]')
for k in range(4):
 c=f'data{k}'
 for i in range(64):e('native',f'o_d[{64*k+i}]',c,f'o_d[{i}]',f'od[{64*k+i}]')
 for i in range(32):e('native',f'o_addr[{i}]',c,f'o_addr[{i}]',f'oa[{i}]')
 for a,b,n in [('o_v','o_v','ov'),('o_we','o_we','owe')]:e('native',a,c,b,n)
 for i in range(2):e('native',f'o_d[{64+i}]',c,f'marker_class[{i}]',f'od[{64+i}]')
 e(c,'fault','ectl',f'data_fault[{k}]',f'df[{k}]')
# hc[0] enters ECTL and separately fans out from parent external boundary;
# no ECTL data producer is invented for this external pin.
source=Path('rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv');files[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
groups={}
for r in edges:
 key=r['source'][0]+' -> '+r['target'][0];v=groups.setdefault(key,dict(endpoint_edges=0,max_manhattan_um=0));v['endpoint_edges']+=1;v['max_manhattan_um']=max(v['max_manhattan_um'],r['manhattan_um'])
r=dict(schema='opentallas.s81.host_connected_pin_audit.v1',scope='Proposed actual source pin geometry only; no delay/cut/route qualification',source_sha256=files,source_parent_registers=0,internal_endpoint_edges=len(edges),groups=groups,edges=edges,open=['Die slot/parent external endpoints including hc[0], rst and all12 clocks have no granted coordinates','Actual PG and obstruction subtraction, pin escape and parent route on M6/M7','Each child measured phi-R source clock and FF hold; no commonpackagephase assumption','Native launch220/capture190/spread80 TT/FF/DRC0','Compiler fixed reservation calendar beyond init ingress'])
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('results/rtl/s81_host_recovery_1016/host_connected_pin_audit.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(internal_endpoint_edges=len(edges),groups=groups),indent=1))
