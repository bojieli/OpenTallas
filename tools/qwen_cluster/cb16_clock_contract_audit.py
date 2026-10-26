#!/usr/bin/env python3
"""Read-only exact CB16 staged clock references + actual post-CTS geometry.
Never edits a gate/source, substitutes an A0 stand-in, or launches physical work.
"""
import argparse,collections,fnmatch,hashlib,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lef(p, measured):
 t=p.read_text();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t);W,H=map(float,m.groups());pins={}
 for x in re.finditer(r'\bPIN\s+(\S+)\s+(.*?)\bEND\s+\1(?:\s|$)',t,re.S):
  n,b=x.groups()
  if n not in measured and not re.search(r'\bUSE\s+CLOCK\b',b):continue
  rs=[list(map(float,z)) for z in re.findall(r'\bRECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',b)]
  if not rs:raise ValueError('clock without geometry '+n)
  pins[n]=[sum((a+c)/2 for a,b,c,d in rs)/len(rs),sum((b+d)/2 for a,b,c,d in rs)/len(rs)]
 return W,H,pins

def xform(x,y,w,h,o):
 return {'R0':(x,y),'MY':(w-x,y),'MX':(x,h-y),'R180':(w-x,h-y)}[o]
def dictionary(t,name):
 m=re.search(r'set ::'+name+r' \[dict create (.*?)\]',t,re.S)
 xs=m[1].replace('\\','').split();return {xs[i]:float(xs[i+1]) for i in range(0,len(xs),2)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();run=a.run;src=run/'src';a.out.mkdir(parents=True,exist_ok=True)
 specp=src/'physical/ref_tile/qfd_c_b16_rgxb/spec.json';s=json.loads(specp.read_text());ck=json.loads((run/'ck.json').read_text())
 dpath=run/'routes/gate/work/orfs/gate_layout_placed.json';d=json.loads(dpath.read_text());blocks={x[0]:x for x in d['blocks']}
 roots={}
 for n in s['clock_ports']:
  p=[q for q in d['pins'] if q[0]==n];assert p,n
  roots[n]=dict(pin_xy_um=[sum((q[2]+q[4])/2 for q in p)/len(p),sum((q[3]+q[5])/2 for q in p)/len(p)],contacts=[])
 code='\n'.join((src/p).read_text() for p in s['sources'] if p.endswith(('.sv','.v')));code=re.sub(r'//[^\n]*','',code)
 hookp=src/'tools/qwen_cluster/cb16_km/cb16_ckkm.tcl';hook=hookp.read_text();scalar=dictionary(hook,'ot_cbk_ins');perpin=dictionary(hook,'ot_cbk_ins_pin')
 records=[];issues=[];manifest={str(p.relative_to(src)):sha(p) for p in [specp,hookp]+[src/p for p in s['sources']]};vmodels={}
 for child in s['children']:
  v=src/child['view'];master=v.name
  if master not in vmodels:
   lp=v/(master+'.lef');ip=v/'insertion.json';ins=json.loads(ip.read_text());w,h,pins=lef(lp,ins.get('clock_measurements',{}));prov=bool(ins.get('standin')) or 'a0_standin' in str(v)
   for p in [lp,ip]+[v/n for n in ['abstract.json','child_lint.json'] if (v/n).exists()]:manifest[str(p.relative_to(src))]=sha(p)
   vmodels[master]=(w,h,pins,ins,prov)
  w,h,pins,ins,prov=vmodels[master]
  names=[n for n in blocks if fnmatch.fnmatchcase(n,child['inst'])];assert len(names)==1,(child['inst'],names)
  n=names[0];b=blocks[n];assert abs(b[2]-child['at'][0])<.002 and abs(b[3]-child['at'][1])<.002,(n,b,child)
  local=n.split('.')[-1]
  pats=list(re.finditer(r'\b'+re.escape(master)+r'\s+'+re.escape(local)+r'\s*\((.*?)\);',code,re.S))
  assert len(pats)==1,(master,local,len(pats));ports=dict(re.findall(r'\.(\w+)\s*\(\s*(ck_c\dr\d)\s*\)',pats[0][1]))
  for p,xy in pins.items():
   root=ports.get(p)
   if root not in roots:issues.append(dict(kind='unmapped_actual_clock_pin',inst=n,pin=p));continue
   q=xform(*xy,w,h,child.get('orient','R0'));xyg=[round(q[0]+child['at'][0],3),round(q[1]+child['at'][1],3)]
   refs={}
   for c in ['tt','ff']:
    item=(ins.get('clock_measurements',{}).get(p,{}) or {}).get(c,{})
    st=item.get('all') or item.get('boundary')
    if st:refs[c]={k:st.get(k) for k in ['mean','min','max']}
    elif p in ins.get('per_pin',{}).get(c,{}):
     mean,lo,hi=ins['per_pin'][c][p];refs[c]=dict(mean=mean,min=lo,max=hi)
    elif len(pins)==1:
     st=ins.get(c,{}).get('all') or ins.get(c,{}).get('boundary');refs[c]={k:st.get(k) for k in ['mean','min','max']} if st else None
    else:refs[c]=None
   proxy=perpin.get(p,150.) if 'qfd_tile_n' in master else scalar.get(master)
   row=dict(inst=n,master=master,pin=p,root=root,xy_um=xyg,view=child['view'],classification='PROVISIONAL_NOT_A_VIEW' if prov else 'supplied_closed_view',refs_ps=refs,legacy_TT_proxy_ps=proxy,legacy_TT_proxy_error_ps=round(proxy-refs['tt']['mean'],3) if proxy is not None and refs['tt'] else None)
   records.append(row);roots[root]['contacts'].append(row)
 for n,r in roots.items():
  pts=[x['xy_um'] for x in r['contacts']];x,y=r['pin_xy_um'];r['hard_clock_pins']=len(pts);r['bbox_um']=[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)];r['max_pin_to_hard_clock_manhattan_um']=round(max(abs(x-p[0])+abs(y-p[1]) for p in pts),3)
  row=ck.get('clock_measurements',{}).get(n,{})
  r['actual_boundary']={c:row.get(c,{}).get('boundary') for c in ['tt','ff']};r['child_flop_contract_present']=any(row.get(c,{}).get('child_flop') for c in ['tt','ff'])
  for c in ['tt','ff']:
   z=r['actual_boundary'].get(c) or {};r[c+'_boundary_spread_ps']=round(z['max']-z['min'],3) if 'max' in z else None
  r.pop('contacts')
 provisional=sum(x['classification']=='PROVISIONAL_NOT_A_VIEW' for x in records)
 summary=dict(schema='opentallas.cb16.clock_contract_geometry_audit.v1',run=str(run),status='CLOCK_FAIL_AND_REAL_A0_CONTRACT_UNRESOLVED',old_clock_mode=s.get('clock'),old_child_clock_ref=s.get('child_clock_ref'),old_clock_entry_domains=s.get('clock_entry_domains'),actual_root_count=len(roots),actual_hard_instances=len(s['children']),actual_hard_clock_pins=len(records),provisional_A0_clock_pins=provisional,supplied_closed_clock_pins=len(records)-provisional,missing_child_flop_domains=sum(not x['child_flop_contract_present'] for x in roots.values()),roots=roots,contacts=records,unmapped=issues,source_manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),artifact_sha256={str(dpath.relative_to(run)):sha(dpath),'ck.json':sha(run/'ck.json')},reference_policy='A0 stand-in assumed/scaled perpin data is evidence of unresolved contract, NEVER a realchild qualification. Closed ring clock_w/r refs remain distinct. Existing within-region80ps rule only; no all-internal/global80 rule.',repair_model=dict(metadata='Declare actual16 samefrequency region roots and explicit entry domains matched to real clock/data pins; current clock=cts plus extraSDC lacks explicit entry-domain metadata; measured child_flop dictionaries exist but use scalar per-master fallback refs.',references='Use actual CLOSED insertion.clock_measurements[clock_pin] TT and FF intervals; no scalar master substitution. REAL A0 source/view required; supplied provisional surrogate blocks adoption.',geometry='Existing rgxc/d diagnostic buffered40um channel/ring route addresses macro-centroid obstacle; preserve those active experiments, no duplicate campaign.',measurement='Balancer1174group latest+TTproxy25.8ps/25782pads does not replace actual boundary373.5/375.7 afterCTS. Require actualTT+FF end-of-flow withinregion measurement, including exact hardchild refs.'))
 (a.out/'model.json').write_text(json.dumps(summary,indent=2)+'\n');(a.out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({k:summary[k] for k in ['status','actual_root_count','actual_hard_instances','actual_hard_clock_pins','provisional_A0_clock_pins','supplied_closed_clock_pins','missing_child_flop_domains','unmapped']}))
if __name__=='__main__':main()
