#!/usr/bin/env python3
"""HEAD spine core strip plus four ribbon shims, retaining external tile pins.

RAW candidate only. Existing internal station registers are transferred into
shim FT chains, preserving every steady-state payload latency. New shims must
share the old spine clock region; CA/START and clocks must be re-composed.
"""
import argparse,copy,json,gzip
from pathlib import Path
from head_channel_resize_delta import shift_type, r3

X0,X1=699.84,1287.36
PAD=17.28


def spine_channels(root,ox,oy):
 return [dict(name=f'hk4_free_{root}_{side}_{band}',
              rect_um=[r3(ox+x0),r3(oy+y0),r3(ox+x1),r3(oy+y1)],
              reason='HEAD spine strip freed whitespace: PG/filler/decap and top-owned die clock cells; no signal standard cells (12.1d,12.2a)')
         for side,x0,x1 in [('w',0,X0),('e',X1,1382.4)]
         for band,y0,y1 in [('mid',682.56,1036.8),('north',1719.36,2073.6)]]

def run(raw):
 p=copy.deepcopy(raw);types=p['partition_types'];report={'status':'RAW_RECOMPOSE_REQUIRED','data_cycles_added':0,'types':{},'parts':[]}
 regions={q['name']:q['name'] for q in p['partitions']}
 assert 'landing_network' not in p.get('clock',{}),'strip derived landing infrastructure before recut'
 # Two reused FT masters; mirrors choose transfer direction without new types.
 for side,width,stages in [('w',X0,2),('e',1382.4-X1,1)]:
  types['hd_spn_'+side+'shim']={'module':'ot_s81hd_spn_'+side+'shim','outline_um':[r3(width),682.56],
   'hard':False,'cells':(565+1)*stages,'contents':[],
   'clock':{'tap_um':[r3(width/2),341.28],'layer':'M9','insertion_ps':450,'insertion_ff_ps':380,'tap_mode':'density','tap_radius_um':250},
   'reset':{'sync_stages':2},'buses':[],
   'ft_slots':[{'name':'link','in_face':'W','out_face':'E','width':565,'stations':stages,
                'in_window_um':[354.24,654.272],'out_window_um':[354.24,654.272],
                'layers':['M4','M6'],'order':'lsb_low'}],
   'note':'Existing spine horizontal station registers transferred into ribbon; no added data cycles.'}
 for tn in ('hd_spn','hd_spn_end'):
  t=types[tn];W,H=t['outline_um'];assert W==1382.4
  assert not t['clock'].get('landing_contract'),'input must be pre-compose raw plan'
  nt,*_=shift_type(t,[X0,0,X1,H]);nt['module']=t['module']+'_strip'
  nt['cells']=max(0,t.get('cells',0)-3396)  # 566 bits x (2+2+1+1) stages moved into shims
  for c in nt.get('contents',[]):c['origin_um'][0]=r3(c['origin_um'][0]-X0)
  # Preserve the source core path depth by assigning removed IS stages to the
  # two west or one east shim stages. Boundary flops already exist in wrappers.
  adjusted={}
  buses={b['name']:b for b in nt['buses']}
  for st in nt.get('internal_stations',[]):
   bus=st['conn'][4:];oldn=len(st['regs_um']);removed=2 if bus in ('xw_o','bw_i') else 1 if bus in ('xe_o','be_i') else 0
   n=oldn-removed;assert n>=0
   leaf=[r3(st['leaf_um'][0]-X0),st['leaf_um'][1]];st['leaf_um']=leaf
   b=buses[bus];face=b['face'];a=sum(b['window_um'])/2
   pin={'W':[0,a],'E':[X1-X0,a],'N':[a,H],'S':[a,0]}[face]
   frm,to=(pin,leaf) if b['dir']=='in' else (leaf,pin)
   # Manhattan walk with horizontal first; all count-preserving stages remain
   # in the strip. Per-bit placement uses leaf_um and each actual pin.
   L=abs(to[0]-frm[0])+abs(to[1]-frm[1]);regs=[]
   for k in range(n):
    d=L*(k+1)/(n+1);dx=min(d,abs(to[0]-frm[0]));dy=max(0,d-abs(to[0]-frm[0]))
    regs.append([r3(frm[0]+(dx if to[0]>=frm[0] else -dx)),r3(frm[1]+(dy if to[1]>=frm[1] else -dy))])
   st.update(from_um=frm,to_um=to,regs_um=regs)
   adjusted[bus]={'old_internal':oldn,'root_internal':n,'shim_stations':removed,'boundary_flops':1,
                  'new_total':n+removed+1,'old_total':oldn+1}
  types[tn]=nt
  p['reset'].get('in_sites',{}).pop(tn,None)
  report['types'][tn]={'old_outline_um':[W,H],'core_outline_um':nt['outline_um'],'paths':adjusted}
 oldparts=list(p['partitions']);extra=[];extra_ports=[]
 for q in oldparts:
  if q['type'] not in ('hd_spn','hd_spn_end'):continue
  assert q.get('orient','R0')=='R0','current HEAD spines are R0; no silent mirror assumptions'
  ox,oy=q['origin_um'];q['origin_um']=[r3(ox+X0),oy];root=q['name']
  # The four spaces between the input/output ribbons are top-owned clock/PG
  # channels. Strip/ribbon outlines retain their exact data interfaces.
  p['die'].setdefault('channels',[]).extend(spine_channels(root,ox,oy))
  for bus,side,direction in [('xw_o','w','out'),('bw_i','w','in'),('xe_o','e','out'),('be_i','e','in')]:
   name=root+'_'+bus+'_shim';x=ox if side=='w' else ox+X1
   y=oy+(1036.8 if direction=='out' else 0.0)  # extend S for measured reset reach; data windows unchanged
   orient='MY' if (side=='w' and direction=='out') or (side=='e' and direction=='in') else 'R0'
   extra.append({'name':name,'type':'hd_spn_'+side+'shim','origin_um':[r3(x),r3(y)],'orient':orient})
   regions[name]=regions[root]
   for port in p['ports']:
    end=port['src' if direction=='out' else 'dst']
    if end['part']==root and end['bus']==bus:
     end.update(part=name,bus='link_o' if direction=='out' else 'link_i')
     owners=[ln for ln in p['lanes'] if port['id'] in ln['ports']]
     assert len(owners)==1,(port['id'],'lane ownership',len(owners))
     ln=owners[0];at=ln['ports'].index(port['id'])+(1 if direction=='in' else 0)
     ln['ports'].insert(at,root+'_'+bus+'_strip_link')
   extra_ports.append({'id':root+'_'+bus+'_strip_link','src':{'part':root,'bus':bus} if direction=='out' else {'part':name,'bus':'link_o'},
                       'dst':{'part':name,'bus':'link_i'} if direction=='out' else {'part':root,'bus':bus},'width':565,'kind':'data'})
   report['parts'].append({'name':name,'clock_region':root,'origin_um':[r3(x),r3(y)],'orient':orient})
 p['partitions'].extend(extra);p['ports'].extend(extra_ports)
 report['parts_added']=len(extra)
 report['required']=['same-region shims per part_region map','CA compose on new endpoint map','reset/START release offsets','die clock provider and GRT/STA']
 return p,report,{'part_region':regions}


def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('--out',required=True);a.add_argument('--report',required=True);a.add_argument('--regions',required=True);a=a.parse_args()
 op=gzip.open if a.plan.endswith('.gz') else open
 with op(a.plan,'rt') as f:p=json.load(f)
 p,r,m=run(p);Path(a.out).write_text(json.dumps(p,indent=1));Path(a.report).write_text(json.dumps(r,indent=1));Path(a.regions).write_text(json.dumps(m,indent=1));print(json.dumps(r))
if __name__=='__main__':main()
