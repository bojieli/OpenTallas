#!/usr/bin/env python3
"""Construct native hrow TD placement from real child LEFs and actual relay CTS pins.

Diagnostic candidate only: no parent closure, assigned boundary pins, reset tree,
or adopted die clock source is inferred. Every serialized hop is checked per bit.
"""
import argparse, hashlib, importlib.util, json, re, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pin_align as PA
OUT=ROOT/'results/arch/s81_hrow_native_placement_1013'
W,H=2998.08,1769.04
CHILDREN={'dsfd_mtp_hrow_ing':'hrow5_ing','dsfd_mtp_hrow_hub':'hrow5_hub','dsfd_mtp_hrow_cbe':'hrow5_cbe_cx','dsfd_mtp_hrow_cbw':'hrow5_cbw_cx'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def masters():
 out={}
 for m,k in CHILDREN.items():
  p=ROOT/'physical/ref_tile'/k/'views'/m/(m+'.lef');t=p.read_text();sz=re.search(r'SIZE\s+(\S+) BY (\S+)',t);ps={}
  for n,b in re.findall(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1',t,re.S):
   r=re.search(r'LAYER (\S+) ;\s*RECT\s+([^;]+);',b)
   if r:
    x0,y0,x1,y1=map(float,r[2].split());ps[n]=((x0+x1)/2,(y0+y1)/2,r[1])
  out[m]=dict(w=float(sz[1]),h=float(sz[2]),pins=ps,evidence=str(p.relative_to(ROOT)),sha256=digest(p),kind='closed_child_lef')
 for m in ['dsfd_hrow_r2079','dsfd_hrow_r1025','dsfd_hrow_r23','dsfd_hrow_r15','dsfd_die_rstsync']:
  p=OUT/'pins'/m/'pins.json';d=json.loads(p.read_text());ps={}
  for n,v in d['pins'].items():
   b=v['boxes'][0];x0,y0,x1,y1=b['rect_um'];ps[n]=((x0+x1)/2,(y0+y1)/2,b['layer'])
  out[m]=dict(w=d['outline_um'][0],h=d['outline_um'][1],pins=ps,evidence=str(p.relative_to(ROOT)),sha256=digest(p),odb_sha256=d['odb_sha256'],kind='actual_cts_pins_route_pending')
 return out
MP=masters()
def vec(p,n,base=0):return [f'{p}[{k}]' for k in range(base,base+n)]
class Plan:
 def __init__(self):self.inst={};self.edges=[];self.hops=[];self.build()
 def add(self,n,m,x,y,o='R0'):
  self.inst[n]=dict(master=m,x=round(x/2.16)*2.16,y=round(y/2.16)*2.16,orient=o)
 def pin(self,n,p):
  z=self.inst[n];a=MP[z['master']];x,y,l=a['pins'][p];w,h=a['w'],a['h'];o=z['orient']
  x,y={'R0':(x,y),'MX':(x,h-y),'MY':(w-x,y),'R180':(w-x,h-y),'R90':(h-y,x),'R270':(y,w-x)}[o]
  face=min([(x,'W'),(y,'S'),((h if o in ('R90','R270') else w)-x,'E'),((w if o in ('R90','R270') else h)-y,'N')])[1]
  return (x+z['x'],y+z['y'],face,l)
 def edge(self,c,a,pa,b,pb):
  assert len(pa)==len(pb)
  self.edges.append(dict(cls=c,source=a,source_pins=pa,sink=b,sink_pins=pb))
 def build(self):
  self.add('u_hub','dsfd_mtp_hrow_hub',1522.8,1252.8)
  self.add('g_hrst/u_rs','dsfd_die_rstsync',1488.24,1488.24)
  for p in range(3):
   n=f'g_part[{p}]';hi=1036.8;lo=172.8;px=43.2+p*963.36
   self.add(n+'/u_ig','dsfd_mtp_hrow_ing',px+172.8,hi+226.8,'R90')
   for k in range(10):
    east=k<5;j=k if east else 9-k
    self.add(n+f'/g_c[{k}]/'+('g_e' if east else 'g_w')+'/u_b','dsfd_mtp_hrow_'+('cbe' if east else 'cbw'),px if east else px+475.2,hi-j*216 if east else hi-j*216,'MY' if k==5 else 'R0')
   self.add(n+'/g_hut/g_r[0]/u_r','dsfd_hrow_r2079',px+414.72,43.2,'MX')
   # Initial return/event/control chains interpolate pin centroids; exact checks below retain failures.
   for kind,count,ma in [('g_hrp/g_r',2,'dsfd_hrow_r1025'),('g_hev/g_ev',2,'dsfd_hrow_r23'),('g_hev/g_rc',3,'dsfd_hrow_r15')]:
    for k in range(count):self.add(n+f'/{kind}[{k}]/u_r',ma,300,300)
   bn=lambda k:n+f'/g_c[{k}]/'+('g_e' if k<5 else 'g_w')+'/u_b'
   self.edge('ing_write',n+'/u_ig',vec('t_wc',1039),bn(0),vec('f_w',1039))
   for k in range(9):
    if k==4:
     r=n+'/g_hut/g_r[0]/u_r'
     for src,dst,bits,off in [('w','w',1039,0),('r','r',15,1039),('d','d',1025,1054)]:
      self.edge('uturn_in',bn(4),vec('t_'+src,bits),r,vec('i',bits,off));self.edge('uturn_out',r,vec('o',bits,off),bn(5),vec('f_'+dst,bits))
    else:
     for bus,bits in [('w',1039),('r',15),('d',1025)]:self.edge('bank_chain',bn(k),vec('t_'+bus,bits),bn(k+1),vec('f_'+bus,bits))
   def chain(cls,a,pa,b,pb,names,ma):
    A=np.mean([self.pin(a,q)[:2] for q in pa],axis=0);B=np.mean([self.pin(b,q)[:2] for q in pb],axis=0)
    for k,r in enumerate(names):
     t=(k+1)/(len(names)+1);v=A+(B-A)*t;self.add(r,ma,v[0]-MP[ma]['w']/2,v[1]-MP[ma]['h']/2)
    self.edge(cls,a,pa,names[0],vec('i',len(pa)))
    for q,r in zip(names,names[1:]):self.edge(cls,q,vec('o',len(pa)),r,vec('i',len(pa)))
    self.edge(cls,names[-1],vec('o',len(pa)),b,pb)
   chain('return',bn(9),vec('t_d',1025),'u_hub',vec(f'f_pr{p}',1025),[n+f'/g_hrp/g_r[{k}]/u_r' for k in range(2)],'dsfd_hrow_r1025')
   chain('event',n+'/u_ig',vec('t_ev',21)+vec('t_flt',2),'u_hub',vec(f'f_ev{p}',21)+vec(f'f_if{p}',2),[n+f'/g_hev/g_ev[{k}]/u_r' for k in range(2)],'dsfd_hrow_r23')
   chain('read_control','u_hub',vec(f't_rc{p}',15),bn(0),vec('f_r',15),[n+f'/g_hev/g_rc[{k}]/u_r' for k in range(3)],'dsfd_hrow_r15')
  for n,z in self.inst.items():
   if z['master'].startswith('dsfd_hrow_r'):self.edge('reset_direct_rtl','g_hrst/u_rs',['rn'],n,['rn'])
 def rects(self):
  out={}
  for n,z in self.inst.items():
   m=z['master'];a=MP[m];w,h=(a['h'],a['w']) if z['orient'] in ('R90','R270') else (a['w'],a['h']);out[n]=(z['x'],z['y'],z['x']+w,z['y']+h,m)
  return out
 def evaluate(self):
  self.hops=[];rows={};bad=[];rs=self.rects()
  for n,(x,y,xx,yy,m) in rs.items():
   if x<0 or y<0 or xx>W+1e-6 or yy>H+1e-6:bad.append('outside '+n)
  ns=list(rs)
  for i,a in enumerate(ns):
   for b in ns[i+1:]:
    A,B=rs[a],rs[b]
    if min(A[2],B[2])-max(A[0],B[0])>1e-6 and min(A[3],B[3])-max(A[1],B[1])>1e-6:bad.append('overlap '+a+' / '+b)
  for e in self.edges:
   A=[self.pin(e['source'],q) for q in e['source_pins']];B=[self.pin(e['sink'],q) for q in e['sink_pins']];ds=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(A,B)];k=int(np.argmax(ds));r=dict(cls=e['cls'],source=e['source'],sink=e['sink'],bits=len(ds),max_um=round(ds[k],3),over_500=sum(x>500 for x in ds),worst_source_pin=e['source_pins'][k],worst_sink_pin=e['sink_pins'][k]);rows.setdefault(e['cls'],[]).append(r);r['pin_alignment']=PA.bundle(A,B);self.hops.append((e['cls'],e['source'],e['sink'],A,B))
  return bad,rows
 def cut_check(self):
  # Same explicit grid/capacity and three-pass L/Z search as the FE checker.
  spec=importlib.util.spec_from_file_location('fe',ROOT/'tools/s81_ph/s81_ph_vm_fe_h_floorplan.py');fe=importlib.util.module_from_spec(spec);spec.loader.exec_module(fe);fe.W,fe.H=W,H
  return fe.Plan.check_cuts(self)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--placements',type=Path);ap.add_argument('--cuts',action='store_true');a=ap.parse_args();p=Plan()
 if a.placements:
  for n,z in json.loads(a.placements.read_text())['instances'].items():p.inst[n].update(z)
 bad,rows=p.evaluate();cuts=p.cut_check() if a.cuts else None
 source=ROOT/'rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_die.sv'
 graph={'clock':dict(source_port='ck',drivers=[],sinks=[dict(instance=n,pin='ck',point_um=list(p.pin(n,'ck')[:2])) for n in p.inst],rtl_net='ck',physical_source_binding=None,status='No adopted native die clock/reset ABI; source ck is a real RTL port, physical driver not assigned'), 'asynchronous_reset':dict(source_port='rst',sinks=[dict(instance=n,pin='rst',point_um=list(p.pin(n,'rst')[:2])) for n,z in p.inst.items() if 'rst' in MP[z['master']]['pins']]),'relay_reset':dict(driver='g_hrst/u_rs.rn',sinks=[n+'.rn' for n,z in p.inst.items() if z['master'].startswith('dsfd_hrow_r')],buffer_tree=None)}
 res=dict(schema='opentallas.s81_hrow_native_candidate.v1',outline_um=[W,H],rtl_source=str(source.relative_to(ROOT)),rtl_sha256=digest(source),relay_rtl_sha256=digest(ROOT/'rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv'),parameters=dict(HARD_RELAYS=1,CQ=3,WK=7,P=2,UT=1),relay_bits=12660,reset_sync_bits=2,instances=p.inst,masters={m:{k:v for k,v in z.items() if k!='pins'} for m,z in MP.items()},placement_violations=bad,hops=rows,cuts=cuts,clock_reset_graph=graph,unmodelled=['Assigned parent boundary pins and external hops','Physical die clock source, insertion, phase and skew','Physical reset driver and buffer-tree placement','Final routed relay LEFs and SS/FF clock timing','Constant f_pid/f_bid and cd[0] tie-cell placements'],pass_=False,cut_scope='64-bit centroid L/Z routing heuristic on 10.8um grid; full and local54um windows. No M8 capacity. Exact bit pin lengths checked separately.',status='OPEN diagnostic candidate; no parent closure or valid physical clock graph claimed')
 res['pass']=res.pop('pass_')
 bench=ROOT/'rtl/dsrom_sys/mtp/tb_mtp_hrow.sv'
 res['clock_reset_graph']['bench_only_source']=dict(path=str(bench.relative_to(ROOT)),sha256=digest(bench),instance='u_st',clock_connection='ck(clk)',reset_connection='rst(rst_n)',clock_generator='always #0.5 clk = ~clk',period_ns=1.0,production_binding=False)
 res['internal_data_geometry_pass']=not bad and not any(r['over_500'] for c,vs in rows.items() if c!='reset_direct_rtl' for r in vs)
 contract=Path('/home/ubuntu/wt/el1011-s81dieit/physical/s81_die_pins/v18/contract_trial.json')
 if contract.exists():res['contract_evidence']=dict(path='physical/s81_die_pins/v18/contract_trial.json',source_tree='/home/ubuntu/wt/el1011-s81dieit',sha256=digest(contract),status='Trial representative hrow slot; physical die origin and native clock/reset ABI not adopted')
 OUT.mkdir(parents=True,exist_ok=True);previous=OUT/'candidate.json'
 if previous.exists():
  history=OUT/'history';history.mkdir(exist_ok=True);(history/(digest(previous)+'.json')).write_bytes(previous.read_bytes())
 previous.write_text(json.dumps(res,indent=1)+'\n')
 print(json.dumps(dict(instances=len(p.inst),placement_violations=bad,hop_max={c:round(max(r['max_um'] for r in rs),3) for c,rs in rows.items()},cuts=cuts),indent=1))
if __name__=='__main__':main()
