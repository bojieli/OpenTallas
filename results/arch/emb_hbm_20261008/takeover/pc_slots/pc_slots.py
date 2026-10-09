import sys,json,hashlib,inspect,copy
from pathlib import Path
src=Path("/srv/opentallas-scratch/codex/emb-geometry-grid92/src")
sys.path.insert(0,str(src/"tools"))
import qwen_rom_fulldie_b3r2 as B
from die_top_lint import QWEN_R21B,QWEN_R21C
from qwen_system.embedding_columns import insert_columns
rec={"source_sha256":{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src/"tools/qwen_rom_fulldie_b3r2.py",src/"tools/qwen_system/embedding_columns.py",src/"tools/die_top_lint.py"]},"signature":str(inspect.signature(B.selected)),"cases":{}}
assert inspect.signature(B.selected).parameters["emb_hbm"].default is False
assert inspect.signature(B.selected).parameters["before_relays"].default is None
from qwen_system.embedding_pc_slots import plan_slots
args=dict(QWEN_R21C);args['cdc']=B._cdc_arg(args['cdc']);args['relay_pitch']=0
v,m=B.selected(enabled=True,before_relays=lambda v,m:insert_columns(v,m,92.016,2000.16,master='qfd_emb_strip_bus92'),**args)
r=plan_slots(v,m)
r['die']=m['die'];r['source_sha256']=rec['source_sha256']
r['source_sha256']['tools/qwen_system/embedding_pc_slots.py']=hashlib.sha256((src/'tools/qwen_system/embedding_pc_slots.py').read_bytes()).hexdigest()
Path('/srv/opentallas-scratch/codex/emb-geometry-grid92/pc_slots.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS slots',len(r['slots']),'max_vertical_um',max(i['minimum_vertical_wire_um'] for i in r['slots']))
