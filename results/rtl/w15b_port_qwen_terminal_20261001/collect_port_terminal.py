"""Read-only terminal intake; never launch, stop, or modify a worker job."""
import subprocess,pathlib,json,hashlib,tarfile,io,datetime
ROOT=pathlib.Path('/home/ubuntu/w15b-codex-sram-20261001')
OUT=ROOT/'results/rtl/w15b_port_qwen_terminal_20261001'
REMOTE=r'''
import subprocess,pathlib,json,hashlib,tarfile,io,sys
job='otjob-a1b0ccc17a'
if job in subprocess.check_output(['docker','ps','--format','{{.Names}}'],text=True).splitlines():
 print('LIVE',file=sys.stderr);sys.exit(2)
if pathlib.Path('/proc/506469').exists():raise RuntimeError('worker wrapper remains; wait')
r=pathlib.Path('/tmp/claude-1000/w15p/out/port_qwen');rec=json.loads((r/'physical.json').read_text());src=pathlib.Path('/home/ubuntu/w15bwt8')
assert rec['git']['commit']=='19ecd2fb4d64c2ace60ec6f18d36a1d754db55bb'
s=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for x in rec['design']['sources']:assert s(src/x['path'])==x['sha256']
driver=rec['runner']['driver'];assert s(src/'tools/run_abi3_physical.py')==driver['sha256']
files={'physical.json':(r/'physical.json').read_bytes(),'source/tools/run_abi3_physical.py':(src/'tools/run_abi3_physical.py').read_bytes()}
for f in ['signoff_ssff.json','signoff.log']:
 if (r/f).exists():files[f]=(r/f).read_bytes()
for x in rec['design']['sources']:files['source/'+x['path']]=(src/x['path']).read_bytes()
if 'signoff_ssff.json' in files:
 so=json.loads(files['signoff_ssff.json']);assert s(src/'tools/signoff_analysis.py')==so['tool']['sha256'];files['source/tools/signoff_analysis.py']=(src/'tools/signoff_analysis.py').read_bytes();assert so['record']['git_commit']==rec['git']['commit'];d=pathlib.Path(so['routed']['results_dir'])
 for key,name in [('netlist_sha256','6_final.v'),('odb_sha256','6_final.odb'),('spef_sha256','6_final.spef')]:assert s(d/name)==so['routed'][key],name
 for p in pathlib.Path('/home/ubuntu/w15work/so_port_qwen').rglob('*'):
  if p.is_file() and p.suffix in ['.log','.rpt','.tcl','.json']:files['corner_sessions/'+str(p.relative_to('/home/ubuntu/w15work/so_port_qwen'))]=p.read_bytes()
for p in (r/'physical_artifacts').glob('*'):
 if p.is_file() and p.suffix in ['.sdc','.mk','.json','.rpt']:files['physical_artifacts/'+p.name]=p.read_bytes()
obs={'container_absent':job,'wrapper_pid_absent':506469,'actual_source_hashes_verified':True,'routed_hashes_verified':'signoff_ssff.json' in files}
files['worker_terminal_check.json']=(json.dumps(obs,indent=2)+'\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
 for n,b in sorted(files.items()):
  i=tarfile.TarInfo(n);i.size=len(b);i.mtime=0;i.mode=0o644;t.addfile(i,io.BytesIO(b))
'''
r=subprocess.run(['ssh','-i',str(pathlib.Path.home()/'.ssh/agidock_ot'),'-o','BatchMode=yes','-o','ConnectTimeout=12','ot-pve2','python3 -'],input=REMOTE.encode(),capture_output=True)
if r.returncode:print(r.stderr.decode(),end='');raise SystemExit(r.returncode)
assert not OUT.exists(), 'immutable destination already exists'
files={}
with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:gz') as t:
 for i in t:
  assert i.isfile() and not i.name.startswith('/') and '..' not in pathlib.PurePosixPath(i.name).parts
  files[i.name]=t.extractfile(i).read()
rec=json.loads(files['physical.json']);pin=rec['git']['commit'];sha=lambda b:hashlib.sha256(b).hexdigest()
for x in rec['design']['sources']:
 assert sha(files['source/'+x['path']])==x['sha256']==sha(subprocess.check_output(['git','show',pin+':'+x['path']],cwd=ROOT))
for f in ['tools/run_abi3_physical.py','tools/signoff_analysis.py']:
 if 'source/'+f in files:assert files['source/'+f]==subprocess.check_output(['git','show',pin+':'+f],cwd=ROOT)
assert rec['design']['clock_uncertainty_ns']==.06 and rec['design']['clock_uncertainty_hold_ns']==.025 and rec['target_clock_period_ns']==.833
sdc=files['physical_artifacts/constraint.sdc'].decode();assert 'set clk_period 833' in sdc and 'set_clock_uncertainty -setup 60' in sdc and 'set_clock_uncertainty -hold 25' in sdc
so=json.loads(files['signoff_ssff.json']) if 'signoff_ssff.json' in files else None
ss=so['corners'].get('SS',{}).get('timing',{}) if so else {};ff=so['corners'].get('FF',{}).get('timing',{}) if so else {}
corner_pass=(ss.get('setup_wns_ns') is not None and ss['setup_wns_ns']>=0 and ff.get('hold_wns_ns') is not None and ff['hold_wns_ns']>=0)
manifest={'source_commit':pin,'worker':'ot-pve2','job':'otjob-a1b0ccc17a','archived_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'physical_status':rec['status'],'ss_setup':ss,'ff_hold':ff,'ssff_timing_pass':corner_pass,'claim_boundary':'Historical pinned port job. Preserve verdict; no current renamed-module contextual qualification or product adoption.','files':{n:sha(b) for n,b in sorted(files.items())}}
for n,b in files.items():p=OUT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
(OUT/'collect_port_terminal.py').write_bytes(pathlib.Path(__file__).read_bytes())
print('TERMINAL_INTAKE_PASS',pin,'physical',rec['status'],'SSFF',corner_pass,len(files),'files')
