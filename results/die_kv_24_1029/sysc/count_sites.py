"""Apply only declared actual-bind SYS_C count-strap sites; no ABI or cycle change."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
import gen_phys as G

def apply(raw,manifest):
 t=raw['partition_types']['kv3_sys_c'];p=S.Plan(raw); w,h=t['outline_um'];spec=manifest['types']['kv3_sys_c']; cs=t['count_straps']
 assert {x['name']:x['width'] for x in cs}=={k:v['width'] for k,v in spec.items() if v['kind']=='count_strap'}
 edges={x['port']:x['tap_um'] for x in t['clock']['edge_clocks']}; lc={x['name']:x['xy_um'] for x in t['clock']['landing_contract']['pins']}; used=set(); rows=[]
 def snap(v,ln,pg=False):
  l=p.layers[ln]; k=round((v-l['offset_um'])/l['pitch_um'])
  for radius in range(200):
   for j in ([k] if not radius else [k-radius,k+radius]):
    q=round(l['offset_um']+j*l['pitch_um'],6)
    if not pg or not any(S.pg_blocked(ln,q-a) for a in (0.,G.CORE_MARGIN_UM)):return q
  raise ValueError('no legal track')
 for sp in cs:
  n=sp['name'];width=sp['width']; assert n in spec
  if n.startswith('strap_ca_k_'):anchor=edges['fclk_in_'+n[len('strap_ca_k_'):]]; y0=anchor[1]+2.0
  else:
   assert n in ('strap_ca_pad','strap_ca_efall');anchor=lc['cland_tstart_in'];y0=anchor[1]+(10 if n.endswith('_pad') else 12)
  x=snap(12 if anchor[0]<w/2 else w-12,'M5',True);xy=[]
  for b in range(width):
   y=snap(y0+b*.864,'M4');q=(x,y);assert q not in used;used.add(q)
   assert 1<x<w-1 and 1<y<h-1
   for c in t.get('contents',[]):
    a,z=c['origin_um'];cw,ch=c['outline_um'];assert not (a-1<=x<=a+cw+1 and z-1<=y<=z+ch+1),(n,c['inst'])
   xy.append([x,y]);rows.append(dict(port=n,bit=b,layer='M5',xy_um=[x,y],anchor_um=anchor))
  sp['layer']='M5';sp['sites_um']=xy
 assert len(rows)==140
 assert len(G.strap_pin_sites(S.Plan(raw),'kv3_sys_c'))==140
 return raw,dict(form='sys_c_actual_bind7_countstrap_sites',ports=len(cs),bits=len(rows),rows=rows,cycles_added=0,ABI_change=False,basis='Existing declared count_straps exactly match actual bind_parent_id_straps; M5 PG-free vertical track / M4 cross-track; 0.864um bit spacing; clear macro bodies +1um')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('manifest');ap.add_argument('out');ap.add_argument('receipt');a=ap.parse_args();d,r=apply(json.load(open(a.plan)),json.load(open(a.manifest)));Path(a.out).write_text(json.dumps(d,indent=1));Path(a.receipt).write_text(json.dumps(r,indent=1));print('25declaredports/140sites; strap_pin_sites140; noABI/cycles')
