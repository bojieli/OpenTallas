#!/usr/bin/env python3
"""Emit a concrete v25 NT parent placement; all absent graph/physical evidence stays open."""
import argparse,copy,hashlib,json,re,subprocess
from pathlib import Path

def show(c,p):return subprocess.check_output(['git','show',f'{c}:{p}']).decode()
def pins(s):
 out={}
 for l in s.splitlines():
  m=re.search(r'-pin_name \{([^}]+)\}.*-location \{([\d.]+) ([\d.]+)\}',l)
  if m:out[m[1]]=[float(m[2]),float(m[3])]
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',default='results/arch/s81_hc_takeover_1015/nt_parent');a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 base='origin/main';path='results/arch/hier_contract_1011/s81_v23_hc_budget.json';raw=show(base,path);old=json.loads(raw)['sub_layouts']['ot_s81_hc_cth'];rows=copy.deepcopy(old['rows']);new=[]
 for r in rows:
  if r['tile']=='ctfx':
   new += [dict(tile='ctfxs_nt',cell='ot_s81_hc_ctfxs_nt',w=576.72,h=25.92,y=386.64),dict(tile='ctfl_nt',cell='ot_s81_hc_ctfl_nt',w=576.72,h=25.92,y=412.56)]
  elif r['tile']=='ctfn':r.update(tile='ctfn_nt',cell='ot_s81_hc_ctfn_nt',y=438.48);new.append(r)
  elif r['tile']=='ctfs':r.update(tile='ctfs_nt',cell='ot_s81_hc_ctfs_nt',h=51.84,y=781.92);new.append(r)
  else:
   if r['y']>=425.52:r['y']=round(r['y']+38.88,3)
   new.append(r)
 H=835.92;W=576.72;instances=[]
 for r in new:
  for col,x in enumerate(r.get('x_cols',old['x_cols']) if r.get('per_col') else [0.]):
   name=r['tile'].replace('[c]',f'[c={col}]').replace('[l]',f'[l={col}]').replace('[g]',f'[g={col}]')
   inst=dict(name=name,cell=r['cell'],x=x,y_from_N=r['y'],w=r['w'],h=r['h'],orient='R0',row_reservation=True,instantiation_status='SOURCE_BINDING_OPEN')
   if r['tile'].startswith('ctnl'):inst['cell']=f'ot_s81_hc_ctnl_l{col}';inst['native_view_binding']='OPEN: actual native successor LEF must be bound, no inherited view'
   if r['cell'].endswith('_column'):inst['params']={'COLUMN':col}
   instances.append(inst)
 assert len({i['name'] for i in instances})==len(instances)
 overlaps=[]
 for i,x in enumerate(instances):
  assert 0<=x['x'] and x['x']+x['w']<=W+.001 and x['y_from_N']+x['h']<=H+.001
  for y in instances[i+1:]:
   dx=min(x['x']+x['w'],y['x']+y['w'])-max(x['x'],y['x']);dy=min(x['y_from_N']+x['h'],y['y_from_N']+y['h'])-max(x['y_from_N'],y['y_from_N'])
   if dx>1e-5 and dy>1e-5:overlaps.append([x['name'],y['name'],dx,dy])
 assert not overlaps,overlaps
 commit='b875feb3a';pinpaths={'xs':'physical/s81_die_pins/v27_hc_ctfxs_spread_candidate/ot_s81_hc_ctfxs_nt.tcl','fl':'physical/s81_die_pins/v24_hc_norm_spread_candidate/ot_s81_hc_ctfl_nt.tcl','fn':'physical/s81_die_pins/v25_hc_norm_fs_yshift_candidate/ot_s81_hc_ctfn_nt.tcl','fs':'physical/s81_die_pins/v25_hc_norm_fs_yshift_candidate/ot_s81_hc_ctfs_nt.tcl'}
 P={};sha={}
 for k,p in pinpaths.items():
  s=show(commit,p);P[k]=pins(s);sha[k]=dict(path=p,commit=commit,sha256=hashlib.sha256(s.encode()).hexdigest())
 places={'xs':(386.64,25.92),'fl':(412.56,25.92),'fn':(438.48,25.92),'fs':(781.92,51.84)}
 def xy(k,n,period=0):
  x,y=P[k][n];top,h=places[k];return x,period*H+top+h-y
 joins=[]
 def join(label,src,dst,pairs,srcperiod=0,dstperiod=0):
  legs=[]
  for s,d in pairs:
   x,y=xy(src,s,srcperiod);xx,yy=xy(dst,d,dstperiod);legs.append(dict(src=s,dst=d,length_um=round(abs(x-xx)+abs(y-yy),3),src_xy=[x,y],dst_xy=[xx,yy]))
  legs.sort(key=lambda v:-v['length_um']);joins.append(dict(name=label,bits=len(legs),over500=sum(v['length_um']>500 for v in legs),max_um=legs[0]['length_um'],worst=legs[:3],scope='actual candidate transforms and exact pin bytes; no clock-adjusted reach claim'))
 join('FSprev_to_FN_data','fs','fn',[(f'fd_out[{i}]',f'fd_in[{i}]') for i in range(2920)]+[(f'fv_out[{i}]',f'fv_in[{i}]') for i in range(7)],0,1)
 join('FSprev_to_XS_data','fs','xs',[(f'fd_out[{i}]',f'fd_in[{i}]') for i in range(1128)]+[(f'fv_out[{i}]',f'fv_in[{i}]') for i in range(7)],0,1)
 join('FN_to_FS_data','fn','fs',[(f'fdm[{i}]',f'fdm[{i}]') for i in range(2920)]+[(f'fvm[{i}]',f'fvm[{i}]') for i in range(7)])
 join('XS_to_FL_data','xs','fl',[(f'fdx[{i}]',f'fdx[{i}]') for i in range(1128)]+[(f'fv[{i}]',f'fv[{i}]') for i in range(7)])
 join('XS_to_FS_partial','xs','fs',[(f'dl_out[{i}]',f'dl_in[{i}]') for i in range(275)])
 join('FS_to_XS_scale','fs','xs',[(f'ul_out[{i}]',f'ul_in[{i}]') for i in range(33)])
 d=dict(schema='opentallas.s81.nt_parent_candidate.v1',status='HELD_GEOMETRY_ONLY',source_contract=dict(path=path,ref=base,sha256=hashlib.sha256(raw.encode()).hexdigest()),outline_um=[W,H],y_from='N face',orientation='R0 explicitly; no inferred MX',rows=new,instances=instances,overlap_count=0,spare_um=2.16,pin_sources=sha,pin_joins=joins,extra_height_from_current_budget_um=45.36,outer_growth_um={'hc_s_10_rows':453.6,'hc_t_12_rows':544.32},open=['Bind actual full NT RTL hierarchy/source and physical masters (FS_YSHIFT=1,LOCAL_SPLIT=1)','CTNL,CTPL,return-column,collective,reset,tid and every first/last anchor join','Actual per-master routed native views; CTFL and CTFXS still fail old native gates','No source/view inheritance, no static calendar or end-to-end token release claim','Full parent pin registry/clock compensation/cut/route and outer C5 rescreen'])
 (out/'placement.json').write_text(json.dumps(d,indent=2)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(9,13))
 for i,r in enumerate(instances):
  y=H-r['y_from_N']-r['h'];ax.add_patch(plt.Rectangle((r['x'],y),r['w'],r['h'],fill=True,alpha=.18,edgecolor='black',facecolor=plt.cm.tab20(i%20)));ax.text(r['x']+r['w']/2,y+r['h']/2,r['name'].replace('ctnl','NL').replace('ctpl','PL'),ha='center',va='center',fontsize=7)
 ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um from S');ax.set_title('Literal v25 NT parent candidate 576.72 x 835.92 um\n0 overlaps; partial pin joins only; all native/parent adoption OPEN');fig.savefig(out/'placement.png',dpi=180)
 print(json.dumps({'outline':d['outline_um'],'instances':len(instances),'overlaps':0,'pin_joins':[(r['name'],r['bits'],r['over500'],r['max_um']) for r in joins]}))
if __name__=='__main__':main()
