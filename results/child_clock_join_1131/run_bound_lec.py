import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent;K=R/'kit';N=K/'run/results/asap7/kl_ot_s81ph_native_sel_hist_bank_hrB20/base/6_final.v';O=R/'official_eq';O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory():return {str(p):sha(p) for p in sorted(K.rglob('*')) if p.is_file()}|{str(R/'lec.py'):sha(R/'lec.py'),str(Path(__file__).resolve()):sha(__file__)}
image=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','openroad/orfs:asap7lock'],text=True).strip()
cmd=['python3',str(R/'lec.py'),str(K),'--netlist',str(N),'--out',str(O),'--gold-frontend','slang','--jobs','2','--mem','4','--image',image]
env=os.environ.copy();env['OT_LEC_SUPERSET_VEC']='1'
for key in ('OT_LEC_RESET_CYCLES','OT_LEC_RAW_BASE_STEPS','OT_LEC_HINTS_PRESEED','OT_LEC_EARLY_COMPARE'):env.pop(key,None)
r=dict(schema='opentallas.lec_input_identity.v1',netlist=str(N),netlist_sha256=sha(N),image_id=image,command=cmd,before=inventory(),environment={k:v for k,v in env.items() if k.startswith('OT_LEC_')})
(R/'official_identity_before.json').write_text(json.dumps(r,indent=2)+'\n')
rc=subprocess.call(cmd,env=env);r['exit_code']=rc;r['after']=inventory()
if (O/'lec.json').is_file():r['lec_sha256']=sha(O/'lec.json')
(R/'official_input_identity.json').write_text(json.dumps(r,indent=2)+'\n')
if r['before']!=r['after']:raise SystemExit('proof input changed')
raise SystemExit(rc)
