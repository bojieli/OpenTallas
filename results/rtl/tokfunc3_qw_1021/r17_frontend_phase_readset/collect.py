from pathlib import Path
import json,hashlib,re
base=Path('/srv/opentallas-scratch2/claude/codex-tok-qw-2000/r17_incremental'); old=Path('/srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020'); obj=old/'out_0e597ed1c/obj'; src=old/'src_0e597ed1c'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
libraries=json.loads((base/'libraries_before.json').read_text()); sources={};children=[]
for lib,digest in libraries.items():
 prefix=lib.split('/')[0];mod=prefix[1:];args=obj/(prefix+'__hierMkArgs.f');dat=base/'obj'/prefix/(prefix+'__verFiles.dat')
 text=args.read_text(); data=dat.read_text();readset=[]
 for line in data.splitlines():
  if not line.startswith('S '):continue
  path=Path(re.findall(r'"([^"]*)"',line)[-1]);path=path if path.is_absolute() else src/path
  if not path.is_file():raise RuntimeError('missing read source '+str(path))
  name=str(path);sources.setdefault(name,sha(path));readset.append(name)
 st=base/'obj'/prefix/(mod+'.sv')
 children.append(dict(library=lib,library_sha256=digest,current_library_sha256=sha(base/'obj'/lib),
  original_library_sha256=sha(obj/lib),hierarchy_arguments_path=str(args),hierarchy_arguments_sha256=sha(args),
  hierarchy_arguments=text,source_readset=readset,verfiles_sha256=sha(dat),
  interface_stub_path=str(st),interface_stub_sha256=sha(st),interface_stub_bytes=st.stat().st_size,
  original_build_command_record=next(x for x in data.splitlines() if x.startswith('C ')),
  original_build_source_records=[x for x in data.splitlines() if x.startswith('S ')],
  original_generated_makefile=(obj/prefix/(prefix+'.mk')).read_text(),
  original_generated_makefile_sha256=sha(obj/prefix/(prefix+'.mk')),
  elaborated_top=re.search(r'--top-module-encoded\s+(\S+)',text).group(1),
  explicit_hierarchy_parameter_commands=[x for x in text.splitlines() if x.startswith('--hierarchical-block')]))
assert all(c['library_sha256']==c['current_library_sha256']==c['original_library_sha256'] for c in children)
top=base/'top_r17.f'
r=dict(schema='opentallas.qwen.r17-hierarchy-phase-readset.v1',status='READ_ONLY_CURRENT_FRONTEND_RUNNING_NO_FINAL_LINK_CLAIM',
 unit='oth-ubuntu-4059818-1792647000',client=1959148,top_arguments=top.read_text(),top_arguments_sha256=sha(top),
 selected_params=dict(RETIRE_STATIC=1,STATUS_DELAY=213,K_EXT=16,V_EXT=16,FIN_RLY=0),
 selected_r17_sources={p:sha(base/'src'/p) for p in ('rtl/qwen_sys/kv_bootage_20261019/qkd_kvs_attn_r17.sv','rtl/lib/face_land/qkd_kvs_attn_fl_r17.sv')},
 source_readset_sha256=sources,children=children,
 attention_identity=dict(new_r17_wrapper_and_core='Regenerated in current top, not any reused child archive',
 reused_native_engine='Vot_qwen_tp8_attention_native_stack_w4_cp_5/libot_qwen_tp8_attention_native_stack_w4_cp_5.a',
 native_engine_role='Unchanged hierarchy child with its own exact compile command and parameters; not qkd_kvs_attn_r16 or r17',
 assertion_no_attention_wrapper_archive=all('qkd_kvs_attn' not in c['library'] for c in children)),
 finding='Frontend consumes source and generated interface SV declarations, not child archives. Final make must link the 35 exact real implementation archives and verify they remain unchanged. Interface compatibility alone is not functional qualification.',
 preserved='Admitted frontend and runner unchanged. Partial EP9 stage is incomplete and no replacement frontend exists.')
print(json.dumps(r,indent=2))
