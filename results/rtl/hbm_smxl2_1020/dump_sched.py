import sys, json, os
from pathlib import Path
W=Path(sys.argv[1]); sys.path.insert(0,str(W/'tools/hbm_layer_vehicle'))
import toksim_smhbm as T
S=T.S
fix=W/'results/rtl/hbm_ds_layer_tput_1018/fixtures'
c=S.compile_all(fix, Path('smw'), S.parse_layers(sys.argv[2]), os.environ.get('SMB_MUT',''))
out=[]
for k in c['kinds']:
  for b in c['descs'][k['d0']:k['d1']]:
    out.append(dict(kind=k['name'],rc0=k['rc0'],d=b['desc_i'],k=b['k'],landing=b['landing'],nl=b['n_lines'],nw=b['nwords'],go=b['go_at'],go_abs=k['rc0']+b['go_at'],rm=b.get('res_model')))
json.dump(dict(blocks=out,events=None),open(sys.argv[3],'w'),indent=0)
print(len(out), c['budget']['per_kind'][0]['ids_at_rc'])
