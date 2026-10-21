"""Fail closed if a copied native view or bound source changes before the chain."""
from pathlib import Path
import hashlib,json,subprocess,sys
from functools import lru_cache
sys.path.insert(0,str(Path(__file__).resolve().parent))
from forward_clock_guard import validate_native_forwarding
case=Path(sys.argv[1]); mirror=sys.argv[2]
q=json.loads((case/'case.json').read_text()); assert q['port_bind_rc']==0
assert q['die_v_sha256']=='75b71038d3ffe04850816771d51899bac6453b49ad79661eb6340c677630a9f2'
ctrl=q['closed_views']['dsfd_ctrl_rg2']
assert ctrl=='12c132d60a8f0300056abb216d48ff9588e7f620:physical/ref_tile/s81ctrl_rg2_n32s/views/dsfd_ctrl_rg2',ctrl
@lru_cache(None)
def read(ref,path):
 return subprocess.run(['git','--git-dir='+mirror,'show',ref+':'+path],check=True,capture_output=True).stdout
rows=[]
for master,origin in sorted(q['closed_views'].items()):
 ref,d=origin.split(':',1)
 if not (master.startswith('dsfd_dvrly') or master=='dsfd_ctrl_rg2'): continue
 for corner in ('tt','ff','ss'):
  file=case/'views/sta'/f'{master}_{corner}.lib'
  data=file.read_bytes(); assert data==read(ref,f'{d}/{master}_{corner}.lib'),str(file)
  validate_native_forwarding(master,corner,data.decode(),lambda name:read(ref,d+'/'+name))
  rows.append({'master':master,'corner':corner,'source':origin,'sha256':hashlib.sha256(data).hexdigest()})
 assert (case/'views'/f'{master}.lib').read_bytes()==read(ref,f'{d}/{master}_tt.lib')
 assert (case/'views'/f'{master}.lef').read_bytes()==read(ref,f'{d}/{master}.lef')
assert len(rows)==45,len(rows)
(case/'source_master_guard.json').write_text(json.dumps({'verdict':'PASS','native_views':rows,'forwarding_corners':45,'CTRL_native_source':ctrl},indent=2)+'\n')
print('SOURCE_MASTER_GUARD PASS 45 native forwarding corners; CTRL n32s source fixed')
