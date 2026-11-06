from pathlib import Path
import sys,json,importlib.util,hashlib
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'tools/s81_static_control'))
spec=importlib.util.spec_from_file_location('owned_aproj_native',R/'aproj_native.py');A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
F=Path('/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/slice_images_batch/u_s_7N/prog/xs/L0.attn.a_proj.json');a=json.loads(F.read_text());assert a['rows_per_slice']==0
frames=a['frames'];actual=[x['frame'] for x in frames]
class Placement:
 inst={f['frame']:{'master':f['master']} for f in frames}
 def frames_of(self,sl):assert sl=='u_s_7N';return actual
D=Placement();images=A.idle_image_material(D,'u_s_7N',frames);assert len(images)==7
# Decode all physical ROM rows: the complete4096x72logical image must be0.
assert all(len(s.splitlines())==512 and all(len(v)==144 and int(v,16)==0 for v in s.splitlines()) for s in images.values())
base=R/'output_a2';base.mkdir(exist_ok=False)
for n,s in images.items():(base/n).write_text(s)
controls=[]
for label,mut in [('active_row',lambda f:f[0].update(rows=[17])),('unknown_row',lambda f:f[0].pop('rows')),('missing_frame',lambda f:f.pop()),('wrong_master',lambda f:f[0].update(master='phantom'))]:
 f=json.loads(json.dumps(frames));mut(f)
 try:A.idle_image_material(D,'u_s_7N',f)
 except ValueError as e:controls.append(dict(name=label,rejected=True,reason=str(e)))
 else:raise AssertionError('accepted bad idle control '+label)
res=dict(verdict='PASS',scope='idle image material and ownership guard only; historical source resolver unavailable',actual_slice='u_s_7N',actual_frame_count=len(frames),actual_ownership_sha256=hashlib.sha256(F.read_bytes()).hexdigest(),zero_roms=len(images),logical_zero_words=7*4096,frame_weights_emitted=0,issuer_commands_emitted=False,selected_source_resolution_qualified=False,production_bundle_emitted=False,layer_lifetime_qualified=False,guard_controls=controls,pin_cycles_added=0,output=str(base))
(R/'result_a2.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res),flush=True)
