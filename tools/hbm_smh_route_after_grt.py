"""Continue only this owner's successful r2 GRT; no synth/place/CTS/GRT replay."""
import sys,os,json,time,subprocess,shutil,hashlib,importlib.util,re
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch');import admit_core
label=sys.argv[1]
root=Path('/srv/opentallas-scratch2/scratch/codex/hbmsm-local-grt-r2');w=root/label;src=root/'src'
meta=w/'final_continuation';meta.mkdir(exist_ok=False)
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
(meta/'status').write_text('WAIT_EXISTING_R2_GRT_TERMINAL\n')
while not (w/'terminal.json').exists():time.sleep(30)
term=json.loads((w/'terminal.json').read_text())
if term['rc']!=0:
 (meta/'status').write_text('BLOCKED_ACTUAL_GRT_FAIL_RC='+str(term['rc'])+'\n');sys.exit(0)
assert term['checkpoint_unchanged']
base=next((w/'results/asap7').glob('*/base'))
assert (base/'5_1_grt.odb').is_file() and (base/'5_1_grt.sdc').is_file()
receipt=json.loads((w/'source_checkpoint_pin.json').read_text())
for p,h in receipt['source_sha256'].items():assert sha(src/p)==h
# Preserve original CTS and good GRT to permit true stage-only recovery.
original={str(p.relative_to(w)):sha(p) for p in [base/'4_cts.odb',base/'4_cts.sdc',base/'5_1_grt.odb',base/'5_1_grt.sdc',w/'config.mk',w/'constraint.sdc',w/'pins.tcl',w/'macros.tcl']}
(meta/'source_checkpoint.json').write_text(json.dumps(dict(image=image,sha256=original,
 source_sha256=receipt['source_sha256'],source_pin=receipt['original_source_pin'],
 synthesis_replay=False,placement_replay=False,CTS_replay=False,GRT_replay=False),indent=2)+'\n')
def guard(stage):
 while True:
  load=os.getloadavg();avail=admit_core._avail();disk=shutil.disk_usage(root)
  # SAME approved24GiB/24core whole-tile reservation as original owner launcher,
  # actual prior GRT peak8.55GiB, source4_cts inventory267MB and totaloutput4GiB.
  # This is admission only, not a per-process/cgroup/time/file limit.
  if load[0]<128 and disk.free>2*4*2**30+300*2**20 and admit_core.try_admit(24*2**30):break
  time.sleep(10)
 (meta/(stage+'_admission.json')).write_text(json.dumps(dict(load=load,MemAvailable=avail,disk_free=disk.free,
  reservation_GiB=24,cores=24,execution_caps=None,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())),indent=2)+'\n')
def container(cmd,name=None):
 a=['docker','run','--rm']
 if name:a+=['--name',name]
 return a+['-v',str(src)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow',image,'bash','-lc',cmd]
guard('route')
# Explicit do- stages have no prerequisite rebuild. do-route is excluded: it
# would invoke GRT again. No guessed droute_end_iter or other execution cap.
cmd=container('source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=24 do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report','codex-smh-final-r2-'+label)
(meta/'route_command.json').write_text(json.dumps(cmd,indent=2)+'\n');(meta/'status').write_text('LIVE_DETAIL_ROUTE_FINAL_FROM_GOOD_GRT\n')
with (meta/'route.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
subprocess.run(container('chmod -R a+rwX /work'),check=True)
assert all(sha(w/p)==h for p,h in original.items())
(meta/'route_exit.json').write_text(json.dumps(dict(rc=rc,checkpoints_unchanged=True))+'\n')
if rc:
 (meta/'status').write_text('FAIL_DETAIL_ROUTE_FINAL_RC='+str(rc)+'\n');sys.exit(rc)
for f in ['6_final.odb','6_final.spef','6_final.sdc']:assert (base/f).is_file()
# Existing source-pinned corner script generates all-path checks and R2R/I2R/
# output classes. Execute it in SAME frozen tool image; check actual rc/errors.
spec=importlib.util.spec_from_file_location('corner',src/'tools/w18/corner_sta.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
macros=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2']
sdc=(base/'6_final.sdc').read_text()
assert re.search(r'set_clock_uncertainty\s+-setup\s+60',sdc) and re.search(r'set_clock_uncertainty\s+-hold\s+25',sdc)
assert re.search(r'create_clock[^\n]*-period\s+833',sdc)
rec=dict(image=image,policy='833ps SSsetup60/F Fhold25 unchanged; virtual neighbour only, full real abutment pending',
 source_checkpoint=original,corner_script_sha256=sha(src/'tools/w18/corner_sta.py'),
 final_sha256={f:sha(base/f) for f in ['6_final.odb','6_final.spef','6_final.sdc']},corners={})
for corner in ['ss','ff']:
 guard(corner)
 tcl=meta/('sta_'+corner+'.tcl');rel='/work/'+str(base.relative_to(w))
 tcl.write_text(C.script(corner,rel,macros).replace('-group_path_count 1 -format full_clock_expanded','-group_path_count 20 -format full_clock_expanded'))
 cmd=container('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/final_continuation/'+tcl.name)
 (meta/('command_'+corner+'.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (meta/('sta_'+corner+'.log')).write_text(r.stdout)
 assert r.returncode==0 and not re.search(r'\[ERROR',r.stdout),corner+' tool error'
 def field(k):
  m=re.search(r'^'+k+r' (\S+)',r.stdout,re.M)
  assert m is not None,k
  return m[1]
 # OT_WS/TNS are raw seconds per existing corner tool; class properties ps.
 rec['corners'][corner]=dict(check='setup' if corner=='ss' else 'hold',
  worst_slack_ps=float(field('OT_WS'))*1e12,TNS_ps=float(field('OT_TNS'))*1e12,
  violating_D_pins=int(field('OT_VIOL_D_PINS')),
  worst_reg_D_ps=field('OT_WS_REG_D'),worst_output_ps=field('OT_WS_OUT'),
  worst_R2R_ps=field('OT_WS_R2R'),worst_I2R_ps=field('OT_WS_I2R'))
rec['closes_conditional_SSFF']=all(x['worst_slack_ps']>=0 for x in rec['corners'].values())
rec['adopt']=False;rec['full_abutment_closed']=False
(meta/'corner_sta.json').write_text(json.dumps(rec,indent=2)+'\n')
(meta/'status').write_text('TERMINAL_FINAL_SSFF_'+('PASS_CONDITIONAL' if rec['closes_conditional_SSFF'] else 'FAIL')+'\n')
