from pathlib import Path
import subprocess,json,re,os
W=Path('/srv/opentallas-scratch2/claude/codex-ds-native-host-1106');OLD=Path('/srv/opentallas-scratch2/claude/codex-ds-native-origin-1106');V='/home/ubuntu/scratch-root/claude/tok-ds-5-vl/install/bin/verilator';(W/'tmp').mkdir(exist_ok=True);env=dict(os.environ,TMPDIR=str(W/'tmp'),CCACHE_DISABLE='1',CCACHE_TEMPDIR=str(W/'tmp'))
s=(OLD/'top.f').read_text().replace(str(OLD/'tb_s81_die_native_ks.sv'),str(W/'tb_s81_die_native_host.sv')).replace(str(OLD/'native_ks_peer.sv'),str(W/'native_ks_peer.sv'));s=re.sub(r'-Mdir\s+\S+','-Mdir '+str(W/'top_obj'),s);s+='\n'+str(W/'native_host_peer.sv')+'\n';(W/'top.f').write_text(s)
def run(cmd,label):
 with (W/(label+'.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
 (W/(label+'.rc')).write_text(str(q.returncode)+'\n');print(label,q.returncode,flush=True)
 if q.returncode:raise SystemExit(q.returncode)
run([V,'-f',str(W/'top.f')],'top_frontend');O=W/'top_obj';(O/'Vtb_s81_die_hier.mk').write_text('# Three existing repaired LP DSOs plus392 original protected DSOs.\nVM_HIER_LIBS :=\n')
run(['make','-C',str(O),'-f','Vtb_s81_die.mk','-j2','VM_HIER_LIBS=','Vtb_s81_die__ALL.a','verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o'],'top_make')
libs=json.loads((OLD/'selected_shared.json').read_text());assert len(libs)==395 and sum(str(OLD/'so') in x for x in libs)==3
(W/'selected_shared.json').write_text(json.dumps(libs,indent=2)+'\n');objects=[x for x in sorted(O.glob('*.o')) if x.name!='Vtb_s81_die__main.o']
run(['g++','-rdynamic','-Wl,--no-as-needed','-Wl,-rpath,'+str(OLD/'so')+':/srv/opentallas-scratch2/claude/codex-ds-link-1105/so','-o',str(W/'Vtb_s81_die')]+list(map(str,objects))+libs+['-pthread','-lpthread','-latomic'],'top_link')
run(['ldd','-r',str(W/'Vtb_s81_die')],'top_loader')
run(['python3','-I',str(W/'run_native_host_diag.py')],'diagnostic_driver')
