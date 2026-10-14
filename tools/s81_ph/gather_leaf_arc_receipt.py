#!/usr/bin/env python3
"""Normalize immutable expanded STA port reports, without changing IO constraints."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('archive');ap.add_argument('--source-commit',required=True);ap.add_argument('--sides',nargs='+',choices=['rw','re'],default=['rw','re']);a=ap.parse_args();D=Path(a.archive)
num=r'[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?'
def term(block,text):
 m=re.search(r'^\s*('+num+r')(?:\s+'+num+r')?\s+(?:[\^v]\s+)?'+re.escape(text)+r'\s*$',block,re.M)
 if not m:raise ValueError('Missing '+text)
 return float(m[1])
def blocks(text):return re.split(r'(?=^Startpoint: )',text,flags=re.M)[1:]
def path(block,dr,kind,R):
 start=re.search(r'^Startpoint: (\S+)',block,re.M)[1];end=re.search(r'^Endpoint: (\S+)',block,re.M)[1]
 arrival=term(block,'data arrival time');slack=term(block,'slack (MET)') if 'slack (MET)' in block else term(block,'slack (VIOLATED)')
 uncertainty=abs(term(block,'clock uncertainty'));cppr=term(block,'clock reconvergence pessimism');assert abs(cppr)<.001,(start,end,'Nonzero CPPR needs explicit derivation')
 rec={'start':start,'end':end,'arrival_ps':arrival,'slack_ps':slack,'uncertainty_ps':uncertainty,'cppr_ps':cppr}
 if kind=='INPUT':
  ext=term(block,'input external delay');rec['external_delay_ps']=ext;rec['pin_to_D_ps']=round(arrival-ext,4)
  if dr=='MAX':
   # Setup deadline = next833.333 edge -U -raw_setup. Reports round to.01ps.
   edge=re.findall(r'^\s*('+num+r')\s+'+num+r'\s+clock core_clk \(rise edge\)',block,re.M)[-1]
   raw=float(edge)-uncertainty-ext-slack;rec.update(raw_setup_constraint_ps=round(raw,4),normalized_s_ps=round(raw+R,4))
  else:
   raw=ext-uncertainty-slack;rec.update(raw_hold_constraint_ps=round(raw,4),normalized_h_ps=round(raw-R,4))
 else:rec.update(master_ck_to_pin_ps=arrival,normalized_o_ps=round(arrival-R,4))
 return rec
all_arcs={};summary={};hashes={}
for side in a.sides:
 ck=json.loads((D/side/'ck.json').read_text());summary[side]={'corners':{},'clock':{c:{'boundary':ck[c]['boundary'],'all':ck[c]['all'],'macro_max_slew_ps':ck[c]['macros']['max_slew']} for c in ['tt','ss','ff']}}
 all_arcs[side]={}
 for c in ['tt','ss','ff']:
  f=D/side/'corners'/(c+'.log.gz');text=gzip.open(f,'rt').read();hashes[str(f.relative_to(D))]=hashlib.sha256(f.read_bytes()).hexdigest();R=ck[c]['boundary']['mean'];arcs={};counts={}
  for dr in ['MAX','MIN']:
   for kind in ['INPUT','OUTPUT']:
    marker='S81_ALL_'+kind+'_ARCS_'+dr+' '+c;section=text.split(marker+'\n',1)[1].split('S81_ALL_',1)[0];records={}
    for block in blocks(section):
     rec=path(block,dr,kind,R);port=rec['start'] if kind=='INPUT' else rec['end'];key=('normalized_s_ps' if dr=='MAX' else 'normalized_h_ps') if kind=='INPUT' else 'normalized_o_ps'
     worse=lambda x,y: x[key]>y[key] if (kind=='INPUT' or dr=='MAX') else x[key]<y[key]
     if port not in records or worse(rec,records[port]):records[port]=rec
    expected={f'li[{i}]' for i in range(1104)}|{f'ci[{i}]' for i in range(636)}|{'fi[0]','fi[1]'} if kind=='INPUT' else {f'lo[{i}]' for i in range(828)}|{f'co[{i}]' for i in range(848)}|{'fo[0]','fo[1]'}
    assert expected<=set(records),(side,c,kind,dr,'missing',expected-set(records))
    assert set(records)-expected<=({'rs'} if kind=='INPUT' else {'rso'}),(side,c,kind,dr,'unexpected',set(records)-expected)
    for port in set(records)-expected:records[port]['scope']='ASYNC_RESET_CONTROL_not_data_pair'
    arcs[kind.lower()+'_'+dr.lower()]=records;counts[kind+'_'+dr]=len(records)
  all_arcs[side][c]=arcs
  m=re.search(r'GATE_PC setup WNS ('+num+r') hold WNS ('+num+r')',text);assert m
  classes={m[1]:{'paths':int(m[2]),'worst_slack_ps':float(m[3]),'example':m[4]} for m in re.finditer(r'GATE_PC (\S+)\s+(\d+) paths, worst slack ('+num+r') ps \(e.g. ([^)]+)\)',text)}
  summary[side]['corners'][c]={'setup_ps':float(m[1])*1e12,'hold_ps':float(m[2])*1e12,'R_ps':R,'ports':counts,'classes':classes}
for side in a.sides:
 forward={}
 for c in ['tt','ss','ff']:
  x=all_arcs[side][c];rows=[]
  for kind,N,inp,out,offs in [('horizontal',828,'li','lo',276),('vertical',636,'ci','co',0)]:
   for bit in range(N):
    ip=f'{inp}[{bit+offs}]';op=f'{out}[{bit if kind=="horizontal" else bit+212}]'
    # This local FF's two roles establish its own exact launch/input arcs;
    # inter-leaf consumption below uses lo[b]->li[b], co[b]->ci[b].
    rows.append({'kind':kind,'input':ip,'output':op,'s_ps':x['input_max'][ip]['normalized_s_ps'],'h_ps':x['input_min'][ip]['normalized_h_ps'],'o_max_ps':x['output_max'][op]['normalized_o_ps'],'o_min_ps':x['output_min'][op]['normalized_o_ps']})
  forward[c]=rows
 all_arcs[side]['forwarding_roles']=forward
pairs={}
for c in ['tt','ss','ff']:
 rows=[]
 for side in a.sides:
  x=all_arcs[side][c]
  for kind,N,inp,out in [('lane_seam',828,'li','lo'),('chain_seam',636,'ci','co')]:
   for bit in range(N):
    ip=f'{inp}[{bit}]';op=f'{out}[{bit}]';o=x['output_max'][op]['normalized_o_ps'];s=x['input_max'][ip]['normalized_s_ps'];omin=x['output_min'][op]['normalized_o_ps'];h=x['input_min'][ip]['normalized_h_ps']
    rows.append({'master':side,'kind':kind,'source':op,'consumer':ip,'o_max_ps':o,'s_ps':s,'o_plus_s_ps':round(o+s,4),'o_min_ps':omin,'h_ps':h,'o_min_minus_h_ps':round(omin-h,4)})
 pairs[c]=rows
summary['pair_extrema_before_wire']={c:{s:{k:{'worst_max_sum':max((r for r in rows if r['master']==s and r['kind']==k),key=lambda r:r['o_plus_s_ps']),'worst_min_difference':min((r for r in rows if r['master']==s and r['kind']==k),key=lambda r:r['o_min_minus_h_ps'])} for k in ['lane_seam','chain_seam']} for s in a.sides} for c,rows in pairs.items()}
summary.update(status='DIAGNOSTIC_NO_ADOPTION',source_commit=a.source_commit,route_eligible=False,IO_delay_change=False,period_ps=833.333,uncertainty_setup_hold_ps=[60,25],report_precision_ps=.01,hashes=hashes,note='Master ck-to-output includes insertion once; o=arc-R. Input setup constraint=T-U-input_external-slack; s=constraint+R. Input hold constraint=input_external-U-slack; h=constraint-R. Zero CPPR verified on every exported port path. Pair extrema before wire are diagnostics; actual routed wire/clock phases and each assigned die pair budget remain owed. No ordinary0.2T IO WNS adoption.')
(D/'port_arcs.json.gz').write_bytes(gzip.compress((json.dumps(all_arcs,indent=1)+'\n').encode(),mtime=0));(D/'interleaf_pair_arcs.json.gz').write_bytes(gzip.compress((json.dumps(pairs,indent=1)+'\n').encode(),mtime=0));(D/'corner_arc_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({s:summary[s]['corners'] for s in a.sides},indent=1));print(json.dumps(summary['pair_extrema_before_wire']['ss'],indent=1))
