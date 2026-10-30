from pathlib import Path
from collections import Counter
import subprocess,json,re,shlex,socket
b=Path('/srv/opentallas-scratch2/claude/codex-sc-cap-0336');host='epyc2';root='/srv/opentallas-scratch2/claude/qc-kits-w/gen';cases=['slw_sc_v3','slw_sc_v1__cl63e5a7a2','sle_sc_v3','slw_sc_v1__cl64543eaf__cl5e017c6f'];out=[]
remote_meta=r'''from pathlib import Path
import json,re,sys
k=Path(sys.argv[1]);cfg=(k/'config.mk').read_text();name=re.search(r'^export DESIGN_NICKNAME = (.*)$',cfg,re.M).group(1);native=k/'1_synth_odb.v';native=native if native.exists() else k/'run/results/asap7'/name/'base/1_2_yosys.v'
shape=list(map(float,re.search(r'^export DIE_AREA = (.*)$',cfg,re.M).group(1).split()));core=[]
for f in (k/'rtl').glob('*.s*'):
 if 'bound' not in f.name and not f.name.startswith('qfd_qc_'):continue
 with f.open() as h:h.seek(max(0,f.stat().st_size-65536));s=h.read()
 m=re.search(r'\b(\w+)\s+u_core\s*\(',s)
 if m:core.append((m.group(1),str(f)))
module=core[0][0] if core else None;ports=[]
for f in (k/'rtl').glob('*.s*'):
 with f.open() as h:s=h.read(8192)
 if not module or not re.search(r'\bmodule\s+'+re.escape(module)+r'\b',s):continue
 s=s[re.search(r'\bmodule\s+'+re.escape(module)+r'\b',s).start():].split('endmodule',1)[0]
 for dr,hi,pn in re.findall(r'^\s*(input|output)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):0\])?\s*(\w+)\s*[,;\n]',s,re.M):ports.append(dict(name=pn,direction=dr,bits=int(hi)+1 if hi else 1))
 print(json.dumps(dict(native=str(native),outline_um=shape[2:],existing_core_module=module,core_instance='u_bound.u_core',bound_source=core,leaf_file=str(f),ports=ports)));break
else:print(json.dumps(dict(native=str(native),outline_um=shape[2:],existing_core_module=module,core_instance='u_bound.u_core',bound_source=core,ports=[])))
'''
rx=re.compile(r'^\s+(\w*ASAP7\w*)\s+(\\?\S+)\s*\(')
for t in cases:
 k=f'{root}/{t}/{t}';local=socket.gethostname()=='dear-crayfish';meta=json.loads(subprocess.check_output((['python3','-c',remote_meta,k] if local else ['ssh',host,'python3 -c '+shlex.quote(remote_meta)+' '+shlex.quote(k)]),text=True));p=subprocess.Popen((['cat',meta['native']] if local else ['ssh',host,'cat -- '+shlex.quote(meta['native'])]),stdout=subprocess.PIPE,text=True);groups=Counter();seq=Counter();masters=Counter()
 for line in p.stdout:
  m=rx.match(line)
  if not m:continue
  master,nm=m.groups();nm=nm.lstrip('\\');parts=re.split('[/.]',nm);g='.'.join(parts[:2]);groups[g]+=1;masters[master]+=1
  if re.search(r'DFF|SDF|DHL|DLL|LQN',master):seq[g]+=1
 assert p.wait()==0
 total=sum(groups.values());core=groups['u_bound.u_core'];r=dict(type=t,host=host,actual_std=total,actual_macro=0,existing_core_std=core,existing_core_seq=seq['u_bound.u_core'],remaining_wrapper_std=total-core,remaining_wrapper_seq=sum(seq.values())-seq['u_bound.u_core'],both_under_400k=bool(core and core<400000 and total-core<400000),top_hierarchy=[dict(prefix=g,std=n,seq=seq[g]) for g,n in groups.most_common(12)],**meta)
 r['interface_bits']=sum(p['bits'] for p in meta['ports']);out.append(r);print(json.dumps({q:r[q] for q in ['type','actual_std','existing_core_std','existing_core_seq','remaining_wrapper_std','remaining_wrapper_seq','both_under_400k','existing_core_module','interface_bits','outline_um'] }),flush=True)
(b/'old_sc_native_cut_census.json').write_text(json.dumps(dict(scope='actual native existing hierarchy census only; no new build/P&R or E-side bay reuse',rows=out),indent=2)+'\n')
