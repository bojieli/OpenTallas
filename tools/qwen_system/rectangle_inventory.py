"""Capture actual opt-in r21c rectangles before columns or relay mutation."""
import hashlib,json
from pathlib import Path
import die_top_lint as L
import qwen_rom_fulldie_b3r2 as B

class Captured(Exception): pass

def capture(v,m):
    rows=[dict(name=i.name,master=i.master,x=i.x,y=i.y,w=i.w,h=i.h,
        kind=i.kind,region=getattr(i,'region',None),domain=getattr(i,'domain',None))
        for i in m['insts']]
    r=dict(schema='opentallas.qwen-r21c-pre-relay-rectangles.v1',die=m['die'],
       rectangles=rows,regions=m['regions'],geometry=m['geo'],
       r21c=m.get('r21c'),embedding_columns_inserted=False,relay_plan_created=False,
       source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in [Path(B.__file__),Path(L.__file__),Path(B.F.__file__)]})
    Path('rectangle_inventory.json').write_text(json.dumps(r,indent=2)+'\n')
    print('PASS actual_selected_r21c_pre_column_pre_relay rectangles',len(rows))
    raise Captured()

r=dict(L.QWEN_RECIPES['r21c']);cdc=r.pop('cdc')
try: B.selected(True,cdc=B._cdc_arg(cdc),before_relays=capture,**r)
except Captured: pass
