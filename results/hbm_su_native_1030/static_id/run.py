import concurrent.futures,json,pathlib,subprocess,re
D=pathlib.Path(__file__).resolve().parent;ROOT=D.parents[2];PACK=ROOT/'physical/die_plan/hbm_arch_cores/native_1030';M=json.load(open(D.parent/'su_source_manifest.json'));facts=json.load(open(D.parent/'native_cut_abi.json'))
files=[str(PACK/(n+'.sv'))for n in M['roots']['ot_hnx_su_exp__rst3']if not n.startswith('ot_sram_')]
bindings=[]
for r in facts:
 if r['module']not in ('ot_hnx_su_exp__rst3','ot_hnx_su_plain4__lid9_rst3'):continue
 base=r['ids']['lane_lane_id']['value'];exp=r['module']=='ot_hnx_su_exp__rst3'
 for lane in range(1 if exp else 4):bindings.append(dict(path=r['path'],lane=lane,kind=1 if exp else 0,id=base if exp else 4*base+lane))
for kind in [0,1]:
 cmd=['iverilog','-g2012','-s','tb','-o',str(D/('tb'+str(kind))),'-Ptb.KIND='+str(kind)]+['-D'+n for n in M['manifest_defines']]+[str(D/'lockstep.sv'),str(D/'ot_hbm_su_static_lane_pinreg__static_id.sv')]+files
 with open(D/('compile'+str(kind)+'.log'),'w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('compile '+str(kind))
 print('COMPILED',kind,flush=True)
def run(pair):
 kind,id=pair;r=subprocess.run(['vvp',str(D/('tb'+str(kind))),'+ID='+str(id)],capture_output=True,text=True);(D/('K'+str(kind)+'_ID'+str(id)+'.log')).write_text(r.stdout+r.stderr)
 match=re.search(r'ERR(\d+) MUT(\d+)',r.stdout);rc=r.returncode or (0 if match and int(match[1])==0 and int(match[2])>0 else 2)
 return dict(kind=kind,id=id,rc=rc,output=r.stdout)
pairs=sorted(set((b['kind'],b['id'])for b in bindings))
with concurrent.futures.ThreadPoolExecutor(max_workers=8)as ex:results=list(ex.map(run,pairs))
report=dict(status='PASS'if all(r['rc']==0 for r in results)else'FAIL',scope='Minimum actual native pinreg full315output boundary; true POR before edge1, cold and warm reset, no masks; same actual preferred bodies/defines',bindings=bindings,unique_cases=len(pairs),results=results)
(D/'lockstep_results.json').write_text(json.dumps(report,indent=1)+'\n');print('RESULT',report['status'],'bindings',len(bindings),'cases',len(pairs),flush=True)
if report['status']!='PASS':raise SystemExit(1)
