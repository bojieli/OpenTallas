"""mesh_hints.py W IN OUT HINTS_OUT: hd_mesh lec_hints -> the proven RBL=1 form (main l48hp1_mesh_hints/lec_hints_rbl1.json.gz,
HEAD-92 11-10 READY 4ed720d29475, EQUIVALENT on ds8). Asserts the only change is g_rb_safe.u_m.wdata[i] eq a_in[i] -> a0_in[i]."""
import json,sys,gzip,subprocess,hashlib
W,IN,OUT,HO=sys.argv[1:5]
fixed=json.loads(gzip.decompress(subprocess.check_output(['git','-C',W,'show','origin/main:physical/die_plan/s81_head/plan_of_record/l48hp1_mesh_hints/lec_hints_rbl1.json.gz'])))
p=json.load(open(IN));t=p['partition_types']['hd_mesh'];old=t['lec_hints']
assert len(old)==len(fixed)
n=0
for a,b in zip(old,fixed):
    if a==b:continue
    exp=json.loads(json.dumps(a).replace('.u_ep.a_in[','.u_ep.a0_in['))
    assert 'g_rb_safe.u_m.wdata[' in a[1] and exp==b,(a,b);n+=1
t['lec_hints']=fixed
body=json.dumps(fixed,indent=1)+'\n';open(HO,'w').write(body)
open(OUT,'w').write(json.dumps(p,indent=1)+'\n')
print(json.dumps(dict(rows_changed=n,count=len(fixed),hints_sha256=hashlib.sha256(body.encode()).hexdigest())))
