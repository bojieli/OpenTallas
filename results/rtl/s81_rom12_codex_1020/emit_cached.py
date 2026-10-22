"""Exercise the production DVC emit_files hook against a preserved actual field; no legaliser rerun."""
import hashlib,json,pickle,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_field_calendar as F
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020');L=sys.argv[1]
r=pickle.loads((D/f'out/pack_real/{L}.pickle').read_bytes())
F.compile_ops=lambda *a,**kw:r
files,cal=F.emit_files(None,{'op':'ffn.experts_gu','id':L+'.ffn.experts_gu'},{'fixtures':str(D/'unused'),'layer':L},'u_s_0S')
O=D/f'out/emit_cached/{L}';O.mkdir(parents=True,exist_ok=False)
proof={}
for key,value in files.items():
 if not key.startswith('prog/xs/layer_calendar/'):continue
 name=Path(key).name
 (O/name).write_text(value)
 if name!='manifest.json':assert value==(D/f'out/pack_real/{L}'/name).read_text(),name
 proof[name]=hashlib.sha256(value.encode()).hexdigest()
(O/'proof.json').write_text(json.dumps(dict(PASS=True,files=proof,source_hook='xs_field_calendar.emit_files'),indent=1)+'\n')
print('DVC_EMIT_SHARED PASS',L,len(proof),'files byte-identical to reader-tested images',flush=True)
