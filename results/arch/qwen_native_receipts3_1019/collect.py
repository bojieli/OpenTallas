"""Read-only snapshots of already running jobs; no tool execution or mutation remotely."""
import concurrent.futures, datetime, hashlib, json, pathlib, subprocess

OUT = pathlib.Path(__file__).resolve().parent
if (OUT / 'safe3.json').exists():
    raise SystemExit('Refusing to overwrite existing evidence; use a fresh directory.')
JOBS = {
    'safe3': ('ot-epyc7', 'qfd_native59_dv_service_safe3-20261019-113209'),
    'safe3b': ('ot-epyc7', 'qfd_native59_dv_service_safe3b-20261019-113209'),
    'safe3c': ('ot-epyc6', 'qfd_native59_dv_service_safe3c-20261019-115739'),
    'bc2l': ('ot-epyc8', 'qfd_sys_face_bc2l-20261019-114348'),
}
REMOTE = r'''
import datetime, hashlib, json, pathlib, subprocess, sys
d=pathlib.Path(sys.argv[1])
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'remote_dir':str(d),'files':{}}
paths=[d/'execution.log',d/'cts.log',d/'textbook.json',d/'pin_geometry.json',d/'routes/gate/flow.log',d/'routes/gate/physical.json']
paths+=list(d.glob('routes/gate/work/orfs/logs/asap7/*/base/1_2_yosys.log'))
paths+=list((d/'src/physical/ref_tile').glob('*/spec.json'))
for p in paths:
 if not p.is_file(): continue
 b=p.read_bytes(); lines=b.decode(errors='replace').splitlines()
 r['files'][str(p.relative_to(d))]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mtime_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'tail':'\n'.join(lines[-100:])}
r['final_cts_odb']=[str(p) for p in d.glob('routes/gate/work/orfs/results/asap7/*/base/4_cts.odb')]
r['layout_png']=[str(p) for p in d.glob('**/gate_layout*.png')]
print(json.dumps(r,indent=2))
'''
def collect(item):
    name,(host,run)=item
    d='/srv/opentallas-scratch/claude/ref_gate/'+run
    p=subprocess.run(['ssh',host,'python3','-',d],input=REMOTE,text=True,capture_output=True,timeout=90)
    if p.returncode: raise RuntimeError(p.stderr)
    data=json.loads(p.stdout); data['host']=host
    (OUT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(collect,JOBS.items()))
result=subprocess.run(['ps','-p','452733,452734,1087840,587360','-o','pid,etime,args'],capture_output=True,text=True,check=True)
(OUT/'clients.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n'+result.stdout)
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.name!='sha256.json' and p.is_file()}
(OUT/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
