import re,json,hashlib,collections
from pathlib import Path
p=Path('/home/ubuntu/scratch/qw-l1seam/dh2');raw=(p/'die.v').read_text();glue=(p/'die_glue.sv').read_text()
inst={}
for m in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);',raw,re.M|re.S):
 typ,name,body=m.groups()
 ports=dict(re.findall(r'\.(\w+)\s*\(([^()]*)\)',body))
 inst[name]=dict(type=typ,ports=ports,line=raw[:m.start(1)].count('\n')+1)
(p.parent/'oldgen_d2d_instance_graph.json').write_text(json.dumps(inst,indent=2)+'\n')
drivers=collections.defaultdict(list)
for n,x in inst.items():
 typ=x['type'];ports=x['ports']
 outs=['q0','q1'] if typ.startswith('qfd_rst_rep') else ['b'] if typ.startswith(('qfd_rly','qfd_land')) else ['rso_d','rso_f'] if typ=='qfd_rstsync' else ['rs','pll_ck'] if typ=='qfd_ckbump' else ['cfg_tx_we','cfg_rx_we','cfg_addr','cfg_data','cal_start','cal_seg','result_v','result_value'] if typ=='qfd_sys_face' else ['pll_d2d'] if typ=='qfd_clkrx' else []
 for port in outs:
  if port in ports:drivers[ports[port]].append((n,port))
def trace(net,seen=()):
 if net in seen:raise Exception(('loop',net))
 ds=drivers[net]
 if len(ds)!=1:return [dict(net=net,terminal='NO_UNIQUE_SOURCE',drivers=ds)]
 n,port=ds[0];x=inst[n];typ=x['type'];r=dict(net=net,instance=n,type=typ,port=port,line=x['line'])
 if typ.startswith('qfd_rst_rep'):
  r.update(input=x['ports']['d'],clock=x['ports']['clk'],registered_edges=10 if typ.endswith('p8') else 2);return [r]+trace(r['input'],seen+(net,))
 if typ.startswith(('qfd_rly','qfd_land')):
  r.update(input=x['ports']['a'],clock=x['ports'].get('ck',x['ports'].get('ckf')),edge_kind='forwarded-reset-stage' if typ.startswith('qfd_rlyr') else 'forwarded-data/landing-stage');return [r]+trace(r['input'],seen+(net,))
 if typ=='qfd_rstsync':r.update(input=x['ports']['arst_n'],clock=x['ports']['ck'],registered_edges=2 if port=='rso_d' else 3,asynchronous_assertion=True);return [r]+trace(r['input'],seen+(net,))
 if typ=='qfd_clkrx':r.update(input=x['ports']['pll_fwd'],clock_behavior='assign,sourceblackbox');return [r]+trace(r['input'],seen+(net,))
 return [r]
traces={}
for owner,ports in [('d2d_rom',['ck','por_n','rst_n','cfg_tx_we','cfg_rx_we','cfg_addr','cfg_data','cal_start','cal_seg','result_v']),('sys_face',['ck','rst_n'])]:
 for port in ports:
  traces[owner+'.'+port]=trace(inst[owner]['ports'][port])
r=dict(schema='oldGEN0d4c.source-ancestry-only',adoption=False,sources={f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['die.v','die_glue.sv']},actual_d2d_type=inst['d2d_rom']['type'],candidate_d2d_type='qfd_d2d_static_ovl',traces=traces)
out=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones/oldgen_d2d_reset_input_ancestry.json');out.write_text(json.dumps(r,indent=2)+'\n')
for name,rows in traces.items():
 print(name,' -> '.join(x.get('instance',x['net'])+'.'+x.get('port','?') for x in rows),'plain_edges',sum(x.get('registered_edges',0) for x in rows),'forwarded_steps',sum('edge_kind' in x for x in rows))
