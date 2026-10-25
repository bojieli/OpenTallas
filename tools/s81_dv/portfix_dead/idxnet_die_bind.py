#!/usr/bin/env python3
"""Connect the six priced IDXNET lanes and the planned reserve SerDes pair.

Usage: idxnet_die_bind.py IN.v PLAN.json MAP_IN.json OUT.v MAP_OUT.json REPORT.json
Run after PORTFIX, F2B and frame-forward adapters. Leaves hard-core timing and
lane-register insertion to bind.py; adds no pipeline stage itself. Never tie a
missing endpoint off. The reserve PHYs use the same one-core-clock sources as
their adjacent existing PHYs; bound die generation supplies the plan clock/reset.
"""
from pathlib import Path
import json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'physical/die_plan/s81/bind'))
import asbparse as A
src,pf,mf,dst,mo,rf=sys.argv[1:]
p=json.loads(Path(pf).read_text());mp=json.loads(Path(mf).read_text());lines,inst=A.parse(src)
rep={'lanes':[],'reserve_phys':[],'removed_ports':[],'errors':[],'added_adapter_cycles':0}
LANES=[
 ('tp__bk_sel__s_7N_LP','bk_sel','u_bk_sel','tpn_o','s_7N_LP','u_s_7N','tp_i',276),
 ('tp__s_7N_LP__bk_sel','s_7N_LP','u_s_7N','tp_o','bk_sel','u_bk_sel','tpn_i',276),
 ('tp__bk_sel__s_7S_LP','bk_sel','u_bk_sel','tps_o','s_7S_LP','u_s_7S','tp_i',276),
 ('tp__s_0S_LP__s_0N_LP','s_0S_LP','u_s_0S','tp_o','s_0N_LP','u_s_0N','tm',276),
 ('qc__iqf__s_0N_LP','iqf','u_iqf','qc','s_0N_LP','u_s_0N','qc',258),
 ('ql__s_0N_LP__iqf','s_0N_LP','u_s_0N','ql','iqf','u_iqf','ql',513),
]
neww=[];newinst=[];newio=[]
def conn(d,n):return next((e for q,e in d['conns'] if q==n),None)
def setc(n,port,expr):
 d=inst[n];d['conns']=[[q,expr if q==port else e] for q,e in d['conns']]
 if not any(q==port for q,e in d['conns']):d['conns'].append([port,expr])
 d['dirty']=True
for n in ('u_bk_sel','u_s_7N','u_s_7S','u_s_0S','u_s_0N','u_iqf'):
 if n not in inst:rep['errors'].append('missing real endpoint '+n)
if rep['errors']:Path(rf).write_text(json.dumps(rep,indent=1));raise SystemExit(rep['errors'])
inst['u_iqf']['module']='dsdv_idx_qfs';inst['u_iqf']['dirty']=True
inst['u_iqf']['conns']=[[q,e] for q,e in inst['u_iqf']['conns'] if q not in ('qc0','qc1','uid','st')]
if not conn(inst['u_iqf'],'fault'):rep['errors'].append('iqf sticky-fault sink missing (PORTFIX must run first)')
inst['u_s_7N']['module']='ot_s81sl_slice_lepe_mab_tp_mu_72';inst['u_s_7N']['dirty']=True
inst['u_s_0S']['module']='ot_s81sl_slice_lepw_mab_tp_mu_72';inst['u_s_0S']['dirty']=True
ports={e['id']:e for e in p['ports']};lanes={e['id']:e for e in p['lanes']}
for lid,sp,si,sport,dp,di,dport,width in LANES:
 lane=lanes.get(lid)
 if lane is None:rep['errors'].append('missing priced plan lane '+lid);continue
 edges=[ports[k] for k in lane['ports']]
 if edges[0]['src']['part']!=sp or edges[-1]['dst']['part']!=dp or any(e['width']!=width for e in edges):
  rep['errors'].append('plan endpoint/width mismatch '+lid);continue
 price=p.get('latency',{}).get('lanes',{}).get(lid,{}).get('cycles')
 if price is None:rep['errors'].append('missing latency for '+lid);continue
 net='idxn_'+re.sub(r'[^A-Za-z0-9_]','_',lid)
 old=(conn(inst[si],sport),conn(inst[di],dport))
 setc(si,sport,net);setc(di,dport,net);neww.append(f'  wire [{width-1}:0] {net};')
 rep['lanes'].append({'lane':lid,'src':edges[0]['src'],'dst':edges[-1]['dst'],'width':width,'cycles':price,
                      'rtl_src':si+'.'+sport,'rtl_dst':di+'.'+dport,'wire':net,'old_connections':old})
# Four physical SerDes columns, not ideal loopback wires: each has independent PMA IO.
part_names={q['name'] for q in p['partitions']}
for side,ep in (('EN','u_s_7N'),('WS','u_s_0S')):
 for n in (2,3):
  name=f'lk_{side}{n}';ip='u_'+name
  if name not in part_names:rep['errors'].append('reserve PHY has no plan slot '+name);continue
  if ip in inst:rep['errors'].append('reserve PHY already exists; refusing duplicate '+ip);continue
  template=inst[f'u_lk_{side}{n-2}'];ec=inst[ep]
  tx=f'idxn_{name}_tx';rx=f'idxn_{name}_rx'
  neww += [f'  wire [511:0] {tx};',f'  wire [513:0] {rx};']
  setc(ep,f'tx{n}',tx);setc(ep,f'rx{n}',rx)
  setc(ep,f'ck_N{n}',conn(ec,f'ck_N{n-2}'))
  conns={'clk':conn(template,'clk'),'rst':conn(template,'rst'),'tx':tx,'rx':rx+'[511:0]','st':rx+'[513:512]'}
  for suffix,direction,width in (('pma_tx','output',544),('pma_tck','output',1),('pma_rx','input',544),('pma_rck','input',1)):
   pn=name+'_'+suffix;conns[suffix]=pn;newio.append((pn,direction,width))
  if any(v is None for v in conns.values()):rep['errors'].append('missing clock/reset template '+name);continue
  newinst.append(A.emit(template['module'],template['params'],ip,list(conns.items())))
  mp['parts'][ip]=name
  rep['reserve_phys'].append({'instance':ip,'module':template['module'],'part':name,'parent':ep,
                               'tx_port':f'tx{n}','rx_port':f'rx{n}','clock_source':conns['clk'],'reset_source':conns['rst']})
# Remove the old unconstrained query die IO after wiring the real link endpoints.
dropped={'iqf_ql','iqf_qc0','iqf_qc1'}
h=next(i for i,l in enumerate(lines) if l.startswith('module dv_die ('))
m=re.fullmatch(r'module dv_die \((.*)\);',lines[h]);assert m
oldports=[q.strip() for q in m[1].split(',')];kept=[q for q in oldports if q not in dropped]
rep['removed_ports']=[q for q in oldports if q in dropped]
lines[h]='module dv_die ('+', '.join(kept+[n for n,_,_ in newio])+');'
for n,d in inst.items():
 if d.get('dirty'):lines[d['line']]=A.emit(d['module'],d['params'],n,d['conns'])
lines=[l for l in lines if not any(re.fullmatch(r'\s*(?:input|output) wire (?:\[[^]]+\] )?'+re.escape(n)+r';\s*',l) for n in dropped)]
end=next(i for i,l in enumerate(lines) if l.strip()=='endmodule')
newdecl=[f'  {direction} wire '+(f'[{width-1}:0] ' if width>1 else '')+n+';' for n,direction,width in newio]
lines[end:end]=newdecl+neww+newinst
text='\n'.join(lines)
for n in dropped:
 if re.search(r'\b'+re.escape(n)+r'\b',text):rep['errors'].append('removed die IO remains referenced '+n)
Path(rf).write_text(json.dumps(rep,indent=1))
if rep['errors']:raise SystemExit(json.dumps(rep['errors']))
Path(dst).write_text(text);Path(mo).write_text(json.dumps(mp,indent=1))
print(json.dumps({'lanes':len(rep['lanes']),'reserve_phys':len(rep['reserve_phys']),'removed_query_ports':rep['removed_ports'],'errors':rep['errors']}))
