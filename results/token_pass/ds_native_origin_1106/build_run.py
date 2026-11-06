from pathlib import Path
import subprocess,json,re,concurrent.futures,time
W=Path('/srv/opentallas-scratch2/claude/codex-ds-native-origin-1106');PLAN=json.loads((W/'proposal.json').read_text());V='/home/ubuntu/scratch-root/claude/tok-ds-5-vl/install/bin/verilator';(W/'obj').mkdir(exist_ok=True);(W/'so').mkdir(exist_ok=True);(W/'wrap').mkdir(exist_ok=True)
def run(cmd,label):
 with (W/(label+'.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 (W/(label+'.rc')).write_text(str(q.returncode)+'\n');print(label,q.returncode,flush=True)
 return q.returncode

def child(c):
 p=c['prefix'];o=W/'obj'/p;o.mkdir(exist_ok=True);t=time.time();q=run([V,'-f',c['args']],p+'.frontend')
 if q:return dict(prefix=p,frontend_rc=q)
 sv=o/c['sv'];s=sv.read_text();name=re.search(r'^module (\w+) \(',s,re.M)[1];pretty=name.replace('___05F','__');s=s.replace('module '+name+' (','module '+pretty+' (',1).replace('verilator_lib -module "'+name+'"','verilator_lib -module "'+pretty+'"',1);(W/'wrap'/c['sv']).write_text(s)
 q=run(['make','-C',str(o),'-f',p+'.mk','-j1'],p+'.make')
 if q:return dict(prefix=p,frontend_rc=0,backend_rc=q)
 a=o/c['archive'];assert a.is_file();objs=sorted(o.glob('*.o'));assert objs and all(not x.name.startswith('verilated') for x in objs)
 so=W/'so'/(a.stem+'.so');q=run(['g++','-shared','-Wl,-soname,'+so.name,'-o',str(so)]+list(map(str,objs)),p+'.shared')
 return dict(prefix=p,frontend_rc=0,backend_rc=0,shared_rc=q,archive=str(a),shared=str(so),elapsed_s=round(time.time()-t,2))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:rows=list(ex.map(child,PLAN['children']))
(W/'children_result.json').write_text(json.dumps(rows,indent=2)+'\n')
if any(x.get('shared_rc',1) for x in rows):raise SystemExit(3)
q=run([V,'-f',str(W/'top.f')],'top_frontend')
if q:raise SystemExit(q)
O=W/'top_obj';hm=O/'Vtb_s81_die_hier.mk'
if hm.exists():(W/'top_hier_generated.mk').write_bytes(hm.read_bytes())
hm.write_text('# Frozen392 child libraries and three owned replacements are linked as DSOs.\nVM_HIER_LIBS :=\n')
assert (O/'Vtb_s81_die__main.cpp').is_file()
q=run(['make','-C',str(O),'-f','Vtb_s81_die.mk','-j2','VM_HIER_LIBS=','Vtb_s81_die__ALL.a','Vtb_s81_die__main.o','verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o'],'top_make')
if q:raise SystemExit(q)
old=Path('/srv/opentallas-scratch2/claude/codex-ds-link-1105/so');new={Path(x['shared']).name:Path(x['shared']) for x in rows};libs=[new.get(p.name,p) for p in sorted(old.glob('*.so'))];assert len(libs)==395 and sum(p.parent==old for p in libs)==392
(W/'selected_shared.json').write_text(json.dumps(list(map(str,libs)),indent=2)+'\n')
q=run(['g++','-rdynamic','-Wl,--no-as-needed','-Wl,-rpath,'+str(W/'so')+':'+str(old),'-o',str(W/'Vtb_s81_die')]+list(map(str,sorted(O.glob('*.o'))))+list(map(str,libs))+['-pthread','-lpthread','-latomic'],'top_link')
if q:raise SystemExit(q)
q=run(['ldd','-r',str(W/'Vtb_s81_die')],'top_loader')
if q:raise SystemExit(q)
s=Path('/srv/opentallas-scratch2/claude/codex-ds-native-ks833-1106/run_native_diag.py').read_text().replace('/srv/opentallas-scratch2/claude/codex-ds-native-ks833-1106',str(W)).replace("W/'a3_link.rc'","W/'top_link.rc'").replace('11-01 pinned source, bounded native KS pad-to-first-dispatch diagnostic','11-01 pinned source with receipt-selected LP origin candidate, bounded native KS pad-to-first-dispatch diagnostic').replace('rtl_changed=False','rtl_changed=True')
(W/'run_native_diag.py').write_text(s)
q=run(['python3','-I',str(W/'run_native_diag.py')],'diagnostic_driver');raise SystemExit(q)
