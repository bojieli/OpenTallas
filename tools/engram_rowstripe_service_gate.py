#!/usr/bin/env python3
"""Remote full six-request same-PC service queue and overcredit gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/engram/ot_dsrom_engram_rowstripe_service.sv',R/'rtl/dsrom_sys/engram/ot_dsrom_engram_rowstripe_read.sv',R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',R/'rtl/test/tb_dsrom_engram_rowstripe_service.sv']
out=R/'results/rtl/engram_rowstripe_service_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-rowstripe-service-gate.v1',boundary='six queued same-PC reads at actual controller face, eight producer credits and overflow failclose; no physical/die/shared arbitration credit',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    with tempfile.TemporaryDirectory() as tmp:
        exe=Path(tmp)/'sim'
        b=subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_rowstripe_service','-o',str(exe),*[str(p) for p in paths]],capture_output=True,text=True)
        if b.returncode:raise RuntimeError(b.stderr[-3000:])
        for name,mode in [('same_pc_queued',0),('overcredit',1)]:
            run=subprocess.run(['vvp',str(exe),f'+MODE={mode}'],capture_output=True,text=True)
            wanted='ENGRAM_SERVICE NEG' if mode else 'ENGRAM_SERVICE PASS'
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and wanted in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
