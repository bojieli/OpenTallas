from pathlib import Path
import subprocess,re,json,hashlib
R=Path('/srv/opentallas-scratch/claude/codex-xs-placed-1020');G=Path('/srv/opentallas-scratch/claude/ref_gate/smh_pvm_ref_s7a-20261020-041646');source=G/'routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_2_yosys.v';s=source.read_text();pattern=re.compile(r'((?:  \(\*[^\n]*\*\)\n)+)(  [^ \n]+ \\u_core[.]g_safe[.]g_madd\[([0-9]+)\][.]g_fan32[.]u_m[.]genblk1[.]g_native7[.]u_native[.][^ \n]+  \()')
manifest={}
for name,filters in [('original',()),('no_dnt',('dont_touch',)),('no_keep_dnt',('dont_touch','keep'))]:
 counts={}
 def sub(m):
  idx=int(m[3]);counts[idx]=counts.get(idx,0)+1
  attrs=''.join(l for l in m[1].splitlines(True) if not any(re.match(r'  \(\* '+x+r' =',l) for x in filters));return attrs+m[2]
 text=pattern.sub(sub,s);assert counts=={i:3500 for i in range(16)},counts
 p=R/('import_'+name+'.v');p.write_text(text);manifest[name]=dict(sha256=hashlib.sha256(text.encode()).hexdigest(),counts=counts,filters=filters)
 cmd=['docker','run','--rm','-v',str(R)+':/audit','-v',str(G/'src')+':/src:ro','-e','IMPORT_V=/audit/'+p.name,'-e','IMPORT_OUT=/audit/import_'+name+'.json','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','-exit','/audit/import_probe.tcl']
 with (R/('import_'+name+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
(R/'import_probe_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
