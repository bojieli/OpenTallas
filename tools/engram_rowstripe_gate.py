#!/usr/bin/env python3
"""Remote layout payload/capacity and actual controller-face rowstripe gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
rtl=[R/'rtl/dsrom_sys/engram'/x for x in ['ot_dsrom_engram_boot_path.sv','ot_dsrom_engram_boot_dispatch.sv','ot_dsrom_engram_boot_ctrl_map.sv']]
tb=R/'rtl/test/tb_dsrom_engram_boot_rowstripe.sv'
out=R/'results/rtl/engram_rowstripe_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    sources=rtl+[tb,R/'tools/engram_boot_image.py',R/'tests/test_engram_boot_image.py',R/'tools/uarch_model.py',Path(__file__)]
    rec=dict(schema='opentallas.engram-rowstripe-gate.v1',boundary='boot/loader mapping and capacity only; read service return stalls, shared controller arbitration and physical closure unqualified',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},cases={})
    with tempfile.TemporaryDirectory() as tmp:
        for name,mutant in [('control',False),('wrong_pc',True)]:
            text=rtl[2].read_text()
            if mutant:
                needle='incoming_pc=(iv_q[1] ? 32 : 0)+(ROWSTRIPE ? ((ia_q/9)%32) : ia_q[4:0]);'
                assert text.count(needle)==1
                text=text.replace(needle,needle[:-1]+" ^ 6'd1;")
            src=Path(tmp)/'map.sv';src.write_text(text);exe=Path(tmp)/'sim'
            b=subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_boot_rowstripe','-o',str(exe),*[str(p) for p in rtl[:2]],str(src),str(tb)],capture_output=True,text=True)
            if b.returncode:raise RuntimeError(b.stderr)
            run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            ok=run.returncode!=0 and 'rowstripe PC/address identity' in run.stdout if mutant else run.returncode==0 and 'ENGRAM_ROWSTRIPE_BOOT PASS' in run.stdout
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=ok)
    run=subprocess.run(['python3','-m','pytest','-q','tests/test_engram_boot_image.py'],cwd=R,capture_output=True,text=True)
    rec['cases']['loader']=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
