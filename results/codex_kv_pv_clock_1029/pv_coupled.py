import sys,json,collections,functools
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029');sys.path.insert(0,str(p/'named_source/tools/die_plan'))
import core_family_slice as C
C.ENV+=['BUFx6f_ASAP7_75t_R','BUFx4f_ASAP7_75t_R','BUFx3_ASAP7_75t_R','BUFx2_ASAP7_75t_R']
# Pure geometry cache: identical exact point tuples, unchanged shared MST implementation/results.
origmst=C.H.mst_edges
@functools.lru_cache(maxsize=None)
def fixedmst(pts):return origmst(pts)
C.H.mst_edges=lambda pts:fixedmst(tuple(tuple(x)for x in pts))
origkey=C.lattice_levelkey
active=None
def key(n):
 k=origkey(n)
 if n[4]=='leaf':
  ls=active['leafsinks'][n[0]]
  return k+('macro' if all(s[4].startswith('MACRO:')for s in ls)else 'register',)
 return k
C.lattice_levelkey=key
sizing={}
def coupled(P,libs,r,c,wc,**kw):
 global active
 active=P
 sizing.update(C.lattice_masters(P,libs,r,c,slew_max=60.,passes=3))
 return collections.Counter((n[4],n[3])for n in P['nodes'])
C.M7.size_d1=coupled
fam=json.load(open(p/'pv_family_named.json'))['families'][0];fam=dict(fam,name='pv_macro_local_coupled_calibration')
out=p/'named_coupled/kv3_pv_pair';out.mkdir(parents=True,exist_ok=True)
geo=p/'named_plan/kv3_pv_pair/geo.txt'
rec=C.plan(geo,fam,str(p/'invbuf_tt.lib'),str(p/'invbuf_ff.lib'),'kv3_pv_pair')
rec['calibration']=dict(scope='PLAN ONLY; outside default master envelope requires root review before prototype',source='850 sourceclockAPI unchanged; exact actual29770FF+8SRAM',group_rule='same master per fixed macro/register load class and tree level; no measured tap offsets',objective='existing lattice_masters TTwindow+FFwindow')
P,libs,r,c,wc=C._PLANS['kv3_pv_pair'];full={}
for corner in ['TT','FF']:
 I=P['_int'][corner];masters={n[0]:n[3]for n in P['nodes']};v=[]
 for u,(ct,ch)in I['drv'].items():
  L=libs[corner][masters[u]];sl=I['slew'][u]
  v.extend([C.H.interp(L['trise'],sl,ct),C.H.interp(L['tfall'],sl,ct)])
 full[corner]=dict(max_input_slew=max(I['slew'].values()),max_output_rise_fall_slew=max(v),verdict='PASS'if max(v+list(I['slew'].values()))<=80 else'FAIL')
rec['all_driver_slew']=full;rec['coupled_level_masters']={str(k):v for k,v in sizing.items()}
ck=C.checks(rec,None,geo)
for corner,v in full.items():
 if v['verdict']!='PASS':ck['fails'].append(corner+' all-driver slew>80');ck['verdict']='FAIL'
(out/'plan.json').write_text(json.dumps([rec],indent=1)+'\n');(out/'checks.json').write_text(json.dumps(ck,indent=1)+'\n');C.render(geo,rec,None,out/'plan.png')
print('PV_COUPLED_CALIBRATION',json.dumps(dict(TT=rec['TT'],FF=rec['FF'],checks=ck,all_driver_slew=full,cache=str(fixedmst.cache_info()))))
