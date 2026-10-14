import sys
from pathlib import Path
sys.path.insert(0,'tools')
import check_macro_track_alignment as C
import hbm_accel_die_fp as F
D=Path(__file__).parent
old=C.parse_lef((D/'hbm_link_endpoint_original.lef').read_text())[0]
new=C.parse_lef((D/'hbm_link_endpoint_repaired.lef').read_text())[0]
a=C.audit_macro(old,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)
b=C.audit_macro(new,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)
assert a['orientations']['M4']['MX']['joint_with_row']['legal_origins_mod_joint_nm']==[]
for ly,cs in b['orientations'].items():
 for o in ('R0','MX'):
  q=cs[o];j=q.get('joint_with_row',q.get('joint_with_site'))
  assert j['legal_origins_mod_joint_nm']
assert old['W']==new['W'] and new['H']-old['H']==520
assert [(p['name'],p['use']) for p in old['pins']]==[(p['name'],p['use']) for p in new['pins']]
for before,after in zip(old['pins'],new['pins']):
 ly,box=before['rects'][0]; nl,nbox=after['rects'][0]
 assert ly==nl
 if ly=='M4': assert box==nbox
 else: assert (box[2]-box[0],box[3]-box[1])==(nbox[2]-nbox[0],nbox[3]-nbox[1])
assert F.r25gq_v13()['link_ep_v2']['wh']==(2600.0,830.52)
assert F.r25gq_v12()['link_ep_v2']['wh']==(2600.0,830.0)
print('PASS actual endpointpinidentity, unchangedM4coords, requestedR0/MX lattice; originalMX mutant REJECTED; v12unchanged')
