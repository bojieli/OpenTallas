from pathlib import Path
import subprocess,json
W=Path('/srv/opentallas-scratch2/claude/codex-ds-native-origin-1106');O=W/'top_obj';libs=json.loads((W/'selected_shared.json').read_text());assert len(libs)==395
objs=[x for x in sorted(O.glob('*.o')) if x.name!='Vtb_s81_die__main.o'];old=Path('/srv/opentallas-scratch2/claude/codex-ds-link-1105/so')
def run(cmd,label):
 with (W/(label+'.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 (W/(label+'.rc')).write_text(str(q.returncode)+'\n');print(label,q.returncode,flush=True)
 if q.returncode:raise SystemExit(q.returncode)
run(['g++','-rdynamic','-Wl,--no-as-needed','-Wl,-rpath,'+str(W/'so')+':'+str(old),'-o',str(W/'Vtb_s81_die')]+list(map(str,objs))+libs+['-pthread','-lpthread','-latomic'],'top_link_a2')
run(['ldd','-r',str(W/'Vtb_s81_die')],'top_loader_a2')
s=Path('/srv/opentallas-scratch2/claude/codex-ds-native-ks833-1106/run_native_diag.py').read_text().replace('/srv/opentallas-scratch2/claude/codex-ds-native-ks833-1106',str(W)).replace("W/'a3_link.rc'","W/'top_link_a2.rc'").replace('11-01 pinned source, bounded native KS pad-to-first-dispatch diagnostic','11-01 pinned source with receipt-selected LP origin candidate, bounded native KS pad-to-first-dispatch diagnostic').replace('rtl_changed=False','rtl_changed=True').replace("cmd=['/usr/bin/time'","cmd=['/usr/bin/stdbuf','-oL','-eL','/usr/bin/time'").replace('cycles=11000','cycles_budget=11000')
s+='\nout["first_dispatch_stop"]=re.findall(r"^NATIVE_FIRST_DISPATCH_STOP first=(\\d+) finish=(\\d+)",s,re.M)\nout["fault_details"]=re.findall(r"^.*(?:FAULT|%Error|THOST.*fault 1).*$",s,re.M)\n(R/"result.json").write_text(json.dumps(out,indent=2)+"\\n")\nraise SystemExit(0 if ok else 1)\n'
(W/'run_native_diag_a2.py').write_text(s)
# Diagnostic writes the detailed structured result; propagate its scoped verdict.
q=subprocess.call(['python3','-I',str(W/'run_native_diag_a2.py')]);raise SystemExit(q)
