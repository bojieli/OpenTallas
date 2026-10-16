#!/usr/bin/env python3
"""Held per-bit TT screen: actual CTFN bank placement ETMs and routed FSv6.
No routed FN bank, parent, FF hold, clock-delivery or native adoption claim.
"""
import argparse,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools/hier_contract'))
import pinreg_audit as A

def show(c,p):return subprocess.check_output(['git','show',f'{c}:{p}'])
def pins(raw):
 out={}
 for l in raw.decode().splitlines():
  m=re.search(r'-pin_name \{([^}]+)\}.*-location \{([\d.]+) ([\d.]+)\}',l)
  if m:out[m[1]]=(float(m[2]),float(m[3]))
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--routed-receipt',type=Path);ap.add_argument('--swap-fn-fl',action='store_true');ap.add_argument('--bank-dir',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 layout=json.loads((R/'physical/s81_die_pins/ctfn_banks_candidate_1015/layout.json').read_text())
 cell='ot_s81_hc_ctfs_nt';base=f'physical/ref_tile/s81hc_ctfsnt_ref/views/{cell}';raw=show('ef32747a0',base+'/'+cell+'_tt.lib');ins=show('ef32747a0',base+'/insertion.json')
 with tempfile.TemporaryDirectory()as td:
  p=Path(td)/'fs.lib';p.write_bytes(raw);lib=A.parse_lib(p)
 fs=A.pin_metrics(lib,A.clock_refs(lib,json.loads(ins),'tt'))
 ffraw=show('ef32747a0',base+'/'+cell+'_ff.lib')
 with tempfile.TemporaryDirectory()as td:
  p=Path(td)/'fs_ff.lib';p.write_bytes(ffraw);libff=A.parse_lib(p)
 ffs=A.pin_metrics(libff,A.clock_refs(libff,json.loads(ins),'ff'));ffn={}
 receipt=json.loads(a.routed_receipt.read_text())if a.routed_receipt else {}
 if receipt:
  rr={v.get('cell'):v for v in receipt.values()if v.get('cell','').startswith('ot_s81_hc_ctfnq')}
  assert len(rr)==5 and all(v.get('native_timing_pass',v['qualification']=='COMPONENT_NATIVE_PASS')for v in rr.values()),'all five current routed bank components required'
 fn={};sources={'FS':{'record':'ef32747a0','sha256':hashlib.sha256(raw).hexdigest()}}
 for g in layout['groups']:
  p=a.bank_dir/g['cell'];lp=p/(g['cell']+'_tt.lib');ip=p/'insertion.json';lib=A.parse_lib(lp);mm=A.pin_metrics(lib,A.clock_refs(lib,json.loads(ip.read_text()),'tt'))
  sources[g['cell']]={'lib_sha256':hashlib.sha256(lp.read_bytes()).hexdigest(),'insertion_sha256':hashlib.sha256(ip.read_bytes()).hexdigest(),'scope':'UNQUALIFIED_PLACEMENT_ONLY'}
  ffp=p/(g['cell']+'_ff.lib');fl=A.parse_lib(ffp);fm=A.pin_metrics(fl,A.clock_refs(fl,json.loads(ip.read_text()),'ff'))
  if receipt:
   assert rr[g['cell']]['lib_sha256']==sources[g['cell']]['lib_sha256'] and rr[g['cell']]['insertion_sha256']==sources[g['cell']]['insertion_sha256']
   assert rr[g['cell']]['ff_lib_sha256']==hashlib.sha256(ffp.read_bytes()).hexdigest()
   sources[g['cell']].update(scope='ACTUAL_ROUTED_NATIVE_COMPONENT',record=rr[g['cell']]['record'])
  for op,ids in [('fd',g['fd_bits']),('fv',g['fv_bits'])]:
   for local,global_ in enumerate(ids):
    for parent,child in [(op+'_in',op+'_in'),(op+'m',op+'m')]:
     metric=dict(mm[f'{child}[{local}]']);
     if metric['out']is not None:metric['out']+=.76*8.64
     fn[f'{parent}[{global_}]']=metric;ffn[f'{parent}[{global_}]']=fm[f'{child}[{local}]']
 pp={'fn':pins(show('902e0f18f','physical/s81_die_pins/ctfn_banks_candidate_1015/ot_s81_hc_ctfn_banks_candidate.tcl')),'fs':pins(show('b875feb3a','physical/s81_die_pins/v25_hc_norm_fs_yshift_candidate/ot_s81_hc_ctfs_nt.tcl'))}
 metrics={'fn':fn,'fs':fs};ffmetrics={'fn':ffn,'fs':ffs};place={'fn':(412.56 if a.swap_fn_fl else 438.48,34.56),'fs':(790.56,51.84)};H=844.56;results=[]
 def xy(k,n,period):
  x,y=pp[k][n];t,h=place[k];return x,period*H+t+h-y
 for name,src,dst,sp,dp,ports in [('FSprev_to_FN','fs','fn',0,1,[('fd_out','fd_in',2920),('fv_out','fv_in',7)]),('FN_to_FS','fn','fs',0,0,[('fdm','fdm',2920),('fvm','fvm',7)])]:
  legs=[];missing=[];holds=[];hold_missing=[]
  for sa,sb,n in ports:
   for i in range(n):
    s,t=f'{sa}[{i}]',f'{sb}[{i}]';o=metrics[src].get(s,{}).get('out');c=metrics[dst].get(t,{}).get('inp')
    if o is None or c is None:missing.append([s,t]);continue
    lo=ffmetrics[src].get(s,{}).get('lmin');ho=ffmetrics[dst].get(t,{}).get('hold')
    if lo is None or ho is None:hold_missing.append([s,t])
    else:holds.append({'src':s,'dst':t,'zero_wire_gap_ps':lo-ho,'slack_ps':lo-ho-100})
    x,y=xy(src,s,sp);xx,yy=xy(dst,t,dp);L=abs(x-xx)+abs(y-yy);cost=o+c+.76*L;legs.append({'src':s,'dst':t,'launch_ps':o,'capture_ps':c,'length_um':L,'slack_ps':683.333-cost})
  legs.sort(key=lambda v:v['slack_ps']);results.append({'name':name,'count':len(legs),'missing_count':len(missing),'negative_count':sum(x['slack_ps']<0 for x in legs),'min_slack_ps':legs[0]['slack_ps'],'worst':legs[:8],'ff_hold_missing':hold_missing,'ff_min_zero_wire_gap_ps':min((h['zero_wire_gap_ps']for h in holds),default=None),'ff_hold_failures':sum(h['slack_ps']<0 for h in holds),'ff_worst':sorted(holds,key=lambda h:h['slack_ps'])[:8]})
 out={'status':'ANALYTIC_ROUTED_VIEWS_TT_FF_SCREEN'if receipt else 'UNQUALIFIED_MIXED_ROUTE_PLACEMENT_ANALYTIC_TT_FF','outline_um':[576.72,H],'swap_fn_fl':a.swap_fn_fl,'budget_ps':683.333,'internal_bank_output_wire_um':8.64,'sources':sources,'results':results,'open':[*(['All five banks routed native TT/FF/DRC0']if not receipt else []),'Full actual parent clock/reset/pins/all incident hops','Die clocks phi-R and wireRC/hold','Static whole-HC timeline',*(['View export manifests require historical poststub proof; no view adoption']if receipt and not all(v.get('view_export_manifest_pass',False)for v in rr.values())else [])]};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(results,indent=1))
if __name__=='__main__':main()
