#!/usr/bin/env python3
"""Actual-view RP4 clock/rectangle candidate. No pin, cut or route qualification."""
import hashlib,json,os,pathlib,re,subprocess,sys
os.environ['SMH_RP']='rp3'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent));import geom as G;from repack import draw,stats
ROOT=pathlib.Path(__file__).resolve().parents[2]
def bind(view):
 p=ROOT/view;files={}
 for n in [p.name+'.lef',p.name+'_tt.lib',p.name+'_ff.lib',p.name+'_ss.lib','insertion.json']:
  f=p/n
  blob=subprocess.check_output(['git','rev-parse','HEAD:'+str(f.relative_to(ROOT))],cwd=ROOT,text=True).strip()
  actual=subprocess.check_output(['git','hash-object',str(f)],cwd=ROOT,text=True).strip()
  if actual!=blob:raise RuntimeError('Stale working input '+str(f))
  files[n]={'git_blob':blob,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',(p/(p.name+'.lef')).read_text())
 return dict(view=view,outline_um=[float(m[1]),float(m[2])],files=files)
def main():
 out=ROOT/'results/arch/hbm_sm_repack_1015/rp4_clock_candidate';out.mkdir(parents=True,exist_ok=True)
 views={k:bind(v) for k,v in G.VIEWS.items()}
 for n in ['row_w','row_e']:views[n]=bind(f'physical/ref_tile/smh_tr_group_{n}_ref/views/ot_smh_tr_group_{n}')
 boxes=[];hard=[]
 mapping={'xs':0,'bdc':1}
 for k,inst,x,y,w,h,orient in G.children():
  if k in ['beat','land']:continue
  j=0 if 'g_lf?0?' in inst else 1
  if j==0:y+=129.6
  name=inst.replace('*g_lf?0?','u.g_lf[0]').replace('*g_lf?1?','u.g_lf[1]')
  off=mapping.get(k,4 if k=='tct' else (2 if 'u_h0' in inst else 3));entry=j*5+off
  hard.append(dict(kind=k,inst=name,at_um=[x,y],outline_um=[w,h],orient=orient,clock_port=f'clk_hard[{entry}]',view=views[k]['view']))
  boxes.append((k,f'{j}:{k} clk{entry}',x,y,w,h))
 placements=[('row_w','u.u_ptw.u_row0',25.92,604.8,10),('row_w','u.u_ptw.u_row1',25.92,492.48,11),
  ('row_e','u.u_pte.u_row0',133.92,604.8,12),('row_e','u.u_pte.u_row1',133.92,492.48,13),
  ('beat','u.u_ptw.u_beat_t',267.84,492.48,14),('land','u.u_ptw.u_land_n',25.92,781.92,15),
  ('land','u.u_ptw.u_land_s',25.92,717.12,16),('beat','u.u_pte.u_beat',336.96,492.48,17)]
 for k,n,x,y,i in placements:
  w,h=views[k]['outline_um'];ori='MX' if i==16 else 'R0'
  hard.append(dict(kind=k,inst=n,at_um=[x,y],outline_um=[w,h],orient=ori,clock_port=f'clk_hard[{i}]',view=views[k]['view']))
  boxes.append((k,n.split('.')[-1]+f' clk{i}',x,y,w,h))
 st=stats(406.08,1321.92,boxes)
 if st['overlaps'] or st['slivers_um']:raise RuntimeError(st)
 rec=dict(schema='opentallas.sm_rp4_clock_plan.v1',scope='matvec-body clock and rectangle candidate; attention integration, ports/cuts/routes remain open',
  outline_um=[406.08,1321.92],delta_outline_um=[0,129.6],same_data_edges=True,normal_edges_added=0,
  actual_existing_closed_views=views,children=sorted(hard,key=lambda x:int(x['clock_port'].split('[')[1][:-1])),geometry=st,
  own_soft_entries={'clk_pin[0]':818,'clk_pin[1]':818,'clk_pin[2]':2069,'clk_oper[0]':'leaf0 XB subset of1670','clk_oper[1]':'leaf0 XF subset of1670','clk_oper[2]':'leaf1 XB subset of1670','clk_oper[3]':'leaf1 XF subset of1670','clk_region[0]':'north gather/strap/reset','clk_region[1]':'middle gather/strap/reset','clk_region[2]':'south gather/strap/reset'},
  original_actual_postDPL_FF=14486,actual_row_FF_moved_to_four_closed_children=6556,remaining_parent_FF_before_gating_companion=7930,
  clock_entry_count=28,old_clock_entry_count=1,clock_pin_delta=27,gating='actual28ot_cg_tile instances in separate die-level distributor; no free-running fallback; exactFF/area and dieCTS still unmeasured',
  removed_parent_ports=['cgi','cgo'],wake='cgi/cgo terminate on actual die-level clock distributor, not hidden in a hard-child entry',
  open=['assigned die clock/data pin files','actual818bit port-to-port path graph','all channel cuts <=0.60 and all incident routes','child clock phase delivery at phi-R','native own-root CTS/TT/FF/DRC','attention PV/wave/prob/BE integration','fullSM physical fit and measured throughput','MTP K2 service and SRAM integration'])
 (out/'plan.json').write_text(json.dumps(rec,indent=2)+'\n')
 draw(out/'rp4_clock_candidate.png',406.08,1321.92,boxes,'RP4 candidate:18existing hard children +10local soft clocks; ports/cuts OPEN')
 print(json.dumps(st,indent=2))
if __name__=='__main__':main()
