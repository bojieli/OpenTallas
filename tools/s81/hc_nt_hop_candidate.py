#!/usr/bin/env python3
"""Pair real routed n3/v6 native pin arcs with held835.92 geometry; analytic TT screen only."""
import hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hier_contract'))
import pinreg_audit as PA
R=Path(__file__).resolve().parents[2]

def show(c,p):return subprocess.check_output(['git','show',f'{c}:{p}'])
def main():
 p=R/'results/arch/s81_hc_takeover_1015/nt_parent/placement.json';d=json.loads(p.read_text());P={};metrics={};sources={}
 for k,record,kit,cell in [('fn','6de40d441','s81hc_ctfnnt_ref','ot_s81_hc_ctfn_nt'),('fs','ef32747a0','s81hc_ctfsnt_ref','ot_s81_hc_ctfs_nt')]:
  root=f'physical/ref_tile/{kit}/views/{cell}';raw=show(record,f'{root}/{cell}_tt.lib');ins=show(record,f'{root}/insertion.json')
  with tempfile.TemporaryDirectory() as td:
   lp=Path(td)/'view.lib';lp.write_bytes(raw);lib=PA.parse_lib(lp)
  metrics[k]=PA.pin_metrics(lib,PA.clock_refs(lib,json.loads(ins),'tt'));sources[k]=dict(record_commit=record,view=root,lib_sha256=hashlib.sha256(raw).hexdigest(),insertion_sha256=hashlib.sha256(ins).hexdigest())
  s=d['pin_sources'][k];txt=show(s['commit'],s['path']).decode();P[k]={}
  for l in txt.splitlines():
   m=re.search(r'-pin_name \{([^}]+)\}.*-location \{([\d.]+) ([\d.]+)\}',l)
   if m:P[k][m[1]]=[float(m[2]),float(m[3])]
 H=835.92;place={'fn':(438.48,25.92),'fs':(781.92,51.84)}
 def xy(k,n,period):
  x,y=P[k][n];t,h=place[k];return x,period*H+t+h-y
 results=[]
 for name,src,dst,sp,dp,pairs in [('FSprev_to_FN','fs','fn',0,1,[(f'fd_out[{i}]',f'fd_in[{i}]') for i in range(2920)]+[(f'fv_out[{i}]',f'fv_in[{i}]') for i in range(7)]),('FN_to_FS','fn','fs',0,0,[(f'fdm[{i}]',f'fdm[{i}]') for i in range(2920)]+[(f'fvm[{i}]',f'fvm[{i}]') for i in range(7)])]:
  legs=[];missing=[]
  for s,t in pairs:
   sm=metrics[src].get(s,{}).get('out');tm=metrics[dst].get(t,{}).get('inp')
   if sm is None or tm is None:missing.append([s,t]);continue
   x,y=xy(src,s,sp);xx,yy=xy(dst,t,dp);L=abs(x-xx)+abs(y-yy);cost=sm+.76*L+tm
   legs.append(dict(src=s,dst=t,launch_ps=sm,capture_ps=tm,L_um=round(L,3),wire_estimate_ps=.76*L,pair_cost_ps=cost,slack_ps=683.333-cost))
  legs.sort(key=lambda v:v['slack_ps']);results.append(dict(name=name,count=len(legs),missing_count=len(missing),missing=missing[:8],negative_count=sum(v['slack_ps']<0 for v in legs),min_slack_ps=legs[0]['slack_ps'],worst=legs[:8]))
 out=dict(scope='UNQUALIFIED ANALYTIC TT SCREEN: real routed ETM native arcs + candidate R0 geometry; no routed parent/clock/FF hold proof',budget_ps=683.333,budget_basis='833.333-60uncertainty-90same-levelskew; phi-R per tile entry; both routed R<=300ps',wire_ps_per_um=.76,geometry='nt_parent/placement.json',views=sources,results=results,open=['Full parent actual RTL/cell/pin binding','Actual die wire RC/clock delivery and FF hold','CTFXS/CTFL and every other incident join','First/last chain anchors'])
 op=p.parent/'routed_pair_tt_screen.json';op.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({r['name']:{k:r[k] for k in ['count','missing_count','negative_count','min_slack_ps']} for r in results},indent=2))
if __name__=='__main__':main()
