import os,sys,time,json,hashlib,fcntl,subprocess
from pathlib import Path
ROOT=Path('/srv/opentallas-scratch2/codex/dsrom-fh-capture-20261005')
SRC=ROOT/'wt-checked-native-r17';RUN=ROOT/'routes/C22_checked_receivers';AUX=ROOT/'C22_receiver_retained_envelope';WORK=RUN/'work/orfs'
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
def check():
 p=json.loads((SRC/'SOURCE_PIN.json').read_text());m=json.loads((AUX/'reuse.json').read_text());assert p['commit']==m['source_commit']
 for n,h in p['sha256'].items():assert hashlib.sha256((SRC/n).read_bytes()).hexdigest()==h,n
 for n,h in m['reused_sha256'].items():assert hashlib.sha256((WORK/n).read_bytes()).hexdigest()==h,n
 c=(WORK/'config.mk').read_text();assert 'export PLACE_DENSITY = 0.6' in c and 'export PLACE_DENSITY_LB_ADDON = \n' in c and 'export CORNERS = WC BC' in c
 assert 'RETIRE 1 VM_ENDPOINT 1' in c
 return m
def measured():
 def stat():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=stat();time.sleep(1);b=stat();d=[y-x for x,y in zip(a,b)];mem={k:int(v.split()[0]) for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())};fs=os.statvfs(ROOT)
 return dict(time=time.time(),load=os.getloadavg()[0],idle_cores=os.cpu_count()*(d[3]+d[4])/sum(d),available_GiB=mem['MemAvailable']/1048576,free_GiB=fs.f_bavail*fs.f_frsize/2**30)
def fits(m):return m['load']<128 and m['idle_cores']>=16 and m['available_GiB']>=148 and m['free_GiB']>=30
def docker(args,env=None):
 return ['docker','run','--rm','-e','OMP_NUM_THREADS=16',*sum((['-e',k+'='+v] for k,v in (env or {}).items()),[]),'-v',str(SRC)+':/src:ro','-v',str(WORK)+':/work','-v',str(AUX)+':/report:ro','-v',str(ROOT/'cut-report-58f288206')+':/cuttool:ro','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc',args]
if '--admitted' in sys.argv:
 m=check();v=measured();print('POSTGUARD '+json.dumps(v),flush=True)
 if not fits(v):sys.exit(75)
 (RUN/'fullroute_postguard.json').write_text(json.dumps(v,indent=2)+'\n')
 base=m['base'];prefix='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
 excludes=' '.join('-o /work/'+n for n in m['reused_sha256'])
 argv=docker(prefix+'python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 '+excludes+' finish metadata-generate');cmds=[argv];print('RETAINED_MAPPING_CONTEXT_EXEC '+json.dumps(argv),flush=True);rc=subprocess.run(argv).returncode
 (RUN/'fullroute_driver_argv.json').write_text(json.dumps(cmds,indent=2)+'\n');(RUN/'fullroute_terminal.json').write_text(json.dumps(dict(returncode=rc,finished=time.time(),source_commit=m['source_commit'],no_synthesis_or_golden_replay=True),indent=2)+'\n');sys.exit(rc)
lock=(ROOT/'C22_checked_receivers_controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);check();print('SOLE_FULLROUTE_CONTROLLER '+str(os.getpid()),flush=True)
while True:
 v=measured();print('PRECHECK '+json.dumps(v),flush=True)
 if fits(v):
  (RUN/'fullroute_preguard.json').write_text(json.dumps(v,indent=2)+'\n')
  rc=subprocess.run(['/srv/opentallas-scratch/admit.sh','48','--','python3',str(Path(__file__).resolve()),'--admitted']).returncode
  if rc!=75:sys.exit(rc)
 time.sleep(30)
