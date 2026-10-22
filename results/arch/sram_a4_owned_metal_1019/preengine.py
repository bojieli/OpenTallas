import gzip,json,copy
from pathlib import Path
from graph import connected
P=Path(__file__).resolve().parent;i=json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes()));out={}
for fam,f in i['families'].items():
 r=connected(f['actual_boxes'],f['vias'],f['ports']);assert all(x['components']==1 for x in r.values())
 # Remove the actual V3 bridge while retaining all metal: M1/M2/M3 island becomes disconnected.
 target=next(v for v in f['vias'] if v['name']=='VIA34');vs=[v for v in f['vias'] if v['identity']!=target['identity']]
 bad=connected(f['actual_boxes'],vs,f['ports']);assert bad[target['net']]['components']==2
 out[fam]={'nominal':r,'missing_VIA34_bridge':{'removed_identity':target['identity'],'actual_components':bad[target['net']]['components'],'whole_graph_refuses':True}}
(P/'preengine_graph.json').write_text(json.dumps(out,indent=2)+'\n');print('independent whole source geometry graph: all signal and supply components connected; missing actual V3 bridge disconnects')
