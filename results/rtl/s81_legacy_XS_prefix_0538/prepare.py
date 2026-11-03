from pathlib import Path
import json,re,hashlib
R=Path('/srv/opentallas-scratch2/claude/codex-ds-legacy-xs-gate-0538');F=Path('/srv/opentallas-scratch2/claude/codex-ds-service-hier-0340/fs');M=json.loads((R/'module_definitions.json').read_text());known=set(M)
seen=set();todo=['ot_s81sl_xg','ot_rom_4096x72_m8'];files={}
while todo:
 n=todo.pop()
 if n in seen:continue
 seen.add(n)
 for d in M[n]:
  p=F/d['file'];raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=d['file_sha256']:raise ValueError('captured source changed '+str(p))
  files[str(p)]=raw.decode();text=re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode(),flags=re.S);text=re.sub(r'"(?:\\.|[^"\\])*"','',text)
  todo.extend((set(re.findall(r'\b[A-Za-z_][\w$]*\b',text))&known)-seen)
xs=next(p for p in files if p.endswith('/ot_s81sl_xs.sv'));xg=next(p for p in files if p.endswith('/portfix178/ot_s81sl_xg.sv'))
oldxs=files.pop(xs);oldxg=files.pop(xg)
newxs=oldxs.replace('#(.INSTANCE(n))','#(.INSTANCE(INSTANCE == "" ? n : {INSTANCE, ".", n}))').replace('module ot_s81sl_xs (','module ot_s81sl_xs #(parameter INSTANCE = "") (')
newxg=oldxg.replace('module ot_s81sl_xg (','module ot_s81sl_xg #(parameter INSTANCE = "") (').replace('ot_s81sl_xs u_s (','ot_s81sl_xs #(.INSTANCE(INSTANCE)) u_s (')
assert newxs.replace('#(.INSTANCE(INSTANCE == "" ? n : {INSTANCE, ".", n}))','#(.INSTANCE(n))').replace('module ot_s81sl_xs #(parameter INSTANCE = "") (','module ot_s81sl_xs (')==oldxs
assert newxg.replace('module ot_s81sl_xg #(parameter INSTANCE = "") (','module ot_s81sl_xg (').replace('ot_s81sl_xs #(.INSTANCE(INSTANCE)) u_s (','ot_s81sl_xs u_s (')==oldxg
(R/'xs_candidate.sv').write_text(newxs);(R/'xg_candidate.sv').write_text(newxg)
(R/'xs_reference.sv').write_text(oldxs.replace('module ot_s81sl_xs (','module ot_s81sl_xs_gate_ref ('))
(R/'xg_reference.sv').write_text(oldxg.replace('module ot_s81sl_xg (','module ot_s81sl_xg_gate_ref (').replace('ot_s81sl_xs u_s (','ot_s81sl_xs_gate_ref u_s ('))
(R/'xs_original.sv').write_text(oldxs);(R/'xg_original.sv').write_text(oldxg)
# Unchanged actual legacy dependencies, with the native aligned-v2 ROM and SRAM models.
(R/'sources.f').write_text(''.join(json.dumps(p)+'\n' for p in sorted(files))+'xs_reference.sv\nxg_reference.sv\nxs_candidate.sv\nxg_candidate.sv\ntb.sv\n')
(R/'source_hashes.json').write_text(json.dumps(dict(module_closure=sorted(seen),files=[dict(path=p,sha256=hashlib.sha256(t.encode()).hexdigest()) for p,t in sorted(files.items())],old_XS_sha256=hashlib.sha256(oldxs.encode()).hexdigest(),old_XG_sha256=hashlib.sha256(oldxg.encode()).hexdigest(),new_XS_sha256=hashlib.sha256(newxs.encode()).hexdigest(),new_XG_sha256=hashlib.sha256(newxg.encode()).hexdigest(),source_body_changes_only='unused simulation INSTANCE declaration/propagation and ROM filename macro',uses_XS4=False),indent=2)+'\n')
# Real compiler image bytes; used as a stimulus corpus only, not SID7 mission qualification.
K=['pq_calendar_action','pq_calendar_time','pq_phase0','pq_stream0','pq_stream1','pq_stream2','pq_stream3'];P=['u_s_3N.u_slice.u_xg','u_s_3S.u_sl.u_xg'];normal=R/'images';normal.mkdir()
oracle=[]
for j,k in enumerate(K):
 src=R/'image_input'/(k+'.viamap.hex');raw=src.read_text();rows=[int(x,16) for x in raw.splitlines()];assert len(rows)==512
 words=[sum(((rows[a//8]>>(b*8+a%8))&1)<<b for b in range(72)) for a in range(4096)];oracle.extend(words)
 (normal/src.name).symlink_to(src.resolve());(normal/(P[0]+'.'+k+'.viamap.hex')).symlink_to(src.resolve())
 marker=sum((0xa0+j+i)<<(8*i) for i in range(9));row=sum((255 if (marker>>b)&1 else 0)<<(8*b) for b in range(72))
 (normal/(P[1]+'.'+k+'.viamap.hex')).write_text((f'{row:0144x}\n')*512)
(R/'oracle.hex').write_text(''.join(f'{x:018x}\n' for x in oracle))
for label in ['wrong_prefix','wrong_image']:
 d=R/label;d.mkdir()
 for p in normal.iterdir():(d/p.name).symlink_to(p.resolve())
 key=P[0]+'.pq_phase0.viamap.hex';(d/key).unlink()
 if label=='wrong_prefix':(d/key).symlink_to((normal/(P[1]+'.pq_phase0.viamap.hex')).resolve())
 else:
  rows=[int(x,16) for x in (R/'image_input/pq_phase0.viamap.hex').read_text().splitlines()];rows[0]^=1
  (d/key).write_text(''.join(f'{x:0144x}\n' for x in rows))
m=json.loads((R/'image_input/programme.json').read_text());cmd=[x for x in m['command_descriptors'] if x['target']==2];first=min(x['XR_output_pin_edge'] for x in cmd)
(R/'control.txt').write_text(''.join(f'{x["XR_output_pin_edge"]-first+30} {x["body160"]}\n' for x in cmd))
print('LEGACY_NATIVE_CLOSURE',len(seen),'modules',len(files)+4,'files')
