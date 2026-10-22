import sys,types,subprocess,json,hashlib,concurrent.futures
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/ref_gate');src=root/'qkd_kvs_grp_h_s4b-20261019-221603/src';out=root/'codex_s5_1020';sys.path.insert(0,str(src/'tools/qwen_kv_die'));import kvs_grp_s2_bench as B
wr=[]
for base,top in [('qkd_kvs_grp_s2','qkd_kvs_grp_s5'),('qkd_kvs_grp_h_s2','qkd_kvs_grp_h_s5')]:
 ports=B.ports((src/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_s2.sv').read_text(),base);name=top+'_bench';decl=[];conn=[];body=[]
 for direction,width,p in ports:
  size='' if width==1 else '[%d:0] '%(width-1);decl.append('    '+direction+' wire '+size+p)
  target=p if direction=='input' else 'raw_'+p;conn.append('.'+p+'('+target+')')
  if direction=='output':
   body.append('wire '+size+target+';');mut=1 if p=='o_dn' else 2 if p=='krsp' else 0;body.append('assign '+p+' = '+target+(" ^ ((MUT == %d) ? %d'd1 : %d'd0)"%(mut,width,width) if mut else '')+';')
 wr.append('module '+name+' #(parameter integer MUT=0) (\n'+',\n'.join(decl)+'\n);\n'+'\n'.join(body)+'\n'+('qkd_kvs_grp_s2' if top=='qkd_kvs_grp_s5' else 'qkd_kvs_grp_h_s4')+' u('+','.join(conn)+');\nendmodule\n')
(out/'bench_orig_wrappers.sv').write_text('\n'.join(wr));shim=types.SimpleNamespace(OUT=str(out/'bench_orig_wrappers.sv'),REF=B.S2.REF,KINDS=(('qkd_kvs_grp','qkd_kvs_grp_s5_bench'),('qkd_kvs_grp_h','qkd_kvs_grp_h_s5_bench')));B.S2=shim
sources=[next((root/'qkd_kvs_grp_s3a-20261019-220148/routes/gate/work/orfs/results/asap7').glob('*/base/1_2_yosys.v')),next((root/'qkd_kvs_grp_h_s4b-20261019-221603/routes/gate/work/orfs/results/asap7').glob('*/base/1_2_yosys.v')),out/'bench_orig_wrappers.sv',out/'library_model.v',src/shim.REF]+[src/p for p in B.LEAVES]
ver=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
def run(mut):
 case=out/('bench_orig_m'+str(mut));case.mkdir(exist_ok=True);txt=B.tb(6000).replace('module tb;','module tb;\nlocalparam integer MUT = %d;'%mut,1);
 txt=txt.replace('task compare(input integer side); begin','task compare(input integer side); begin if (e >= 32) begin').replace('end endtask\nalways @(negedge hck)','end end endtask\nalways @(negedge hck)')
 txt=txt.replace('    stim_g; stim_h;', '    if (e >= 32) begin stim_g; stim_h; end')
 (case/'tb.sv').write_text(txt)
 cmd=[ver,'--binary','--timing','-j','8','-Wno-fatal','-Wno-lint','-Wno-style','--x-assign','0','--x-initial','0','--top-module','tb','--Mdir',str(case/'build'),str(case/'tb.sv')]+[str(p) for p in sources]
 with (case/'build.log').open('w') as h:rc=subprocess.run(cmd,stdout=h,stderr=subprocess.STDOUT).returncode
 if rc:return dict(mut=mut,build_rc=rc,pass_expected=False)
 with (case/'run.log').open('w') as h:rc=subprocess.run([str(case/'build/Vtb')],stdout=h,stderr=subprocess.STDOUT).returncode
 log=(case/'run.log').read_text();ok=rc==0 and 'S2_PASS' in log if mut==0 else rc!=0 and 'S2_FAIL' in log;print('MUT',mut,'EXPECTED',ok,'RC',rc,flush=True);return dict(mut=mut,rc=rc,pass_expected=ok,line=next((s for s in log.splitlines() if 'S2_' in s),''))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:res=list(ex.map(run,[0]))
(out/'bench_orig_results.json').write_text(json.dumps(dict(cases=res,verilator=subprocess.check_output([ver,'--version'],text=True).strip(),sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},arbitrary_init_qualification='separate coldproof, not this zero-initial value regression'),indent=1)+'\n');print(json.dumps(res),flush=True)
raise SystemExit(0 if all(r['pass_expected'] for r in res) else 1)
