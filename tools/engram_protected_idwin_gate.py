#!/usr/bin/env python3
"""Full64-user protected history/metadata exact fault/rewind gate, remote only."""
import ast,hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/engram/ot_dsrom_engram_idwin_protected.sv',R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',R/'rtl/test/tb_dsrom_engram_idwin_protected.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_protected_idwin_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-protected-idwin-'));obj=work/'obj';top='tb_dsrom_engram_idwin_protected'
    src=R/'tools/uarch_model.py';tree=ast.parse(src.read_text());ns={}
    fn=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_engram_protected_idwin_model'];exec(compile(ast.Module(body=fn,type_ignores=[]),str(src),'exec'),ns)
    rec=dict(schema='opentallas.engram-protected-idwin-gate.v1',retained_objects=str(work),model=ns['dsrom_engram_protected_idwin_model'](),cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[src,Path(__file__)]})
    b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:
        rec.update(status='build-fail',build_error=b.stderr[-3000:]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');return 1
    for m in range(9):
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={m}'],capture_output=True,text=True)
        rec['cases'][str(m)]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and ('ENGRAM_PROTECTED NEG' if m else 'ENGRAM_PROTECTED PASS') in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
