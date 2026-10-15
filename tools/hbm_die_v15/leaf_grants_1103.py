#!/usr/bin/env python3
"""Typed grants for two source-exact independent leaves, no parent closure claim."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sha_at(ref,path):return hashlib.sha256(subprocess.run(['git','-C',str(ROOT),'show',ref+':'+path],capture_output=True,check=True).stdout).hexdigest()
def pins(faces,wh):
 out=[]
 for f,ps in faces.items():
  L=wh[0] if f in 'NS' else wh[1]
  used=sum(b for _,b in ps)*.096
  assert used/L <= .60
  cur=(L-used)/2
  for n,b in ps:
   span=.096*b
   out.append(dict(name=n+(f'[{b-1}:0]' if b>1 else ''),face=f,layer='M5' if f in 'NS' else 'M4',
                   offset=round(cur+span/2,6),span_um=[round(cur,6),round(cur+span,6)],offset_pending_view=True))
   cur+=span
 return out

def apply(h):
 keep=[s for s in h['slots'] if not s.get('leaf_grant_1103')]
 h['slots']=keep
 meta='rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv'
 writer='rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite.sv'
 plans=[('meta', 'hidx_meta_w25_d123_r0',meta,(51.84,51.84),dict(N=[('clk',1),('rst_n',1),('d',25)],S=[('q',25)]),'efb89a135'),
        ('writer','ot_hgi_coll_static_vmwrite',writer,(103.68,388.8),dict(W=[('rgx_v',4),('rgx_addr',160),('rgx_data',2048),('rgx_vm',1)],E=[('kq',2248),('launch_done',5),('fault',1)],S=[('tkw_v',1),('tkw_d',568)],N=[('clk',1),('rst_n',1),('sid',2),('ingress_slot',5),('slot_valid',8),('slot_owner',32)]),'HEAD')]
 hashes={role:sha_at(ref,src) for role,_,src,_,_,ref in plans}
 for par in keep[:]:
  nm=par['name']
  if nm in ('idx_s0','idx_s1','idx_s2','idx_s3'):
   role='meta';count=4
   qi=int(nm[-1]); par['instance']=f'hb_idx/index/parent/gscore[{qi}]/scorer'
  elif nm in ('coll_SW','coll_SE','coll_NW','coll_NE'):role='writer';count=1
  else:continue
  _,cell,src,wh,fs,ref=next(p for p in plans if p[0]==role)
  # These parents contain real M5/M6 hard children. The parent owns M7 PG,
  # die straps M8; signals stop at M6. No leaf layer rule is relaxed.
  par.update(kind='cluster',layer_rule='cluster',pg_layer='M7',strap_layer='M8',signal_max_layer='M6',layer_cap='M6',
             hierarchy_status='child leaf grants present; complete child placement/registered seams/clock/pin/cut proof OPEN')
  for k in range(count):
   if role=='meta':
    x,y,orient=2376.0+216*k,2894.4,'R0'
    inst=f'hb_idx/index/parent/gscore[{qi}]/scorer/ge[{k}]/md'
   else:
    vmface=next(p['face'] for p in par['pins'] if p['name'].startswith('vm_kq'))
    assert vmface in 'EW'
    x=21.6 if vmface=='W' else par['outline']['w']-wh[0]-21.6
    y=21.6;orient='MY' if vmface=='W' else 'R0'
    inst=par['instance']+'/u_q/u_writer'
   assert 0<=x and 0<=y and x+wh[0]<=par['outline']['w'] and y+wh[1]<=par['outline']['h']
   h['slots'].append(dict(name=f'{nm}_{role}{k}',cell=cell,source=src,source_sha256=hashes[role],source_prerequisite=ref,
      params={} if role=='meta' else dict(MUT=0),kind='tile',parent=nm,instance=inst,outline=dict(w=wh[0],h=wh[1]),
      origin=dict(x=round(x,6),y=y,orient=orient),clock_entry=dict(pin='clk',face='N',layer='M5'),
      clock_domain='stream',clock_period_ps=833.333333,pg_layer='M5',strap_layer='M6',signal_max_layer='M5',layer_cap='M5',layer_rule='tile',
      io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),pins=pins(fs,wh),version=2,leaf_grant_1103=True,
      qualification_scope='typed independent leaf slot; exact offsets adopted from final source-bound view; full parent and all incident registered relay/clock paths OPEN',
      reservation_basis=('four previously unassigned footer reservations in planned20x26 hslice array; source-exact512hslice+glue packing still required' if role=='meta' else 'registered VM writer at parent VM-facing edge; qslots/TKM/control placements and seams not yet qualified'),
      measured_std_um2=1033 if role=='meta' else 6730.9299,
      measured_ff=3075 if role=='meta' else 6264,
      logical_cycles=123 if role=='meta' else 'capture C, launch C+1/C+2 unchanged'))
 h['independent_leaf_grants_1103']=dict(masters=2,replicas=dict(hidx_meta_w25_d123_r0=16,ot_hgi_coll_static_vmwrite=4),
  scopes='source-exact independent components; no full parent fit/timing or current-die closure inherited',
  source_sha256=hashes)
 return h

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 h=apply(json.loads(args.input.read_text()));args.out.write_text(json.dumps(h,indent=1)+'\n')
 print(json.dumps(h['independent_leaf_grants_1103']))
