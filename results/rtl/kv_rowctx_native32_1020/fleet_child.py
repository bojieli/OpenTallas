"""Source-pinned minimum full-row child bench or mapped synthesis, no layout gate."""
import base64, hashlib, io, json, pathlib, subprocess, sys, tarfile
root=pathlib.Path(__file__).resolve().parents[3]
mode=sys.argv[1];mut=int(sys.argv[2])if len(sys.argv)>2 else 0
base='rtl/qwen_sys/static_embedding_20261014/'
macro='physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/'
paths=[base+'qkd_embedding_row_tx_ctx_native32.sv',base+'qkd_embedding_row_tx_ctx.sv','rtl/lib/ot_rst_relay.sv',macro+'ot_sram_1r1w_64x512_m1_r2c2.v',macro+'ot_sram_1r1w_64x512_m1_r2c2_tt.lib',macro+'ot_sram_1r1w_64x512_m1_r2c2.lef','tools/qwen_kv_die/attn_rv_1019/fanout_census.py']
if mode!='synth':paths+=['results/rtl/kv_rowctx_native32_1020/tb_rowctx_native32.sv','results/rtl/kv_rowctx_native32_1020/baseline/ot_pin_regs_wrapper.v']
files={p:(root/p).read_bytes()for p in paths}
files['tools_snapshot/ot_keep_regs.tcl']=subprocess.check_output(['git','-C',str(root),'show','origin/main:physical/common_flow/ot_keep_regs.tcl'])
if mode!='synth':
 p=base+'qkd_embedding_row_tx_ctx.sv'
 files[p]=files[p].replace(b'module qkd_embedding_row_tx_ctx #(',b'module qkd_embedding_row_tx_ctx__ot_pr_core #(')
 p='results/rtl/kv_rowctx_native32_1020/baseline/ot_pin_regs_wrapper.v'
 files[p]=files[p].replace(b'module qkd_embedding_row_tx_ctx (',b'module qkd_embedding_row_tx_ctx_old_view (')
manifest={p:hashlib.sha256(b).hexdigest()for p,b in files.items()}
id=hashlib.sha256(json.dumps(dict(mode=mode,mut=mut,sources=manifest),sort_keys=True).encode()).hexdigest()[:10]
name='codex-rowctx-native32-'+mode+'-m'+str(mut)+'-'+id
(root/'results/rtl/kv_rowctx_native32_1020'/('inputs_'+id+'.json')).write_text(json.dumps(dict(name=name,mode=mode,mut=mut,sources=manifest),indent=1)+'\n')
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz')as t:
 for p,b in files.items():i=tarfile.TarInfo(p);i.size=len(b);t.addfile(i,io.BytesIO(b))
remote='''import base64,io,os,pathlib,subprocess,tarfile
p=pathlib.Path(os.environ.get('OT_SCRATCH','/srv/opentallas-scratch'))/'claude'/__NAME__;p.mkdir(parents=True,exist_ok=True);os.chdir(p)
tarfile.open(fileobj=io.BytesIO(base64.b64decode(__PAYLOAD__)),mode='r:gz').extractall()
print('SOURCE_ROOT',p,flush=True)
if __MODE__!='synth':
 v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 for m in ([1,2,3,4] if __MODE__=='mutants' else [__MUT__]):
  with open('m'+str(m)+'-build.log','w')as f:r=subprocess.run([v,'--binary','--timing','-O2','-j','4','-Wno-fatal','--top-module','tb_rowctx_native32','-DMUT='+str(m),'--Mdir','obj'+str(m),*__SIMFILES__],stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:print(pathlib.Path('m'+str(m)+'-build.log').read_text()[-3000:]);raise SystemExit(r.returncode)
  r=subprocess.run(['obj'+str(m)+'/Vtb_rowctx_native32'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);pathlib.Path('m'+str(m)+'.log').write_text(r.stdout);print(r.stdout,flush=True)
  if m==0 and r.returncode:raise SystemExit(r.returncode)
  if m and (r.returncode==0 or 'FAIL ROWCTX_NATIVE32' not in r.stdout):raise SystemExit(2)
 print('ROWCTX_NATIVE32_EXPECTED_VERDICTS_PASS',flush=True);raise SystemExit(0)
w=p/'work';w.mkdir(exist_ok=True)
cfg={'DESIGN_NICKNAME':'codex_rowctx_native32','DESIGN_NAME':'qkd_embedding_row_tx_ctx_native32','PLATFORM':'asap7','VERILOG_FILES':'/src/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx_ctx_native32.sv /src/rtl/lib/ot_rst_relay.sv','ADDITIONAL_LIBS':'/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib','ADDITIONAL_LEFS':'/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.lef','SDC_FILE':'/work/constraint.sdc','DIE_AREA':'0 0 216 151.2','CORE_AREA':'2.16 2.16 213.84 149.04','PLACE_DENSITY':'0.45','CORNER':'WC','NUM_CORES':'4','LEC_CHECK':'0','SYNTH_CANONICALIZE_TCL':'/src/tools_snapshot/ot_keep_regs.tcl'}
(w/'config.mk').write_text(''.join('export '+k+' = '+v+'\\n'for k,v in cfg.items()))
(w/'constraint.sdc').write_text('create_clock -name core_clk -period 833.333 [get_ports ck]\\n')
with open('synth.log','w')as f:r=subprocess.run(['docker','run','--rm','--memory=16g','--memory-swap=16g','-v',str(p)+':/src','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:latest','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth'],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:print(pathlib.Path('synth.log').read_text()[-3000:]);raise SystemExit(r.returncode)
r=subprocess.run(['python3','tools/qwen_kv_die/attn_rv_1019/fanout_census.py','work/results/asap7/codex_rowctx_native32/base/1_2_yosys.v','--max','32','--top','50','--json','native32.json'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);pathlib.Path('census.log').write_text(r.stdout);print(r.stdout);raise SystemExit(r.returncode)
'''.replace('__NAME__',repr(name)).replace('__PAYLOAD__',repr(base64.b64encode(payload.getvalue()).decode())).replace('__MODE__',repr(mode)).replace('__MUT__',repr(mut)).replace('__SIMFILES__',repr([p for p in files if p.endswith('.sv')or p.endswith('.v')]))
compile(remote,'bootstrap','exec')
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','16'if mode=='synth'else'12','--threads','4','--dir','/tmp','--','python3','-c',remote]))
