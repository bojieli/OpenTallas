#!/usr/bin/env python3
"""Actual native HIDDEN formatter and package receiver window identity gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/s81_ctrl/ot_s81_hop_tx.sv',R/'rtl/dsrom_sys/s81_ctrl/ot_s81_pkg_ctrl.sv',R/'rtl/test/tb_s81_engram_window.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_window_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-window-'));obj=work/'obj';top='tb_s81_engram_window'
    rec=dict(schema='opentallas.engram-native-window-gate.v1',retained_objects=str(work),cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]})
    b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise RuntimeError(b.stderr[-3000:])
    for m in range(5):
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={m}'],capture_output=True,text=True)
        rec['cases'][str(m)]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and ('ENGRAM_WINDOW NEG' if m else 'ENGRAM_WINDOW PASS') in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
