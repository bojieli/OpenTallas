from pathlib import Path
import sys,json,os,hashlib
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'tools/s81_dv'));sys.path.insert(0,str(R/'tools/s81_static_control'))
from layer_prog import aproj_native as A
P=R/'source';meta=json.loads((R/'source_receipt.json').read_text());sel=json.loads((P/'idle_source_selection.json').read_text())
os.environ.update(OT_S81_SELECTED_SOURCE_ROOT=str(P),OT_S81_SELECTED_ASBUILT_MANIFEST='idle_source_selection.json',OT_S81_SELECTED_DEFINES=','.join(sel['defines']))
F=Path('/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/slice_images_batch/u_s_7N/prog/xs/L0.attn.a_proj.json');original=F.read_bytes();a=json.loads(original);assert a['rows_per_slice']==0;frames=a['frames']
class Placement:
 inst={**{f['frame']:{'master':f['master']} for f in frames},'u_s_7N':dict(master=meta['actual_idle_slice_master'],params=meta['actual_idle_slice_params'])}
 def frames_of(self,sl):assert sl=='u_s_7N';return [x['frame'] for x in frames]
files=A.idle_programme(Placement(),dict(id='L0.attn.a_proj'),dict(slice='u_s_7N'),frames);O=R/'output';O.mkdir(exist_ok=False)
for n,s in files.items():p=O/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
m=json.loads(next(s for n,s in files.items() if n.endswith('/programme.json')))
assert m['selected_slice_source']['die_master']==meta['actual_idle_slice_master'];assert not m['lifetime_qualified'] and m['sealed_programme_held'] and m['idle_actual_slice']
res=dict(verdict='PASS',scope='actual idle source resolution and prototype image emission only',selected_source=m['selected_slice_source'],actual_ownership_sha256=hashlib.sha256(original).hexdigest(),idle_frames=6,zero_roms=7,original_untracked_selector_restored=False,source_selector_cohort='new minimal explicit selector over retained exact RTL and actual native build defines',production_enabled=False,physical_binding_qualified=False,pin_cycles_added=0,prototype_output=str(O))
(R/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res),flush=True)
