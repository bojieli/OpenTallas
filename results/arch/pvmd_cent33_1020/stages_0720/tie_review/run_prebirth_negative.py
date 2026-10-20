from pathlib import Path
import subprocess,json,hashlib,shutil
r=Path('/srv/opentallas-scratch/claude/codex-pvm-bindfirst-stages-0720');d=r/'prebirth_kernel_rewire';d.mkdir(exist_ok=False);shutil.copy2(r/'prebirth_guard_source/graph_guard.tcl',d/'graph_guard.tcl')
p=r/'work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_2_yosys.v';s=p.read_text()
needle='\\u_core.g_safe.g_madd[0].g_fan32.u_m.genblk1.g_native7.u_native.c2602  (';i=s.index(needle);j=s.index('  );',i);part=s[i:j]
assert part.count('.SETN(_18312_)')==1
mutant=s[:i]+part.replace('.SETN(_18312_)','.SETN(clk)')+s[j:];(d/'mutant.v').write_text(mutant)
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','-v',str(r)+':/audit','-v',str(r/'src')+':/src:ro','-e','IMPORT_V=/audit/prebirth_kernel_rewire/mutant.v','-e','PVM_BF_EXPECTED=/audit/work/bindfirst_proof/expected.tcllist','-e','PVM_BF_RECEIPTS=/audit/prebirth_kernel_rewire','--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',img,'-exit','/audit/prebirth_negative.tcl']
with (d/'witness.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
log=(d/'witness.log').read_text();ok=rc!=0 and 'PVM_BF_GRAPH_DRIFT prebirth_kernel_rewire' in log and 'cells=56000 protected=0 noDNTclear' in log
out=dict(status='PASS' if ok else 'FAIL',rc=rc,expected='PVM_BF_GRAPH_DRIFT prebirth_kernel_rewire',matched=ok,phase='fresh postlink before PG/protection',mutated_pin='u_core.g_safe.g_madd[0].g_fan32.u_m.genblk1.g_native7.u_native.c2602/SETN',old_net='_18312_',new_net='clk',original_mapped_sha256=hashlib.sha256(s.encode()).hexdigest(),mutant_mapped_sha256=hashlib.sha256(mutant.encode()).hexdigest(),guard_sha256=hashlib.sha256((d/'graph_guard.tcl').read_bytes()).hexdigest())
(d/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(out,flush=True);raise SystemExit(0 if ok else 1)
