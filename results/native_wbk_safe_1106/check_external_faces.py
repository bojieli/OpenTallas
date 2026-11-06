import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import face_guard as F
root=Path.cwd();results={}
for name,top,held in [('old','ot_wbq_sw_split_out',()),('new','ot_wbq_sw_split_out__elastic_native',('w_k_addr','w_k_wdata'))]:
 r=F.guard((root/(name+'.v')).read_text(),top=top,
     skip_re=r'^(hbm_clk|hbm_rst_n|in_v|in_ready|in_addr|in_data)$',hold_outputs=held)
 (root/(name+'.external_faces.json')).write_text(json.dumps(r,indent=1)+'\n')
 print('EXTERNAL_FACES',name,r['verdict'],r['checked'],r['ok'],r['fail_counts'])
 assert r['verdict']=='PASS',r['fails']
 results[name]=dict(verdict=r['verdict'],checked=r['checked'],ok=r['ok'],registered_hold_bits=r.get('registered_hold_bits',0))
print(json.dumps(dict(external_only=results,native_seam_context='NOT_QUALIFIED_IN_THIS_COMPONENT_CHECK',physical_STA='NOT_RUN'),indent=1))
