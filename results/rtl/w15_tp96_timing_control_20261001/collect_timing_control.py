"""Archive only small measurement controls; never launch a collective campaign."""
import pathlib,subprocess,json,hashlib,sys,shutil,datetime
root=pathlib.Path('/home/ubuntu/w15b-tp96-timing-20261001')
out=root/'results/rtl/w15_tp96_timing_control_20261001'
build=pathlib.Path('/tmp/claude-1000/w15b_codex_sram_20261001/timing_control_build_d9d78')
assert not out.exists() and not build.exists()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
sha=lambda b:hashlib.sha256(b).hexdigest()
sys.path.insert(0,str(root/'tools'));import w15_tp96_exact as C;import w15_collectives as W
files={};cases={}
build.mkdir()
for name,width,overflow,witness in [('long_round',64,0,'MEASURE_CONTROL_PASS'),('narrow_rejected',16,0,'measurement width must be 23..64'),('overflow_rejected',23,1,'measurement counter overflow')]:
 exe=build/(name+'.vvp')
 cmd=['iverilog','-g2012','-s','tb_w15_tp96_measure_control',f'-Ptb_w15_tp96_measure_control.WIDTH={width}','-o',str(exe),str(root/'rtl/test/w15_tp96_measure_counter.sv'),str(root/'rtl/test/tb_w15_tp96_measure_control.sv')]
 b=subprocess.run(cmd,capture_output=True,text=True);files[name+'.build.log']=(b.stdout+b.stderr).encode();assert b.returncode==0,b.stderr
 argv=['vvp',str(exe),f'+OVERFLOW={overflow}']
 r=subprocess.run(argv,capture_output=True,text=True,timeout=60);log=r.stdout+r.stderr;files[name+'.log']=log.encode();files['binary/'+name+'.vvp']=exe.read_bytes()
 passed=witness in log and (r.returncode==0 if name=='long_round' else r.returncode!=0) and 'measurement control timeout' not in log
 if name=='long_round':passed=passed and 'issue=65530 done=528992 elapsed=463462 final=600000 protocol=10176 wraps=9 period_ps=1112' in log
 cases[name]={'passed':passed,'actual_rc':r.returncode,'expected_rejection':name!='long_round','witness':witness,'compile_argv':cmd,'run_argv':argv,'binary_sha256':sha(exe.read_bytes())}
 assert passed,(name,log)
 print('MEASUREMENT_CONTROL',name,'PASS','rc',r.returncode,flush=True)
# Positive refusal control against the sole actual current campaign, not a launch.
try:C.assert_no_live_tp96()
except RuntimeError as e:live_guard={'passed':True,'observation':str(e)}
else:live_guard={'passed':False,'observation':'no equivalent local job live at observation; mock process tests cover guard'}
paths=C.SOURCES+['rtl/test/tb_w15_tp96_measure_control.sv','tools/w15_tp96_exact.py','tests/test_w15_tp96_exact.py','tests/test_w15_tp96_measurement.py','results/rtl/w15_tp96_timing_contract_20261001.json']
pins={p:sha((root/p).read_bytes()) for p in paths}
for p,h in pins.items():assert sha(subprocess.check_output(['git','show',pin+':'+p],cwd=root))==h,p
contract=json.loads((root/'results/rtl/w15_tp96_timing_contract_20261001.json').read_text())
for p,h in contract['source_sha256'].items():assert pins[p]==h
files['full_harness_lint.log']=pathlib.Path('/tmp/claude-1000/w15b_codex_sram_20261001/timing_fix_lint.log').read_bytes()
files['collect_timing_control.py']=pathlib.Path(__file__).read_bytes()
record={'schema':'w15_tp96_measurement_control_v1','source_commit':pin,'source_sha256':pins,'cases':cases,'live_campaign_guard':live_guard,'full_harness_lint_rc':0,'full_harness_lint_scope':'corrected TP96 harness and all10 actual RTL sources; instrumentation only, no full collective simulation','focused_test_scope':'15 focused tests observed PASS before source commit; source bytes match committed pin. Includes synthetic288-row parser checks and actual counter controls.','verdict':'PASS','actual_full96_measurement':'pending_not_run','legacy_latency':'pending_unqualified; preserve original source and outputs','no_collective_campaign_launched':True,'no_physical_or_product_claim':True,'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tools':{}}
for name in ['iverilog','vvp']:
 p=pathlib.Path(shutil.which(name));r=subprocess.run([str(p),'-V'],capture_output=True,text=True)
 record['tools'][name]={'path':str(p),'sha256':sha(p.read_bytes()),'version':r.stdout+r.stderr}
files['record.json']=(json.dumps(record,indent=2,sort_keys=True)+'\n').encode()
manifest={'files':{n:sha(b) for n,b in files.items()},'source_commit':pin,'scope':'Actual measurement-counter controls only; not a substitute for full96 exact terminal results or contextual SS/FF.'}
out.mkdir()
for n,b in files.items():p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('IMMUTABLE_MEASUREMENT_CONTROLS_READY',pin,len(files),flush=True)
