# Build the frozen HP13 frontend tree (QDIE5 recipe) at OUT; optionally swap u_cal to the CALREG[0] FQREG form.
import json,hashlib,subprocess,sys,re
from pathlib import Path
hub,ref,out,mode=sys.argv[1],sys.argv[2],Path(sys.argv[3]),sys.argv[4]   # mode: base | fqreg | fqreg_mut2
out.mkdir(parents=True,exist_ok=True)
NF='results/arch/qw_headprep_1021/rrloc_projection/native_frontend'
def show(c,p): return subprocess.run(['git','-C',hub,'show',f'{c}:{p}'],capture_output=True,check=True).stdout
inv=json.loads(show(ref,NF+'/input_source_inventory.json'))['files']
cmap=json.load(open('/tmp/ctlm_inv_map.json'))
root_files={'physical_abstracts.v','physical_abstracts.json','full_generic_hp13.ys','construct_hp13.py','run_frontend.sh'}
for p,s in inv.items():
    if p in root_files: continue
    b=show(cmap[p],p); assert hashlib.sha256(b).hexdigest()==s,p
    q=out/p; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(b)
for f in ['physical_abstracts.v','physical_abstracts.json','full_generic_hp13.ys','construct_hp13_2.py']:
    (out/f).write_bytes(show(ref,NF+'/'+f))
for f in ['physical_abstracts.v','physical_abstracts.json','full_generic_hp13.ys']:
    assert hashlib.sha256((out/f).read_bytes()).hexdigest()==inv[f],f
# macro abstracts' sources (sha-checked by construct)
for m in json.loads((out/'physical_abstracts.json').read_text()):
    q=out/m['source']
    if not q.exists():
        b=None
        for c in [ref,'4b215c0b3','8349f4a116626c59dfdb5ab8670f818514faa0e8']:
            try:
                x=show(c,m['source'])
                if hashlib.sha256(x).hexdigest()==m['source_sha256']: b=x;break
            except subprocess.CalledProcessError: pass
        assert b is not None,m['source']; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(b)
rec={'mode':mode,'ref':ref}
if mode!='base':
    h=show(ref,'rtl/qwen_dv/headprep37/qfd_dv_cmd_cal_mu_head37.sv').decode()
    rec['head37_sha256']=hashlib.sha256(h.encode()).hexdigest()
    h=h.replace('module qfd_dv_cmd_cal_mu_head37 #(','module qfd_dv_cmd_cal_mu #(',1)
    old='    parameter integer CALREG = 0                    // QE3-CTLM3'
    assert h.count(old)==1
    h=h.replace(old,'    parameter integer CALREG = 1                    // CTLM-FQREG 11-08 frontend: [0] FQREG on; QE3-CTLM3',1)
    if mode=='fqreg_mut2':
        # mutant: nx_q refill from the wrong ring half at c0 == 1 (bench must catch)
        o2="                    else if (c0 == 4'd1) nx_q[g] <= rds[127:0];"
        assert h.count(o2)==1; h=h.replace(o2,"                    else if (c0 == 4'd1) nx_q[g] <= rds[255:128];",1)
    p='rtl/qwen_dv/headprep13/frontend_fqreg/qfd_dv_cmd_cal_mu_fqreg.sv'
    (out/p).parent.mkdir(parents=True,exist_ok=True); (out/p).write_text(h)
    ys=(out/'full_generic_hp13.ys').read_text()
    assert ys.count(' rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv ')==1
    (out/'full_generic_hp13.ys').write_text(ys.replace(' rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv ',' '+p+' ',1))
    rec['cal_source']=p; rec['cal_sha256']=hashlib.sha256((out/p).read_bytes()).hexdigest()
(out/'TREE.json').write_text(json.dumps(rec,indent=1)+'\n'); print('TREE OK',mode,rec.get('cal_sha256','')[:12])
