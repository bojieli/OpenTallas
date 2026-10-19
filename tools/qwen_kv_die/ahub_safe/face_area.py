#!/usr/bin/env python3
import collections,json,sys
from pathlib import Path
old=json.loads(Path(sys.argv[1]).read_text());new=json.loads(Path(sys.argv[2]).read_text())
def census(j,top):
 m=j['modules'][top];cnt=collections.Counter(c['type']for c in m['cells'].values());areas={t:float(j['modules'][t]['attributes'].get('area',0))for t in cnt}
 return {'cells':dict(cnt),'standard_cell_area_um2':sum(cnt[t]*areas[t]for t in cnt if t not in ('ot_nhb_zh','ot_qkh_recip_leaf')),'area_by_master':areas,'flip_flops':sum(n for t,n in cnt.items()if t.startswith('DFF')),'hard_children':{t:cnt[t]for t in ('ot_nhb_zh','ot_qkh_recip_leaf')}}
a=census(old,'qkd_ahub_static_dw_safe_native');b=census(new,'qkd_ahub_static_dw_safe_native');print(json.dumps({'schema':'opentallas.ahub.face_area.v1','old':a,'new':b,'delta_standard_cell_area_um2':b['standard_cell_area_um2']-a['standard_cell_area_um2'],'delta_ff_clock_sinks':b['flip_flops']-a['flip_flops'],'physical_qualified':False},indent=2))
