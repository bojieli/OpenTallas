"""Stage a source-pinned minimum candidate on the automatically admitted fleet."""
import base64, hashlib, json, pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parents[3]
mode = sys.argv[1]
target = sys.argv[2] if len(sys.argv)>2 else "cal"
mutation = int(sys.argv[3]) if len(sys.argv)>3 else 0
base = 'rtl/qwen_sys/static_embedding_20261014/'
paths = [base+n+'.sv' for n in ('qkd_embedding_static_join4', 'qkd_embedding_static_join', 'qkd_embedding_static_join4_cal', 'qkd_embedding_static_join_fan32')]
paths += ['rtl/lib/ot_rst_relay.sv', 'tools/qwen_kv_die/attn_rv_1019/fanout_census.py']
if mode == 'miter': paths += ['results/rtl/kv_embpc_takeover_1020/tb_cal_pipe_native32.sv']
if target == 'ctx':
 paths=[base+'qkd_embedding_ctx_start.sv','rtl/lib/ot_rst_relay.sv','tools/qwen_kv_die/attn_rv_1019/fanout_census.py']
 if mode=='miter':paths+=['results/rtl/kv_embpc_takeover_1020/tb_ctx_native32.sv']
files = {p:(root/p).read_text() for p in paths}
files['ot_keep_regs.tcl'] = subprocess.check_output(['git','-C',str(root),'show','origin/main:physical/common_flow/ot_keep_regs.tcl'], text=True)
if mode == 'synth':
 p=base+('qkd_embedding_ctx_start.sv' if target=='ctx' else 'qkd_embedding_static_join4_cal.sv')
 files[p]=files[p].replace('parameter integer NATIVE32 = 0','parameter integer NATIVE32 = 1').replace('parameter integer PIPE_JOIN = 0','parameter integer PIPE_JOIN = 1')
elif target=='cal':
 p='results/rtl/kv_embpc_takeover_1020/tb_cal_pipe_native32.sv'
 files[p]=files[p].replace('if(warm>8)','if(warm>16)').replace('i%512==40','i%512==80').replace('i%512<16 && i%2==0','i%512>=32 && i%512<48 && i%2==0').replace('if(i%11!=0)','if(i%11!=0 || warm<16)')
if target=='ctx' and mode=='miter' and mutation:
 p='results/rtl/kv_embpc_takeover_1020/tb_ctx_native32.sv'
 files[p]=files[p].replace('#(.NATIVE32(1)) u_b','#(.NATIVE32(1), .MUT('+str(mutation)+')) u_b')
manifest={p:hashlib.sha256(s.encode()).hexdigest() for p,s in files.items()}
digest=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
name='codex-emb-'+target+'-native32-'+mode+'-'+digest[:10]
(root/'results/rtl/kv_embpc_takeover_1020'/('inputs_'+mode+'_'+digest[:10]+'.json')).write_text(json.dumps(dict(name=name,mode=mode,sources=manifest),indent=1)+'\n')
remote = '''import pathlib,base64,json,os,subprocess
p=pathlib.Path(os.environ.get('OT_SCRATCH','/srv/opentallas-scratch'))/'claude'/__TASK_NAME__
p.mkdir(parents=True,exist_ok=True);os.chdir(p)
files=json.loads(base64.b64decode(PAYLOAD))
for n,s in files.items():
 t=p/n;t.parent.mkdir(parents=True,exist_ok=True);t.write_text(s)
print('SOURCE_ROOT',p,flush=True)
if MODE=='miter':
 v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 with open('build.log','w') as f:r=subprocess.run([v,'--binary','--timing','-O2','-j','4','-Wno-fatal','--top-module','tb_cal_pipe_native32','--Mdir','obj',*[n for n in files if n.endswith('.sv')]],stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:print(pathlib.Path('build.log').read_text()[-2500:]);raise SystemExit(r.returncode)
 r=subprocess.run(['obj/Vtb_cal_pipe_native32'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);pathlib.Path('run.log').write_text(r.stdout);print(r.stdout);raise SystemExit(r.returncode)
w=p/'work';w.mkdir(exist_ok=True)
cfg={'DESIGN_NICKNAME':'codex_emb_calnative','DESIGN_NAME':'qkd_embedding_static_join4_cal','PLATFORM':'asap7','VERILOG_FILES':' '.join('/src/'+n for n in files if n.endswith('.sv')),'SDC_FILE':'/work/constraint.sdc','DIE_AREA':'0 0 432 302.4','CORE_AREA':'2.16 2.16 429.84 300.24','PLACE_DENSITY':'0.5','CORNER':'WC','NUM_CORES':'4','LEC_CHECK':'0','SYNTH_CANONICALIZE_TCL':'/src/ot_keep_regs.tcl'}
(w/'config.mk').write_text(''.join('export '+k+' = '+v+'\\n' for k,v in cfg.items()))
(w/'constraint.sdc').write_text('create_clock -name core_clk -period 833.333 [get_ports ck]\\n')
with open('synth.log','w') as f:r=subprocess.run(['docker','run','--rm','--memory=16g','--memory-swap=16g','-v',str(p)+':/src','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth'],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:print(pathlib.Path('synth.log').read_text()[-2500:]);raise SystemExit(r.returncode)
r=subprocess.run(['python3','tools/qwen_kv_die/attn_rv_1019/fanout_census.py','work/results/asap7/codex_emb_calnative/base/1_2_yosys.v','--max','32','--top','40','--json','native32.json'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);pathlib.Path('census.log').write_text(r.stdout);print(r.stdout);raise SystemExit(r.returncode)
'''.replace('__TASK_NAME__',repr(name)).replace('MODE',repr(mode)).replace('PAYLOAD',repr(base64.b64encode(json.dumps(files).encode()).decode()))
if target=='ctx':remote=remote.replace('tb_cal_pipe_native32','tb_ctx_native32').replace('qkd_embedding_static_join4_cal','qkd_embedding_ctx_start')
compile(remote,'fleet_bootstrap','exec')
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','16' if mode=='synth' else '8','--threads','4','--dir','/tmp','--','python3','-c',remote]))
